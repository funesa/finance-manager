# src/web/routes/transactions.py
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
    
    if not category and not search:
        info = db.get_salary_info(current_user.id)
        fixed = info.get('salary', 0.0) + info.get('bonus', 0.0)
        summary['paid_income'] += fixed
        summary['paid_bal'] += fixed
    
    categories = [c[1] for c in db.fetch_categories(current_user.id)]
    recurring_rules = db.fetch_recurring_expenses(current_user.id)

    return render_template("index.html",
                           rows=df.to_dict(orient="records") if not df.empty else [],
                           income=summary['paid_income'], expense=summary['paid_expense'], bal=summary['paid_bal'],
                           categories=categories, recurring_rules=recurring_rules,
                           page=page, pages=pages, per_page=per_page, total=total,
                           target_month_str=target_month_str, target_month_display=target_month_display,
                           prev_month=prev_month, next_month=next_month,
                           datetime=datetime, active_page="transactions")

@transactions_bp.route("/add", methods=["POST"])
@login_required
def add():
    try:
        date = request.form.get("date")
        typ = request.form.get("type")
        category = request.form.get("category")
        desc = request.form.get("description")
        amount = float(request.form.get("amount").replace(",", "."))
        cat_id = db.get_category_id(category, current_user.id)
        db.add_transaction(current_user.id, date, desc, cat_id, amount, typ)
        flash("Transação adicionada!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for(".index"))

@transactions_bp.route("/delete/<int:trans_id>", methods=["POST"])
@login_required
def delete(trans_id):
    db.delete_transaction(trans_id, current_user.id)
    flash("Transação excluída!", "success")
    return redirect(url_for(".index"))