# src/web/routes/transactions.py
import json
from flask import (
    Blueprint, render_template, request, redirect, url_for, send_file, flash, json,
    session, jsonify  # <-- ADICIONADO 'session' E 'jsonify'
)
from flask_login import login_required, current_user
from datetime import datetime, timezone

import database as db
from helpers.export import dataframe_to_excel_bytes, dataframe_to_pdf_bytes

transactions_bp = Blueprint('transactions', 
                            __name__, 
                            template_folder='../templates')


@transactions_bp.route("/", methods=["GET"])
@login_required
def index():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))
    search = request.args.get("search", "")
    category = request.args.get("category", "")
    
    date_from_form = request.args.get("date_from", "")
    date_to_form = request.args.get("date_to", "")
    
    date_from_filter = date_from_form
    date_to_filter = date_to_form
    
    is_default_month_view = False
    
    if not date_from_form and not date_to_form:
        is_default_month_view = True
        now = datetime.now(timezone.utc)
        date_from_filter = now.replace(day=1).strftime('%Y-%m-%d')
    
    filter_args = {
        "user_id": current_user.id,
        "filter_category": (category or None),
        "date_from": (date_from_filter or None),
        "date_to": (date_to_filter or None),
        "search": (search or None)
    }

    total = db.count_transactions(**filter_args)
    pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page

    rows = db.fetch_transactions(**filter_args, limit=per_page, offset=offset)
    df = db.to_df(rows)
    
    income, expense, bal = db.calculate_filtered_summary(**filter_args)
    
    if is_default_month_view:
        salary_info = db.get_salary_info(current_user.id)
        income += salary_info.get('salary', 0)
        income += salary_info.get('bonus', 0)
        bal = income - expense
    
    categories = [c[1] for c in db.fetch_categories(current_user.id)]

    return render_template("index.html",
                           rows=df.to_dict(orient="records"),
                           income=income,
                           expense=expense,
                           bal=bal,
                           categories=categories,
                           page=page,
                           pages=pages,
                           per_page=per_page,
                           total=total,
                           search=search,
                           category=category,
                           date_from=date_from_form,
                           date_to=date_to_form,
                           active_page="transactions",
                           today=datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                           datetime=datetime
                           )

@transactions_bp.route("/add", methods=["POST"])
@login_required
def add():
    try:
        date = request.form.get("date")
        typ = request.form.get("type")
        category = request.form.get("category")
        desc = request.form.get("description")
        amount = request.form.get("amount")
        note = request.form.get("note", "") 

        if not amount:
            flash("Informe o valor", "danger")
            return redirect(url_for(".index"))
        
        value = float(amount.replace(",", "."))
        
        cat_id = db.get_category_id(category, current_user.id)
        if cat_id is None:
            flash("Categoria inválida", "danger")
            return redirect(url_for(".index"))

        db.add_transaction(current_user.id, date, desc, cat_id, value, typ, note)
        flash("Transação adicionada com sucesso", "success")
    except Exception as e:
        flash(f"Erro ao adicionar: {e}", "danger")
    return redirect(url_for(".index"))

@transactions_bp.route("/delete/<int:trans_id>", methods=["POST"])
@login_required
def delete(trans_id):
    try:
        db.delete_transaction(trans_id, current_user.id)
        flash("Transação excluída", "success")
    except Exception as e:
        flash(f"Erro ao excluir: {e}", "danger")
    return redirect(url_for(".index"))

@transactions_bp.route("/export/excel")
@login_required
def export_excel():
    filter_args = {
        "user_id": current_user.id,
        "search": request.args.get("search", ""),
        "filter_category": request.args.get("category", ""),
        "date_from": request.args.get("date_from", ""),
        "date_to": request.args.get("date_to", "")
    }
    filter_args = {k: v for k, v in filter_args.items() if v} 
    
    rows = db.fetch_transactions(**filter_args)
    df = db.to_df(rows)
    buf = dataframe_to_excel_bytes(df)
    return send_file(buf, download_name="transactions.xlsx", as_attachment=True, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@transactions_bp.route("/export/pdf")
@login_required
def export_pdf():
    filter_args = {
        "user_id": current_user.id,
        "search": request.args.get("search", ""),
        "filter_category": request.args.get("category", ""),
        "date_from": request.args.get("date_from", ""),
        "date_to": request.args.get("date_to", "")
    }
    filter_args = {k: v for k, v in filter_args.items() if v}
    
    rows = db.fetch_transactions(**filter_args)
    df = db.to_df(rows)
    buf = dataframe_to_pdf_bytes(df)
    if buf is None:
        flash("reportlab não disponível para gerar PDF", "warning")
        return redirect(url_for(".index"))
    return send_file(buf, download_name="transactions.pdf", as_attachment=True, mimetype="application/pdf")

@transactions_bp.route('/api/transaction/<int:trans_id>')
@login_required
def api_get_transaction(trans_id):
    """Retorna JSON com dados da transação (sepertencer ao usuário)."""
    try:
        rows = db.fetch_transactions(current_user.id)
        for r in rows:
            if r[0] == trans_id:
                # map: id, date, description, category, amount, type, note
                return json.dumps({
                    'id': r[0], 'date': r[1], 'description': r[2] or '', 'category': r[3] or '',
                    'amount': r[4], 'type': r[5], 'note': r[6] or ''
                })
    except Exception:
        pass
    return json.dumps({}), 404


@transactions_bp.route('/edit/<int:trans_id>', methods=['POST'])
@login_required
def edit_transaction(trans_id):
    try:
        date = request.form.get('date')
        typ = request.form.get('type')
        category = request.form.get('category')
        desc = request.form.get('description')
        amount = request.form.get('amount')
        note = request.form.get('note', '')

        if not amount:
            flash('Informe o valor', 'danger')
            return redirect(url_for('.index'))
        value = float(amount.replace(',', '.'))

        cat_id = db.get_category_id(category, current_user.id)
        if cat_id is None:
            flash('Categoria inválida', 'danger')
            return redirect(url_for('.index'))

        db.update_transaction(trans_id, current_user.id, date, desc, cat_id, value, typ, note)
        flash('Transação atualizada com sucesso', 'success')
    except Exception as e:
        flash(f'Erro ao editar transação: {e}', 'danger')
    return redirect(url_for('.index'))


# --- ROTA PARA O AVISO BETA ---
@transactions_bp.route("/api/accept_warning", methods=["POST"])
@login_required
def accept_warning():
    """Define na sessão que o usuário está ciente do aviso."""
    session['is_aware'] = True
    return jsonify({"status": "ok"}), 200


# --- ROTA ADICIONADA PARA O TUTORIAL ---
@transactions_bp.route("/api/finish_tutorial", methods=["POST"])
@login_required
def finish_tutorial():
    """Marca na sessão que o usuário já viu o tutorial."""
    session['has_seen_tutorial'] = True
    return jsonify({"status": "ok"}), 200
# --- FIM DA ROTA ADICIONADA ---


# Função que o __init__.py irá chamar
def configure_transactions(app):
    app.register_blueprint(transactions_bp)