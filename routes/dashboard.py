"""
Dashboard routes and functionality for the web interface.
"""
import json
from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime  # <-- Certifique-se que 'datetime' está importado

# Importando o 'database.py' da raiz
import database as db

def configure_dashboard(app):
    """Configure dashboard routes for the Flask app."""
    
    from flask import Blueprint
    dashboard = Blueprint('dashboard', __name__)

    @dashboard.route("/dashboard")
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
                                # Dados dos cards superiores
                                month_income=total_income,
                                month_expenses=total_expenses,
                                month_balance=total_balance,
                                salary_info=salary_info,
                                
                                # Dados dos cards inferiores
                                budgets_list=budgets,
                                recent_transactions=recent_transactions_list,
                                
                                # Dados dos Gráficos e Calendário
                                expense_data_json=json.dumps(expense_data),
                                daily_summary_json=json.dumps(daily_summary),
                                current_month=current_month,
                                
                                # --- CORREÇÃO AQUI ---
                                datetime=datetime
                                )

    @dashboard.route("/api/calendar")
    @login_required
    def calendar_events():
        month = request.args.get('month', datetime.now().strftime('%Y-%m'))
        events = db.get_month_transactions(current_user.id, month)
        return jsonify(events)

    # Register blueprint
    app.register_blueprint(dashboard)