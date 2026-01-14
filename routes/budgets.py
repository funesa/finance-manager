# src/web/routes/budgets.py
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash
)
from flask_login import login_required, current_user
from datetime import datetime, timezone
import locale # Importado para formatar o mês
from contextlib import contextmanager # Para gerenciar o locale

# --- CORREÇÃO: Import absoluto (sem '...') ---
import database as db

# Crie o Blueprint
budgets_bp = Blueprint('budgets', 
                       __name__, 
                       template_folder='../templates')

# --- MELHORIA: Context Manager para Locale ---
# Isso garante que o mês (ex: "Novembro") apareça em Português
# sem afetar o resto da aplicação de forma global.
@contextmanager
def set_locale(name):
    saved = None
    try:
        # Tenta definir o locale. Pode falhar no Windows com 'pt_BR.UTF-8'
        # 'Portuguese_Brazil.1252' é um fallback comum no Windows.
        try:
            saved = locale.setlocale(locale.LC_TIME, name)
        except locale.Error:
            saved = locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
            
        yield
    finally:
        if saved:
            locale.setlocale(locale.LC_TIME, saved)

@budgets_bp.route("/budgets", methods=["GET", "POST"])
@login_required
def index():
    current_month = request.args.get("month", datetime.now(timezone.utc).strftime('%Y-%m'))
    
    if request.method == "POST":
        try:
            month_to_save = request.form.get("month")
            categories = db.fetch_categories(current_user.id)
            for cat_id, cat_name in categories:
                budget_val_str = request.form.get(f"budget_{cat_id}")
                if budget_val_str:
                    # Permite salvar valores vazios como "remover orçamento"
                    amount = 0.0
                    # Remove R$ e espaços, depois troca vírgula por ponto
                    cleaned_val = budget_val_str.replace("R$", "").strip()
                    if cleaned_val:
                        amount = float(cleaned_val.replace(",", "."))
                        
                    if amount >= 0:
                        db.set_budget(current_user.id, cat_id, amount, month_to_save)
            flash("Orçamentos salvos com sucesso!", "success")
        except Exception as e:
            flash(f"Erro ao salvar orçamentos: {e}", "danger")
        return redirect(url_for(".index", month=current_month))

    # GET
    budget_data = db.get_budgets_with_spending(user_id=current_user.id, month=current_month)
    
    current_month_str = current_month
    try:
        month_dt = datetime.strptime(current_month, '%Y-%m')
        # Usa o context manager para formatar o nome do mês em PT-BR
        with set_locale('pt_BR.UTF-8'):
            current_month_str = month_dt.strftime('%B de %Y').capitalize()
    except ValueError:
        pass # Mantém o formato 'YYYY-MM' se a data for inválida

    return render_template("budgets.html",
                           budget_data=budget_data,
                           current_month=current_month,
                           current_month_str=current_month_str,
                           datetime=datetime,
                           active_page="budgets"
                           )


@budgets_bp.route('/budgets/add_category', methods=['POST'])
@login_required
def add_category():
    try:
        name = request.form.get('category_name')
        amount_str = request.form.get('category_amount', '')
        month = request.form.get('month', datetime.now(timezone.utc).strftime('%Y-%m'))
        if not name:
            flash('Nome da categoria é obrigatório.', 'danger')
            return redirect(url_for('.index', month=month))

        cat_id = db.create_category(current_user.id, name)

        if amount_str:
            try:
                # Remove R$ e espaços, depois troca vírgula por ponto
                cleaned_val = amount_str.replace("R$", "").strip()
                amount = float(cleaned_val.replace(',', '.'))
                if amount >= 0:
                    db.set_budget(current_user.id, cat_id, amount, month)
            except ValueError:
                flash('Valor do orçamento inválido.', 'warning')

        flash('Categoria adicionada com sucesso.', 'success')
    except Exception as e:
        flash(f'Erro ao adicionar categoria: {e}', 'danger')
    return redirect(url_for('.index', month=month))


@budgets_bp.route('/budgets/delete_budget', methods=['POST'])
@login_required
def delete_budget_route():
    # --- CORREÇÃO: Lógica de exclusão reestruturada ---
    cat_id_str = request.form.get('category_id')
    month = request.form.get('month', datetime.now(timezone.utc).strftime('%Y-%m'))

    try:
        if not cat_id_str:
            raise ValueError("ID da categoria não fornecido")
            
        cat_id = int(cat_id_str)

        # Etapa 1: Tentar deletar o orçamento do mês específico
        budget_deleted = db.delete_budget(current_user.id, cat_id, month)

        # Etapa 2: Tentar deletar a categoria (se não estiver mais em uso)
        category_deleted = False
        category_error = None
        try:
            # Esta função (no DB) só deve deletar se não houver MAIS NENHUM
            # orçamento ou transação associada a ela.
            category_deleted = db.delete_category_if_unused(current_user.id, cat_id)
        except ValueError as ve:
            # Captura erro se a categoria ainda estiver em uso (ex: transações)
            category_error = str(ve) 

        # Etapa 3: Dar feedback claro ao usuário
        if budget_deleted and category_deleted:
            flash('Orçamento e categoria (agora sem uso) removidos com sucesso.', 'success')
        elif budget_deleted:
            flash('Orçamento do mês removido. A categoria foi mantida pois ainda está em uso.', 'success')
        elif category_deleted:
            # Caso estranho: orçamento não existia, mas a categoria existia e estava sem uso
            flash('Nenhum orçamento para este mês. A categoria (que estava sem uso) foi removida.', 'success')
        elif category_error:
            # Ex: "Categoria não pode ser removida pois possui transações."
            flash(category_error, 'warning')
        else:
            flash('Nenhum orçamento encontrado para este mês. A categoria foi mantida.', 'info')

        return redirect(url_for('.index', month=month))
            
    except Exception as e:
        print(f"Erro ao remover orçamento: {str(e)}")
        flash(f'Erro ao remover: {e}', 'danger')
        return redirect(url_for('.index', month=month))

# Função que o __init__.py irá chamar
def configure_budgets(app):
    app.register_blueprint(budgets_bp)

# --- CORREÇÃO: Removido o '}' extra que causava erro de sintaxe ---