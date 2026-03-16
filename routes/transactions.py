# routes/transactions.py
import json
from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash, session, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from dateutil.relativedelta import relativedelta
import database as db

transactions_bp = Blueprint('transactions', __name__)

@transactions_bp.route("/", methods=["GET"])
@login_required
def index():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))
    search = request.args.get("search", "")
    category = request.args.get("category", "")
    month_val = request.args.get('month')
    
    if month_val:
        try: target_date = datetime.strptime(month_val, '%Y-%m')
        except ValueError: target_date = datetime.now()
    else: target_date = datetime.now()

    target_month_str = target_date.strftime('%Y-%m')
    target_month_display = target_date.strftime('%b/%Y').capitalize()
    
    prev_month = (target_date - relativedelta(months=1)).strftime('%Y-%m')
    next_month = (target_date + relativedelta(months=1)).strftime('%Y-%m')

    date_from = request.args.get("date_from", target_date.replace(day=1).strftime('%Y-%m-%d'))
    date_to = request.args.get("date_to", (target_date + relativedelta(months=1, days=-1)).strftime('%Y-%m-%d'))
    
    filter_args = {"user_id": current_user.id, "filter_category": category or None, "date_from": date_from, "date_to": date_to, "search": search or None}

    total = db.count_transactions(**filter_args)
    pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page

    rows = db.fetch_transactions(**filter_args, limit=per_page, offset=offset)
    df = db.to_df(rows)
    summary = db.calculate_filtered_summary(**filter_args)
    
    # Adiciona fixas ao resumo se não houver filtro
    if not category and not search:
        info = db.get_salary_info(current_user.id)
        fixed = info.get('salary', 0.0) + info.get('bonus', 0.0)
        # Em transações.index, income/bal são usados para o topo
        # Mas total_income/total_bal (previsto) vêm de summary['total_income'] etc.
    
    categories = [c[1] for c in db.fetch_categories(current_user.id)]
    recurring_rules = db.fetch_recurring_expenses(current_user.id)

    return render_template("index.html",
                           rows=df.to_dict(orient="records") if not df.empty else [],
                           income=summary['paid_income'], expense=summary['paid_expense'], bal=summary['paid_bal'],
                           total_income=summary['total_income'], total_expense=summary['total_expense'], total_bal=summary['total_bal'],
                           categories=categories, recurring_rules=recurring_rules,
                           page=page, pages=pages, per_page=per_page, total=total,
                           target_month_str=target_month_str, target_month_display=target_month_display,
                           prev_month=prev_month, next_month=next_month,
                           date_from=date_from, date_to=date_to, search=search, category=category,
                           datetime=datetime, active_page="transactions")

@transactions_bp.route("/add", methods=["POST"])
@login_required
def add():
    try:
        date = request.form.get("date")
        typ = request.form.get("type")
        category = request.form.get("category")
        status = request.form.get("status", "paid")
        desc = request.form.get("description")
        amount = float(request.form.get("amount").replace(",", "."))
        cat_id = db.get_category_id(category, current_user.id)
        db.add_transaction(current_user.id, date, desc, cat_id, amount, typ, status=status)
        flash("Transação adicionada!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for(".index"))

@transactions_bp.route("/edit/<int:trans_id>", methods=["POST"])
@login_required
def edit(trans_id):
    try:
        date = request.form.get("date")
        typ = request.form.get("type")
        category = request.form.get("category")
        status = request.form.get("status", "paid")
        desc = request.form.get("description")
        amount = float(request.form.get("amount").replace(",", "."))
        cat_id = db.get_category_id(category, current_user.id)
        db.update_transaction(trans_id, current_user.id, date, desc, cat_id, amount, typ, status=status)
        flash("Transação atualizada!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for(".index"))

@transactions_bp.route("/delete/<int:trans_id>", methods=["POST"])
@login_required
def delete(trans_id):
    db.delete_transaction(trans_id, current_user.id)
    flash("Transação excluída!", "success")
    return redirect(url_for(".index"))

@transactions_bp.route("/api/transaction/<int:trans_id>")
@login_required
def api_get_transaction(trans_id):
    t = db.get_transaction_by_id(trans_id, current_user.id)
    return jsonify(t) if t else ({'error': 'Not found'}, 404)

@transactions_bp.route("/settle/<month_str>", methods=["POST"])
@login_required
def settle_month(month_str):
    try:
        db.settle_transactions_for_month(current_user.id, month_str)
        flash(f"Mês {month_str} quitado e fixas geradas!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for(".index", month=month_str))

@transactions_bp.route("/recurrence/add", methods=["POST"])
@login_required
def add_recurrence():
    try:
        desc = request.form.get("description")
        amount = float(request.form.get("amount").replace(",", "."))
        day = int(request.form.get("day"))
        category = request.form.get("category")
        cat_id = db.get_category_id(category, current_user.id)
        db.add_recurring_expense(current_user.id, desc, amount, day, cat_id)
        flash("Regra recorrente adicionada!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for(".index"))

@transactions_bp.route("/recurrence/delete/<int:rule_id>", methods=["POST"])
@login_required
def delete_recurrence(rule_id):
    db.delete_recurring_expense(rule_id, current_user.id)
    flash("Regra recorrente removida!", "success")
    return redirect(url_for(".index"))