from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
import json
import database as db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route("/dashboard")
@login_required
def index():
    current_month = datetime.now().strftime('%Y-%m')
    
    # --- 1. DADOS PARA O RESUMO (CARDS SUPERIORES) ---
    month_summary = db.get_month_summary(current_user.id, current_month)
    salary_info = db.get_salary_info(current_user.id)
    
    total_income = month_summary['income'] + salary_info.get('salary', 0) + salary_info.get('bonus', 0)
    total_expenses = month_summary['expenses']
    total_balance = total_income - total_expenses
    
    # --- 2. DADOS PARA OS CARDS INFERIORES ---
    budgets = db.get_budgets_with_spending(current_user.id, current_month)
    
    recent_rows = db.fetch_transactions(current_user.id, limit=5)
    recent_df = db.to_df(recent_rows)
    recent_transactions_list = recent_df.to_dict(orient='records') if not recent_df.empty else []

    # --- 3. DADOS PARA OS GRÁFICOS (NOVO) ---
    expense_data = db.get_spending_by_category(user_id=current_user.id, date_from=f"{current_month}-01")
    daily_summary = db.get_daily_summary(current_user.id, days=30)

    savings = db.get_savings_for_user(current_user.id)
    total_savings = sum(s['balance'] for s in savings)
    
    return render_template('dashboard.html',
                            month_income=total_income,
                            month_expenses=total_expenses,
                            month_balance=total_balance,
                            salary_info=salary_info,
                            budgets_list=budgets,
                            recent_transactions=recent_transactions_list,
                            expense_data_json=json.dumps(expense_data),
                            daily_summary_json=json.dumps(daily_summary),
                            current_month=current_month,
                            datetime=datetime
                            )

@dashboard_bp.route("/api/calendar")
@login_required
def calendar_events():
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    events = db.get_month_transactions(current_user.id, month)
    return jsonify(events)