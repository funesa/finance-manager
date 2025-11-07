"""
Entry point for FinanceManager web application.
"""
import os
import sys

# --- CORREÇÃO DE IMPORTAÇÃO (Versão mais robusta) ---
# 1. Obtenha o caminho absoluto para o diretório onde este arquivo (run.py) está
# Ex: C:\Users\POFJunior\Desktop\FinancialManager (2)
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# 2. Insira este diretório no *início* do caminho de importação do Python
# Isso força o Python a procurar módulos aqui PRIMEIRO.
sys.path.insert(0, PROJECT_ROOT)
# ----------------------------------------------------

# 3. Agora, o Python DEVE ser capaz de encontrar 'database.py' e 'forms.py'
import database
# --- CORREÇÃO AQUI ---
# Importa o 'forms.py' de dentro da pasta 'web'
from web import forms
# ---------------------
from web import create_app

# 4. Garanta que o banco de dados e as tabelas existam
database.init_db()

# 5. Crie a aplicação
app = create_app()

if __name__ == '__main__':
    # debug=True é essencial para desenvolvimento
    
    # --- ALTERAÇÃO AQUI ---
    # Adicionado host='0.0.0.0' para permitir acesso pela rede (IP da sua máquina)
    # Em vez de apenas 'localhost' (127.0.0.1)
    app.run(host='0.0.0.0', port=5000, debug=True)