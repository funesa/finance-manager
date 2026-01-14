"""
Main Flask application entry point.
"""
import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from datetime import datetime

# --- IMPORTAÇÕES DAS ROTAS ---
from routes.auth import configure_auth
from routes.dashboard import configure_dashboard
from routes.savings import configure_savings
from routes.budgets import configure_budgets
from routes.salary import configure_salary
from routes.transactions import configure_transactions

def create_app():
    """Factory function to create and configure Flask app."""
    app = Flask(__name__)
    
    # Configuração básica
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "fallback-default-key-for-development")
    
    # Configuração do Login Manager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'
    
    # Injeta a variável 'datetime' em todos os templates
    @app.context_processor
    def inject_datetime():
        return {'datetime': datetime}
    
    # --- REGISTRO DOS BLUEPRINTS/ROTAS ---
    configure_auth(app, login_manager)
    configure_dashboard(app)
    configure_savings(app)
    configure_budgets(app)
    configure_salary(app)
    configure_transactions(app)
    
    
    # --- INÍCIO DA CORREÇÃO ---
    #
    # Todos os 'app.add_url_rule' (aliases) foram removidos.
    # Eles não são mais necessários porque o 'layout.html'
    # agora usa os endpoints corretos (ex: 'transactions.index')
    # e eles estavam causando conflitos de rota.
    #
    # --- FIM DA CORREÇÃO ---
    
    return app