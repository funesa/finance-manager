# routes/receivables.py
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, jsonify
)
from flask_login import login_required, current_user
from datetime import datetime  # <-- 'datetime' já está importado
from dateutil.relativedelta import relativedelta
import locale

import database as db

receivables_bp = Blueprint('receivables', __name__)

@receivables_bp.route("/receivables")
@login_required
def index():
    """Página principal de Contas a Receber."""
    
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')
        except locale.Error:
            locale.setlocale(locale.LC_TIME, '')

    today = datetime.now()
    target_date = today + relativedelta(months=1)
    target_month_str = target_date.strftime('%Y-%m')
    target_month_display = target_date.strftime('%b/%Y').capitalize()
    
    recurring_rules = db.get_recurring_receivables_by_user(current_user.id)
    paid_in_target_month_ids = db.get_paid_recurring_ids_for_month(current_user.id, target_month_str)
    pending_recurring_list = [
        rule for rule in recurring_rules if rule['id'] not in paid_in_target_month_ids
    ]
    
    pending_manual = db.get_receivables_by_user(current_user.id, status='pending')
    paid_history = db.get_paid_receivables_history(current_user.id)
    
    total_pending_recurring_target_month = sum(rule['amount'] for rule in pending_recurring_list)
    
    # Calculate cutoff for "everything up to end of target month"
    # Precisamos de tudo que é MENOR que o mês seguinte (ex: < '2026-03')
    cutoff_date = target_date + relativedelta(months=1)
    cutoff_str = cutoff_date.strftime('%Y-%m') # "2026-03"

    total_pending_manual_target_month = 0
    for row in pending_manual:
        # row[4] formata 'YYYY-MM-DD'. Comparação de string funciona (ISO 8601)
        # Se '2026-01-15' < '2026-03' -> True (Inclui atrasados)
        # Se '2026-02-28' < '2026-03' -> True (Inclui mês atual)
        if row[4] < cutoff_str:
            total_pending_manual_target_month += row[3]
    
    total_pending_target_month = total_pending_recurring_target_month + total_pending_manual_target_month
    
    total_all_pending_manual = sum(row[3] for row in pending_manual)
    total_all_pending_recurring = sum(rule['amount'] for rule in recurring_rules)
    total_pending_all_time = total_all_pending_manual + total_all_pending_recurring
    
    
    return render_template('receivables.html', 
                           pending_manual_receivables=pending_manual,
                           pending_recurring=pending_recurring_list,
                           all_recurring_rules=recurring_rules,
                           paid_history=paid_history,
                           
                           total_pending_this_month=total_pending_target_month,
                           total_pending_all_time=total_pending_all_time,   
                           
                           target_month_display=target_month_display,
                           
                           today=today.strftime('%Y-%m-%d'),
                           current_day=today.day,
                           # --- CORREÇÃO AQUI ---
                           datetime=datetime
                           )

# ... (restante do arquivo 'receivables.py' permanece o mesmo) ...

@receivables_bp.route("/receivables/add_manual", methods=["POST"])
@login_required
def add_manual():
    """Adiciona uma nova conta a receber (Avulsa ou Parcelada)."""
    try:
        debtor_name = request.form.get('debtor_name')
        description = request.form.get('description')
        total_amount_str = request.form.get('amount')
        start_date_str = request.form.get('date')
        
        try:
            installments = int(request.form.get('installments', 1))
            if installments <= 0:
                installments = 1
        except ValueError:
            installments = 1
        
        if not debtor_name or not total_amount_str or not start_date_str:
            flash("Nome, valor total e data da 1ª parcela são obrigatórios.", "danger")
            return redirect(url_for('receivables.index'))
        
        total_amount = float(total_amount_str)
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

        if installments == 1:
            db.add_receivable(current_user.id, debtor_name, description, total_amount, start_date_str)
        else:
            installment_amount = round(total_amount / installments, 2)
            remainder = round(total_amount - (installment_amount * installments), 2)
            
            for i in range(installments):
                current_installment = i + 1
                current_date = start_date + relativedelta(months=i)
                current_desc = f"{description} ({current_installment}/{installments})"
                
                current_amount = installment_amount
                if i == 0:
                    current_amount += remainder
                    current_amount = round(current_amount, 2)
                
                db.add_receivable(
                    user_id=current_user.id,
                    debtor_name=debtor_name,
                    description=current_desc,
                    amount=current_amount,
                    date=current_date.strftime('%Y-%m-%d')
                )
                
        flash(f"{installments} parcela(s) de '{description}' adicionada(s) com sucesso!", "success")
        
    except Exception as e:
        flash(f"Erro ao adicionar: {e}", "danger")
        
    return redirect(url_for('receivables.index'))


@receivables_bp.route("/receivables/mark_manual_paid/<int:receivable_id>", methods=["POST"])
@login_required
def mark_manual_paid(receivable_id):
    """Marca uma conta avulsa/parcelada como paga."""
    try:
        db.update_receivable_status(receivable_id, current_user.id, 'paid')
        flash("Conta marcada como paga.", "success")
    except Exception as e:
        flash(f"Erro ao atualizar status: {e}", "danger")
        
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/receivables/delete_manual/<int:receivable_id>", methods=["POST"])
@login_required
def delete_manual(receivable_id):
    """Apaga uma conta avulsa/parcelada (ou um item do histórico)."""
    try:
        db.delete_receivable(receivable_id, current_user.id)
        flash("Registro apagado.", "success")
    except Exception as e:
        flash(f"Erro ao apagar: {e}", "danger")
        
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/receivables/edit_manual/<int:receivable_id>", methods=["POST"])
@login_required
def edit_manual(receivable_id):
    """Edita uma conta avulsa/parcelada."""
    try:
        debtor_name = request.form.get('edit_debtor_name')
        description = request.form.get('edit_description')
        amount = float(request.form.get('edit_amount'))
        date = request.form.get('edit_date')
        
        if not debtor_name or not amount or not date:
            flash("Nome, valor e data são obrigatórios.", "danger")
            return redirect(url_for('receivables.index'))
            
        db.update_receivable(receivable_id, current_user.id, debtor_name, description, amount, date)
        flash("Conta atualizada com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao editar: {e}", "danger")
        
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/api/receivable/<int:receivable_id>")
@login_required
def api_get_receivable(receivable_id):
    """Retorna dados de uma conta avulsa/parcelada para o modal de edição."""
    data = db.get_receivable_by_id(receivable_id, current_user.id)
    if data:
        return jsonify(data)
    return jsonify({"error": "Não encontrado"}), 404


# --- ROTAS PARA DÍVIDAS RECORRENTES ---

@receivables_bp.route("/receivables/add_recurring", methods=["POST"])
@login_required
def add_recurring():
    """Adiciona uma nova REGRA de cobrança recorrente."""
    try:
        debtor_name = request.form.get('recurring_debtor_name')
        description = request.form.get('recurring_description')
        amount = float(request.form.get('recurring_amount'))
        day_of_month = int(request.form.get('recurring_day'))
        
        if not debtor_name or not amount or not day_of_month:
            flash("Nome, valor e dia são obrigatórios.", "danger")
            return redirect(url_for('receivables.index'))
        
        db.add_recurring_receivable(current_user.id, debtor_name, description, amount, day_of_month)
        flash("Cobrança recorrente criada com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao criar recorrente: {e}", "danger")
        
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/receivables/pay_recurring/<int:recurring_id>", methods=["POST"])
@login_required
def pay_recurring(recurring_id):
    """Marca uma conta recorrente como PAGA para o mês ATUAL."""
    try:
        rule = db.get_recurring_receivable_by_id(recurring_id, current_user.id)
        if not rule:
            flash("Regra recorrente não encontrada.", "danger")
            return redirect(url_for('receivables.index'))
        
        # Cria um registro no histórico (tabela 'receivables')
        db.add_receivable(
            user_id=current_user.id,
            debtor_name=rule['debtor_name'],
            description=rule['description'],
            amount=rule['amount'],
            date=datetime.now().strftime('%Y-%m-%d'),
            status='paid', # Já entra como PAGO
            recurring_id=recurring_id # Vincula ao ID da regra
        )
        flash(f"Pagamento de {rule['debtor_name']} registrado!", "success")
    except Exception as e:
        flash(f"Erro ao registrar pagamento: {e}", "danger")
        
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/receivables/delete_recurring/<int:recurring_id>", methods=["POST"])
@login_required
def delete_recurring(recurring_id):
    """Apaga uma REGRA de cobrança recorrente."""
    try:
        db.delete_recurring_receivable(recurring_id, current_user.id)
        flash("Regra recorrente apagada.", "success")
    except Exception as e:
        flash(f"Erro ao apagar regra: {e}", "danger")
        
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/api/recurring_receivable/<int:recurring_id>")
@login_required
def api_get_recurring_receivable(recurring_id):
    """Retorna dados de uma REGRA recorrente para o modal de edição."""
    data = db.get_recurring_receivable_by_id(recurring_id, current_user.id)
    if data:
        return jsonify(data)
    return jsonify({"error": "Não encontrado"}), 404

@receivables_bp.route("/receivables/edit_recurring/<int:recurring_id>", methods=["POST"])
@login_required
def edit_recurring(recurring_id):
    """Edita uma REGRA de cobrança recorrente."""
    try:
        debtor_name = request.form.get('edit_recurring_debtor_name')
        description = request.form.get('edit_recurring_description')
        amount = float(request.form.get('edit_recurring_amount'))
        day_of_month = int(request.form.get('edit_recurring_day'))
        
        db.update_recurring_receivable(recurring_id, current_user.id, debtor_name, description, amount, day_of_month)
        flash("Regra recorrente atualizada!", "success")
    except Exception as e:
        flash(f"Erro ao editar regra: {e}", "danger")
        
    return redirect(url_for('receivables.index'))


# Função que o __init__.py irá chamar
def configure_receivables(app):
    app.register_blueprint(receivables_bp)