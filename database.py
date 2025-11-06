# database.py
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# --- Configuração do Banco de Dados ---
BASE = Path(__file__).parent
DB = BASE / "data" / "finance.db"

def get_conn():
    """Retorna uma conexão com o banco de dados."""
    return sqlite3.connect(DB)

# --- Classe de Usuário (NOVO) ---
class User(UserMixin):
    def __init__(self, id, email, password_hash):
        self.id = id
        self.email = email
        self.password_hash = password_hash

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

# --- Inicialização do DB (MODIFICADO) ---
def init_db():
    """Cria as tabelas do banco de dados se elas não existirem."""
    with get_conn() as conn:
        cur = conn.cursor()
        
        # Tabela de Usuários (NOVO)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            );
        """)
        
        # Tabela de Categorias (MODIFICADO: Adicionado user_id)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        """)
        
        # Tabela de Transações (MODIFICADO: Adicionado user_id)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL,
                type TEXT NOT NULL,
                category_id INTEGER,
                note TEXT,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (category_id) REFERENCES categories (id)
            );
        """)
        
        # Tabela de Orçamentos (MODIFICADO: Adicionado user_id)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                month TEXT NOT NULL, -- Formato 'YYYY-MM'
                user_id INTEGER NOT NULL,
                UNIQUE(category_id, month, user_id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (category_id) REFERENCES categories (id)
            );
        """)

        # Tabela de Salário e Bonificações Fixas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS salary_info (
                user_id INTEGER PRIMARY KEY,
                salary REAL NOT NULL DEFAULT 0,
                bonus REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        """)

        # Tabela de Cofrinhos / Reservas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS savings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                bank TEXT,
                bank_code TEXT,
                balance REAL NOT NULL DEFAULT 0,
                cdi_rate REAL DEFAULT NULL,
                last_rate_update TEXT,
                currency TEXT DEFAULT 'BRL',
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        """)

        # Tabela de Contas a Receber (Avulsas/Parceladas E Histórico das Recorrentes)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS receivables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                debtor_name TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', -- 'pending' ou 'paid'
                
                -- Link para a regra recorrente (se aplicável)
                recurring_id INTEGER, 
                
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (recurring_id) REFERENCES recurring_receivables (id)
            );
        """)
        
        # NOVA TABELA para REGRAS RECORRENTES
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recurring_receivables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                debtor_name TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL,
                day_of_month INTEGER NOT NULL, -- Dia do mês (1-31)
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        """)

        # --- INÍCIO DA CORREÇÃO (MIGRAÇÃO) ---
        # Tenta adicionar a nova coluna 'recurring_id' na tabela 'receivables'
        # Isso é necessário se o 'finance.db' já existia antes dessa coluna.
        try:
            cur.execute("ALTER TABLE receivables ADD COLUMN recurring_id INTEGER REFERENCES recurring_receivables(id)")
            print("MIGRAÇÃO: Coluna 'recurring_id' adicionada com sucesso.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                # A coluna já existe, está tudo bem.
                pass
            else:
                # Outro erro, melhor reportar
                print(f"Erro de migração: {e}")
                raise e
        # --- FIM DA CORREÇÃO (MIGRAÇÃO) ---

        conn.commit()
        print("Banco de dados (com todas as tabelas) inicializado com sucesso.")

# --- Funções de Usuário (NOVO) ---

def create_user(email, password):
    """Cria um novo usuário e suas categorias padrão."""
    hashed_password = generate_password_hash(password)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, hashed_password))
        user_id = cur.lastrowid
        conn.commit()
        
        # Adiciona categorias padrão para o NOVO usuário
        default_categories = ["Salário", "Aluguel", "Mercado", "Transporte", "Lazer", "Contas", "Saúde", "Outros"]
        cat_data = [(name, user_id) for name in default_categories]
        cur.executemany("INSERT INTO categories (name, user_id) VALUES (?, ?)", cat_data)
        conn.commit()
        return user_id

def get_user_by_email(email):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, email, password_hash FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        if row:
            return User(id=row[0], email=row[1], password_hash=row[2])
        return None

def get_user_by_id(user_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, email, password_hash FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            return User(id=row[0], email=row[1], password_hash=row[2])
        return None

def update_user_password(user_id, new_password):
    hashed_password = generate_password_hash(new_password)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_password, user_id))
        conn.commit()

# --- Funções de Categorias (MODIFICADO: Requer user_id) ---
def fetch_categories(user_id):
    """Busca todas as categorias (id, name) de um usuário específico."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM categories WHERE user_id = ? ORDER BY name", (user_id,))
        return cur.fetchall()

def create_category(user_id, name):
    """Cria uma nova categoria para o usuário e retorna seu id."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO categories (name, user_id) VALUES (?, ?)", (name, user_id))
        conn.commit()
        return cur.lastrowid

def get_category_id(name, user_id):
    """Busca o ID de uma categoria pelo nome para um usuário específico."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM categories WHERE name = ? AND user_id = ?", (name, user_id))
        result = cur.fetchone()
        return result[0] if result else None

# --- Funções de Transações (MODIFICADO: Requer user_id) ---
def fetch_transactions(user_id, filter_category=None, date_from=None, date_to=None, search=None, limit=None, offset=None):
    """Busca transações de um usuário com filtros, pesquisa e paginação."""
    q = "SELECT t.id, t.date, t.description, c.name as category, t.amount, t.type, t.note FROM transactions t LEFT JOIN categories c ON t.category_id = c.id WHERE t.user_id = ?"
    params = [user_id]
    
    if filter_category:
        q += " AND c.name = ?"
        params.append(filter_category)
    if date_from:
        q += " AND date(t.date) >= date(?)"
        params.append(date_from)
    if date_to:
        q += " AND date(t.date) <= date(?)"
        params.append(date_to)
    if search:
        q += " AND (t.description LIKE ? OR c.name LIKE ? OR t.note LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        
    q += " ORDER BY date(t.date) DESC, t.id DESC"
    
    if limit:
        q += " LIMIT ?"
        params.append(limit)
    if offset:
        q += " OFFSET ?"
        params.append(offset)
        
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, params)
        return cur.fetchall()

def count_transactions(user_id, filter_category=None, date_from=None, date_to=None, search=None):
    """Conta transações de um usuário com base nos filtros (para paginação)."""
    q = "SELECT COUNT(*) FROM transactions t LEFT JOIN categories c ON t.category_id = c.id WHERE t.user_id = ?"
    params = [user_id]
    
    if filter_category:
        q += " AND c.name = ?"
        params.append(filter_category)
    if date_from:
        q += " AND date(t.date) >= date(?)"
        params.append(date_from)
    if date_to:
        q += " AND date(t.date) <= date(?)"
        params.append(date_to)
    if search:
        q += " AND (t.description LIKE ? OR c.name LIKE ? OR t.note LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, params)
        return cur.fetchone()[0]

def add_transaction(user_id, date, desc, category_id, amount, typ, note=""):
    """Adiciona uma nova transação para um usuário."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO transactions(user_id, date,description,category_id,amount,type,note) VALUES(?,?,?,?,?,?,?)",
                    (user_id, date, desc, category_id, amount, typ, note))
        conn.commit()

def delete_transaction(trans_id, user_id):
    """Exclui uma transação pelo ID, verificando se pertence ao usuário."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (trans_id, user_id))
        conn.commit()

def update_transaction(trans_id, user_id, date, desc, category_id, amount, typ, note=""):
    """Atualiza uma transação verificando propriedade pelo usuário."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE transactions
            SET date = ?, description = ?, category_id = ?, amount = ?, type = ?, note = ?
            WHERE id = ? AND user_id = ?
        """, (date, desc, category_id, amount, typ, note, trans_id, user_id))
        conn.commit()

# --- Funções de Resumo e Utilitários (MODIFICADO: Requer user_id) ---

def calculate_filtered_summary(user_id, filter_category=None, date_from=None, date_to=None, search=None):
    """Calcula o resumo (receita, despesa, saldo) de um usuário com base nos filtros."""
    base_q = "SELECT SUM(t.amount) FROM transactions t LEFT JOIN categories c ON t.category_id = c.id WHERE t.user_id = ?"
    params = [user_id]
    
    if filter_category:
        base_q += " AND c.name = ?"
        params.append(filter_category)
    if date_from:
        base_q += " AND date(t.date) >= date(?)"
        params.append(date_from)
    if date_to:
        base_q += " AND date(t.date) <= date(?)"
        params.append(date_to)
    if search:
        base_q += " AND (t.description LIKE ? OR c.name LIKE ? OR t.note LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    q_income = base_q + " AND t.type = 'income'"
    q_expense = base_q + " AND t.type = 'expense'"
    
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q_income, params)
        income = cur.fetchone()[0] or 0.0
        cur.execute(q_expense, params)
        expense = cur.fetchone()[0] or 0.0
        
    return income, expense, income - expense

def to_df(rows):
    """Converte as linhas do banco de dados em um DataFrame Pandas."""
    columns = ["id", "date", "description", "category", "amount", "type", "note"]
    df = pd.DataFrame(rows, columns=columns)
    if not df.empty:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    return df

# --- Funções de Dashboard (MODIFICADO: Requer user_id) ---

def get_spending_by_category(user_id, date_from=None, date_to=None):
    """Retorna o total de despesas de um usuário agrupado por categoria."""
    q = "SELECT c.name, SUM(t.amount) as total FROM transactions t JOIN categories c ON t.category_id = c.id WHERE t.type = 'expense' AND t.user_id = ?"
    params = [user_id]
    
    if date_from:
        q += " AND date(t.date) >= date(?)"
        params.append(date_from)
    if date_to:
        q += " AND date(t.date) <= date(?)"
        params.append(date_to)
        
    q += " GROUP BY c.name HAVING total > 0 ORDER BY total DESC"
    
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, params)
        return [{"category": row[0], "total": row[1]} for row in cur.fetchall()]

def get_daily_summary(user_id, days=30):
    """Retorna o total de receitas e despesas de um usuário por dia."""
    q = f"""
    SELECT 
        date(t.date) as day,
        SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END) as income,
        SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END) as expense
    FROM transactions t
    WHERE date(t.date) >= date('now', '-{days} days') AND t.user_id = ?
    GROUP BY day
    ORDER BY day ASC
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, (user_id,))
        return [{"date": row[0], "income": row[1], "expense": row[2]} for row in cur.fetchall()]

def get_month_summary(user_id, month):
    """
    Calcula o resumo (receita, despesa, saldo) de um usuário para um mês específico.
    'month' deve estar no formato 'YYYY-MM'.
    """
    base_q = "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND strftime('%Y-%m', date) = ?"
    params = (user_id, month)

    q_income = base_q + " AND type = 'income'"
    q_expense = base_q + " AND type = 'expense'"
    
    with get_conn() as conn:
        cur = conn.cursor()
        
        cur.execute(q_income, params)
        income = cur.fetchone()[0] or 0.0
        
        cur.execute(q_expense, params)
        expense = cur.fetchone()[0] or 0.0
        
    return {
        "income": income,
        "expenses": expense,
        "balance": income - expense
    }

def get_month_transactions(user_id, month):
    """
    Retorna todas as transações de um usuário para um mês específico (formato 'YYYY-MM').
    Usado pela API do calendário no dashboard.
    """
    q = """
        SELECT t.id, t.date, t.description, c.name as category, t.amount, t.type
        FROM transactions t 
        LEFT JOIN categories c ON t.category_id = c.id 
        WHERE t.user_id = ? AND strftime('%Y-%m', t.date) = ?
        ORDER BY t.date ASC
    """
    params = (user_id, month)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, params)
        rows = cur.fetchall()
        events = []
        for row in rows:
            # Formata os dados para o FullCalendar (ou outra API de calendário)
            events.append({
                "id": row[0],
                "title": row[2] or "Transação", 
                "start": row[1], # 'YYYY-MM-DD'
                "category": row[3],
                "amount": row[4],
                "type": row[5]
            })
        return events


# --- Funções de Orçamento (Budget) (MODIFICADO: Requer user_id) ---

def set_budget(user_id, category_id, amount, month):
    """Define ou atualiza o orçamento de um usuário para uma categoria/mês."""
    if amount <= 0:
        # Se o valor for 0 ou negativo, remove o orçamento
        delete_budget(user_id, category_id, month)
        return

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO budgets (user_id, category_id, amount, month) VALUES (?, ?, ?, ?)
            ON CONFLICT(category_id, month, user_id) DO UPDATE SET amount = excluded.amount
        """, (user_id, category_id, amount, month))
        conn.commit()

def delete_budget(user_id, category_id, month):
    """Remove o orçamento de uma categoria para um mês (se existir)."""
    print(f"Tentando excluir orçamento: user_id={user_id}, category_id={category_id}, month={month}")
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            
            # Remove diretamente da tabela budgets
            cur.execute("""
                DELETE FROM budgets 
                WHERE user_id = ? AND category_id = ? AND month = ?
            """, (user_id, category_id, month))
            
            deleted = cur.rowcount
            print(f"Registros deletados: {deleted}")

            # Força commit das alterações
            conn.commit()

            return deleted
    except Exception as e:
        print(f"Erro ao excluir orçamento no banco: {str(e)}")
        raise e

def get_budgets_with_spending(user_id, month):
    """Busca todos os orçamentos de um usuário para um mês e calcula o gasto atual."""
    q = """
    SELECT 
        c.id as category_id,
        c.name as category_name,
        b.amount as budgeted_amount,
        COALESCE(SUM(t.amount), 0) as spent_amount
    FROM categories c
    LEFT JOIN budgets b ON c.id = b.category_id 
        AND b.month = ? 
        AND b.user_id = ?
    LEFT JOIN transactions t ON c.id = t.category_id 
        AND t.type = 'expense' 
        AND strftime('%Y-%m', t.date) = ?
        AND t.user_id = ?
    WHERE c.user_id = ?
    GROUP BY c.id, c.name, b.amount
    ORDER BY c.name
    """
    params = (month, user_id, month, user_id, user_id)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, params)
        result = [
            {
                "category_id": row[0],
                "category_name": row[1],
                "budgeted": row[2] if row[2] is not None else 0,
                "spent": row[3],
                "remaining": (row[2] if row[2] is not None else 0) - row[3]
            } 
            for row in cur.fetchall()
        ]

    return result

# --- FUNÇÕES MOVIDAS DO TOPO DO ARQUIVO ---
def set_salary_info(user_id, salary, bonus):
    """Define ou atualiza salário líquido e bonificações fixas do usuário."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO salary_info (user_id, salary, bonus) VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET salary = excluded.salary, bonus = excluded.bonus
        """, (user_id, salary, bonus))
        conn.commit()

def get_salary_info(user_id):
    """Obtém salário líquido e bonificações fixas do usuário."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT salary, bonus FROM salary_info WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            return {"salary": row[0], "bonus": row[1]}
        return {"salary": 0.0, "bonus": 0.0}

# --- Funções para Cofrinho / Savings ---
def create_saving(user_id, name, bank=None, bank_code=None, balance=0.0, cdi_rate=None, currency='BRL'):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO savings (user_id, name, bank, bank_code, balance, cdi_rate, currency) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, name, bank, bank_code, balance, cdi_rate, currency))
        conn.commit()
        return cur.lastrowid


def get_savings_for_user(user_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, bank, bank_code, balance, cdi_rate, last_rate_update, currency FROM savings WHERE user_id = ? ORDER BY id DESC", (user_id,))
        rows = cur.fetchall()
        return [
            {"id": r[0], "name": r[1], "bank": r[2], "bank_code": r[3], "balance": r[4], "cdi_rate": r[5], "last_rate_update": r[6], "currency": r[7]} for r in rows
        ]


def update_saving_rate(saving_id, rate):
    from datetime import datetime as _dt
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE savings SET cdi_rate = ?, last_rate_update = ? WHERE id = ?", (rate, _dt.utcnow().isoformat(), saving_id))
        conn.commit()


def update_all_savings_rates(user_id, api_url):
    """Tenta atualizar taxas para os savings do usuário usando api_url (o endpoint é responsabilidade do deploy)."""
    import requests
    updated = 0
    savings = get_savings_for_user(user_id)
    for s in savings:
        try:
            # envia informação do banco para a API e espera receber {"rate": 12.34}
            payload = {"bank": s.get('bank'), "bank_code": s.get('bank_code')}
            resp = requests.get(api_url, params=payload, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                rate = data.get('rate') or data.get('cdi')
                if rate is not None:
                    update_saving_rate(s['id'], float(rate))
                    updated += 1
        except Exception:
            continue
    return updated


def get_saving_by_id(saving_id):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, bank, bank_code, balance, cdi_rate, last_rate_update, currency FROM savings WHERE id = ?", (saving_id,))
        r = cur.fetchone()
        if not r:
            return None
        return {"id": r[0], "name": r[1], "bank": r[2], "bank_code": r[3], "balance": r[4], "cdi_rate": r[5], "last_rate_update": r[6], "currency": r[7]}

def delete_category_if_unused(user_id, category_id):
    """Deleta a categoria se o usuário não tiver transações vinculadas a ela.
    Retorna True se deletou, False se não havia categoria, lança ValueError se houver transações.
    """
    with get_conn() as conn:
        cur = conn.cursor()
        # Verifica se existem transações para essa categoria
        cur.execute("SELECT COUNT(*) FROM transactions WHERE category_id = ? AND user_id = ?", (category_id, user_id))
        cnt = cur.fetchone()[0] or 0
        print(f"Transações encontradas para categoria {category_id}: {cnt}")
        if cnt > 0:
            raise ValueError('Categoria possui transações e não pode ser removida.')

        # Tenta deletar a categoria
        cur.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (category_id, user_id))
        deleted = cur.rowcount
        conn.commit()
        print(f"Categorias deletadas: {deleted}")
        return deleted > 0

def get_budget_summary(user_id, month):
    """Retorna o total orçado vs. total gasto de um usuário para um mês."""
    q_budget = "SELECT SUM(amount) FROM budgets WHERE month = ? AND user_id = ?"
    q_spent = "SELECT SUM(t.amount) FROM transactions t JOIN categories c ON t.category_id = c.id WHERE t.type = 'expense' AND strftime('%Y-%m', t.date) = ? AND t.user_id = ?"
    
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q_budget, (month, user_id))
        total_budgeted = cur.fetchone()[0] or 0.0
        
        cur.execute(q_spent, (month, user_id))
        total_spent = cur.fetchone()[0] or 0.0
        
    remaining = total_budgeted - total_spent
    percentage = (total_spent / total_budgeted) * 100 if total_budgeted > 0 else 0
    
    return {
        "budgeted": total_budgeted,
        "spent": total_spent,
        "remaining": remaining,
        "percentage": percentage
    }

# --- INÍCIO DA IMPLEMENTAÇÃO (RECEBÍVEIS - AJUSTADA) ---
def add_receivable(user_id, debtor_name, description, amount, date, status='pending', recurring_id=None):
    """Adiciona uma nova conta a receber (avulsa ou como histórico de recorrente)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO receivables (user_id, debtor_name, description, amount, date, status, recurring_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, debtor_name, description, amount, date, status, recurring_id)
        )
        conn.commit()

def get_receivables_by_user(user_id, status=None):
    """Busca contas a receber (APENAS AVULSAS/PARCELADAS) por status."""
    q = "SELECT id, debtor_name, description, amount, date, status FROM receivables WHERE user_id = ? AND recurring_id IS NULL"
    params = [user_id]
    
    if status:
        q += " AND status = ?"
        params.append(status)
        
    q += " ORDER BY date DESC"
    
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, params)
        return cur.fetchall()

def get_paid_receivables_history(user_id):
    """Busca O HISTÓRICO de todas as contas pagas (avulsas + recorrentes)."""
    q = "SELECT id, debtor_name, description, amount, date, status FROM receivables WHERE user_id = ? AND status = 'paid' ORDER BY date DESC"
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, (user_id,))
        return cur.fetchall()


def update_receivable_status(receivable_id, user_id, new_status):
    """Muda o status de uma dívida avulsa/parcelada (ex: 'paid' ou 'pending')."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE receivables SET status = ? WHERE id = ? AND user_id = ? AND recurring_id IS NULL",
            (new_status, receivable_id, user_id)
        )
        conn.commit()

def delete_receivable(receivable_id, user_id):
    """Exclui uma conta a receber (avulsa/parcelada OU um registro de histórico)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM receivables WHERE id = ? AND user_id = ?", (receivable_id, user_id))
        conn.commit()

def get_receivable_by_id(receivable_id, user_id):
    """Busca uma única conta a receber avulsa/parcelada para edição."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, debtor_name, description, amount, date FROM receivables WHERE id = ? AND user_id = ? AND recurring_id IS NULL", (receivable_id, user_id))
        row = cur.fetchone()
        if row:
            return {'id': row[0], 'debtor_name': row[1], 'description': row[2], 'amount': row[3], 'date': row[4]}
        return None

def update_receivable(receivable_id, user_id, debtor_name, description, amount, date):
    """Atualiza os dados de uma conta a receber avulsa/parcelada (Editar)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE receivables SET debtor_name = ?, description = ?, amount = ?, date = ? WHERE id = ? AND user_id = ? AND recurring_id IS NULL",
            (debtor_name, description, amount, date, receivable_id, user_id)
        )
        conn.commit()

# --- Novas Funções para Dívidas RECORRENTES ---

def add_recurring_receivable(user_id, debtor_name, description, amount, day_of_month):
    """Adiciona uma nova REGRA de conta a receber recorrente."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO recurring_receivables (user_id, debtor_name, description, amount, day_of_month) VALUES (?, ?, ?, ?, ?)",
            (user_id, debtor_name, description, amount, day_of_month)
        )
        conn.commit()

def get_recurring_receivables_by_user(user_id):
    """Busca todas as REGRAS de contas a receber recorrentes."""
    q = "SELECT id, debtor_name, description, amount, day_of_month FROM recurring_receivables WHERE user_id = ? ORDER BY day_of_month"
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, (user_id,))
        # Retorna como lista de dicionários para facilitar
        rows = cur.fetchall()
        return [{'id': r[0], 'debtor_name': r[1], 'description': r[2], 'amount': r[3], 'day_of_month': r[4]} for r in rows]

def get_paid_recurring_ids_for_month(user_id, month_str):
    """Busca os IDs das regras recorrentes que JÁ FORAM PAGAS este mês."""
    q = """
        SELECT DISTINCT recurring_id 
        FROM receivables 
        WHERE user_id = ? 
          AND status = 'paid' 
          AND recurring_id IS NOT NULL 
          AND strftime('%Y-%m', date) = ?
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, (user_id, month_str))
        # Retorna um set (conjunto) para busca rápida, ex: {1, 5, 10}
        return {row[0] for row in cur.fetchall()}

def delete_recurring_receivable(recurring_id, user_id):
    """Exclui uma REGRA de conta a receber recorrente."""
    with get_conn() as conn:
        cur = conn.cursor()
        # Opcional: Desvincular registros históricos. Por enquanto, vamos só apagar a regra.
        # Se houver 'ON DELETE SET NULL' na FK, os históricos serão mantidos.
        # Como não definimos, vamos apagar em cascata (ou falhar se houver restrição)
        # Por segurança, vamos primeiro desvincular o histórico:
        cur.execute("UPDATE receivables SET recurring_id = NULL WHERE recurring_id = ? AND user_id = ?", (recurring_id, user_id))
        cur.execute("DELETE FROM recurring_receivables WHERE id = ? AND user_id = ?", (recurring_id, user_id))
        conn.commit()

def get_recurring_receivable_by_id(recurring_id, user_id):
    """Busca uma única REGRA recorrente para edição."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, debtor_name, description, amount, day_of_month FROM recurring_receivables WHERE id = ? AND user_id = ?", (recurring_id, user_id))
        row = cur.fetchone()
        if row:
            return {'id': row[0], 'debtor_name': row[1], 'description': row[2], 'amount': row[3], 'day_of_month': row[4]}
        return None

def update_recurring_receivable(recurring_id, user_id, debtor_name, description, amount, day_of_month):
    """Atualiza os dados de uma REGRA recorrente (Editar)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE recurring_receivables SET debtor_name = ?, description = ?, amount = ?, day_of_month = ? WHERE id = ? AND user_id = ?",
            (debtor_name, description, amount, day_of_month, recurring_id, user_id)
        )
        conn.commit()
# --- FIM DA IMPLEMENTAÇÃO ---


if __name__ == "__main__":
    print("Inicializando o banco de dados...")
    init_db()