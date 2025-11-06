"""
Main Flask application entry point.
"""
import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from datetime import datetime
import time 

# --- IMPORTAÇÕES DAS ROTAS ---
from routes.auth import configure_auth
from routes.dashboard import configure_dashboard
from routes.savings import configure_savings
from routes.budgets import configure_budgets
from routes.salary import configure_salary
from routes.transactions import configure_transactions
from routes.receivables import configure_receivables

def create_app():
    """Factory function to create and configure Flask app."""
    
    # --- INÍCIO DA CORREÇÃO (CAMINHO ABSOLUTO) ---
    
    # 1. Descobre o caminho para a pasta 'web' (onde este arquivo está)
    # Ex: C:\Users\POFJunior\Desktop\FinancialManager (2)\web
    WEB_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # 2. Descobre o caminho para a PASTA RAIZ (um nível acima da 'web')
    # Ex: C:\Users\POFJunior\Desktop\FinancialManager (2)
    ROOT_DIR = os.path.dirname(WEB_DIR)
    
    # 3. Descobre o caminho para a pasta 'static' (que está na raiz)
    # Ex: C:\Users\POFJunior\Desktop\FinancialManager (2)\static
    STATIC_DIR = os.path.join(ROOT_DIR, 'static')
    
    # 4. Cria o app Flask dizendo EXATAMENTE onde a pasta 'static' está
    #    e qual é a pasta raiz do projeto.
    app = Flask(__name__, root_path=ROOT_DIR, static_folder=STATIC_DIR)
    
    # --- FIM DA CORREÇÃO ---
    
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
    
    # Injeta o 'cache_buster' para forçar o navegador a recarregar o CSS
    @app.context_processor
    def inject_cache_buster():
        return {'cache_buster': int(time.time())}
    
    # --- REGISTRO DOS BLUEPRINTS/ROTAS ---
    configure_auth(app, login_manager)
    configure_dashboard(app)
    configure_savings(app)
    configure_budgets(app)
    configure_salary(app)
    configure_transactions(app)
    configure_receivables(app)
    
    return app