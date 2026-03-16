import os
import sys
from web import create_app
import database as db

# 1. Garante que o diretório raiz está no path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 2. Inicializa o banco de dados
db.init_db()

# 3. Cria a aplicação
app = create_app()

if __name__ == '__main__':
    # Rodar com debug=True localmente
    print("Iniciando servidor de desenvolvimento...")
    app.run(host='0.0.0.0', port=5001, debug=True)