import os
import sys
from dotenv import load_dotenv

# Carrega .env se existir
load_dotenv()

# Configuração de caminhos para PythonAnywhere
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from web import create_app
import database as db

# Inicializa o banco de dados
db.init_db()

# Cria a aplicação Flask para o servidor WSGI (PythonAnywhere)
application = create_app()
