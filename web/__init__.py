"""
Main Flask application entry point.
"""
import os
import time
from datetime import datetime
from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv

# --- IMPORTAÇÕES DAS ROTAS ---
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.savings import savings_bp
from routes.budgets import budgets_bp
from routes.salary import salary_bp
from routes.transactions import transactions_bp
from routes.receivables import receivables_bp

def create_app():
    """Factory function to create and configure Flask app."""
    
    # Carrega variáveis de ambiente do arquivo .env
    load_dotenv()
    
    # Configuração de diretórios
    WEB_DIR = os.path.abspath(os.path.dirname(__file__))
    ROOT_DIR = os.path.dirname(WEB_DIR)
    STATIC_DIR = os.path.join(ROOT_DIR, 'static')
    
    app = Flask(__name__, root_path=ROOT_DIR, static_folder=STATIC_DIR)
    
    # Configuração básica via variáveis de ambiente
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "fallback-default-key-for-development")
    app.config['ENV'] = os.environ.get("FLASK_ENV", "production")
    
    # Configuração do Login Manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'info'
    
    # Configuração do user_loader no próprio app (ou pode ser movido para auth)
    import database as db
    @login_manager.user_loader
    def load_user(user_id):
        return db.get_user_by_id(int(user_id))
    
    # Injeta variáveis globais nos templates
    @app.context_processor
    def inject_globals():
        return {
            'datetime': datetime,
            'cache_buster': int(time.time())
        }
    
    # --- REGISTRO DOS BLUEPRINTS ---
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(savings_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(salary_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(receivables_bp)
    
    return app