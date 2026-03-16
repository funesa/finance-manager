# routes/transactions.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import database as db
import utils

transactions_bp = Blueprint('transactions', __name__)

@transactions_bp.route("/", methods=["GET"])
@login_required
def index():
    # Setup locale and common date variables
    utils.setup_locale()
    m = utils.get_month_range(request.args.get('month'))
    
    # Pagination & Filters
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 25))
    search = request.args.get("search", "")
    category = request.args.get("category", "")
    date_from = request.args.get("date_from", m['target_date'].replace(day=1).strftime('%Y-%m-%d'))
    date_to = request.args.get("date_to", (m['target_date'].replace(day=28) + datetime.timedelta(days=4)).replace(day=1).replace(day=1).strftime('%Y-%m-%d')) # Simplified later
    
    # Actual proper end of month
    import calendar
    _, last_day = calendar.monthrange(m['target_date'].year, m['target_date'].month)
    date_to = request.args.get("date_to", f"{m['month_str']}-{last_day}")

    filter_args = {
        "user_id": current_user.id, 
        "filter_category": category or None, 
        "date_from": date_from, 
        "date_to": date_to, 
        "search": search or None
    }

    # Fetch Data
    total = db.count_transactions(**filter_args)
    pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page
    rows = db.fetch_transactions(**filter_args, limit=per_page, offset=offset)
    
    # Summary & Salary Integration
    summary = db.calculate_filtered_summary(**filter_args)
    paid_income = summary['paid_income']
    paid_bal = summary['paid_bal']
    total_income = summary['total_income']
    total_bal = summary['total_bal']

    if not category and not search:
        info = db.get_salary_info(current_user.id)
        fixed = info.get('salary', 0.0) + info.get('bonus', 0.0)
        paid_income += fixed
        paid_bal += fixed
        total_income += fixed
        total_bal += fixed
    
    return render_template("index.html",
                           rows=rows,
                           income=paid_income, expense=summary['paid_expense'], bal=paid_bal,
                           total_income=total_income, total_expense=summary['total_expense'], total_bal=total_bal,
                           categories=[c['name'] for c in db.fetch_categories(current_user.id)], 
                           recurring_rules=db.fetch_recurring_expenses(current_user.id),
                           page=page, pages=pages, per_page=per_page, total=total,
                           target_month_str=m['month_str'], target_month_display=m['display'],
                           prev_month=m['prev_month'], next_month=m['next_month'],
                           date_from=date_from, date_to=date_to, search=search, category=category,
                           datetime=datetime, active_page="transactions")

@transactions_bp.route("/add", methods=["POST"])
@login_required
def add():
    try:
        amount = utils.parse_amount(request.form.get("amount"))
        cat_id = db.get_category_id(request.form.get("category"), current_user.id)
        db.add_transaction(current_user.id, request.form.get("date"), request.form.get("description"), 
                          cat_id, amount, request.form.get("type"), status=request.form.get("status", "paid"))
        flash("Transação adicionada!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for(".index"))

@transactions_bp.route("/edit/<int:trans_id>", methods=["POST"])
@login_required
def edit(trans_id):
    try:
        amount = utils.parse_amount(request.form.get("amount"))
        cat_id = db.get_category_id(request.form.get("category"), current_user.id)
        db.update_transaction(trans_id, current_user.id, request.form.get("date"), request.form.get("description"), 
                             cat_id, amount, request.form.get("type"), status=request.form.get("status", "paid"))
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
        flash(f"Mês {month_str} quitado!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for(".index", month=month_str))

@transactions_bp.route("/recurrence/add", methods=["POST"])
@login_required
def add_recurrence():
    try:
        amount = utils.parse_amount(request.form.get("amount"))
        cat_id = db.get_category_id(request.form.get("category"), current_user.id)
        db.add_recurring_expense(current_user.id, request.form.get("description"), amount, int(request.form.get("day")), cat_id)
        flash("Regra recorrente adicionada!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for(".index"))

@transactions_bp.route("/recurrence/delete/<int:rule_id>", methods=["POST"])
@login_required
def delete_recurrence(rule_id):
    db.delete_recurring_expense(rule_id, current_user.id)
    flash("Regra recorrente removida!", "success")
    return redirect(url_for(".index"))