# database.py
import sqlite3
import pandas as pd
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# --- Configuração do Banco de Dados ---
# Tenta obter o caminho do .env primeiro, senão usa o padrão
DATABASE_PATH_ENV = os.environ.get("DATABASE_PATH")
if DATABASE_PATH_ENV:
    DB = Path(DATABASE_PATH_ENV)
else:
    BASE = Path(__file__).parent
    DB = BASE / "finance.db"

def get_conn() -> sqlite3.Connection:
    """Retorna uma conexão com o banco de dados com suporte a dicionário."""
    conn = sqlite3.connect(DB)
    # Habilita o acesso por nome de coluna (dict-like)
    conn.row_factory = sqlite3.Row
    return conn

# --- Classe de Usuário ---
class User(UserMixin):
    def __init__(self, id: int, email: str, password_hash: str):
        self.id = id
        self.email = email
        self.password_hash = password_hash

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

# --- Inicialização do DB ---
def init_db():
    """Cria as tabelas do banco de dados se elas não existirem."""
    with get_conn() as conn:
        cur = conn.cursor()
        
        # Tabela de Usuários
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            );
        """)
        
        # Tabela de Categorias
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        """)
        
        # Tabela de Transações
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
                status TEXT NOT NULL DEFAULT 'paid',
                recurring_id INTEGER, 
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (category_id) REFERENCES categories (id),
                FOREIGN KEY (recurring_id) REFERENCES recurring_expenses (id)
            );
        """)

        # Tabela de Despesas Recorrentes
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recurring_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                day_of_month INTEGER NOT NULL,
                category_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (category_id) REFERENCES categories (id)
            );
        """)
        
        # Tabela de Orçamentos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                month TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                UNIQUE(category_id, month, user_id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (category_id) REFERENCES categories (id)
            );
        """)

        # Tabela de Salário e Bonificações
        cur.execute("""
            CREATE TABLE IF NOT EXISTS salary_info (
                user_id INTEGER PRIMARY KEY,
                salary REAL NOT NULL DEFAULT 0,
                bonus REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        """)

        # Tabela de Cofrinhos
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

        # Tabela de Recebíveis
        cur.execute("""
            CREATE TABLE IF NOT EXISTS receivables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                debtor_name TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                recurring_id INTEGER, 
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (recurring_id) REFERENCES recurring_receivables (id)
            );
        """)
        
        # Tabela de Regras Recorrentes de Recebíveis
        cur.execute("""
            CREATE TABLE IF NOT EXISTS recurring_receivables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                debtor_name TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL,
                day_of_month INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            );
        """)

        # Migrações Automáticas
        migrations = [
            ("receivables", "ALTER TABLE receivables ADD COLUMN recurring_id INTEGER REFERENCES recurring_receivables(id)"),
            ("transactions", "ALTER TABLE transactions ADD COLUMN status TEXT NOT NULL DEFAULT 'paid'"),
            ("transactions", "ALTER TABLE transactions ADD COLUMN recurring_id INTEGER"),
            ("transactions", "ALTER TABLE transactions ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
        ]
        
        for table, sql in migrations:
            try:
                cur.execute(sql)
            except sqlite3.OperationalError:
                pass # Coluna já existe

        conn.commit()

# --- Funções de Usuário ---
def create_user(email: str, password: str) -> int:
    hashed_password = generate_password_hash(password)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, hashed_password))
        user_id = cur.lastrowid
        
        default_categories = ["Salário", "Aluguel", "Mercado", "Transporte", "Lazer", "Contas", "Saúde", "Outros"]
        cat_data = [(name, user_id) for name in default_categories]
        cur.executemany("INSERT INTO categories (name, user_id) VALUES (?, ?)", cat_data)
        conn.commit()
        return user_id

def get_user_by_email(email: str) -> Optional[User]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, email, password_hash FROM users WHERE email = ?", (email,))
        row = cur.fetchone()
        return User(id=row['id'], email=row['email'], password_hash=row['password_hash']) if row else None

def get_user_by_id(user_id: int) -> Optional[User]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, email, password_hash FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return User(id=row['id'], email=row['email'], password_hash=row['password_hash']) if row else None

def update_user_password(user_id: int, new_password: str):
    hashed_password = generate_password_hash(new_password)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_password, user_id))
        conn.commit()

# --- Funções de Categorias ---
def fetch_categories(user_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM categories WHERE user_id = ? ORDER BY name", (user_id,))
        return cur.fetchall()

def create_category(user_id: int, name: str) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO categories (name, user_id) VALUES (?, ?)", (name, user_id))
        conn.commit()
        return cur.lastrowid

def get_category_id(name: str, user_id: int) -> Optional[int]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM categories WHERE name = ? AND user_id = ?", (name, user_id))
        result = cur.fetchone()
        return result['id'] if result else None

# --- Funções de Transações ---
def fetch_transactions(user_id: int, filter_category: str = None, date_from: str = None, date_to: str = None, search: str = None, limit: int = None, offset: int = None, status: str = None) -> List[sqlite3.Row]:
    q = "SELECT t.*, c.name as category FROM transactions t LEFT JOIN categories c ON t.category_id = c.id WHERE t.user_id = ?"
    params = [user_id]
    
    if status:
        q += " AND t.status = ?"
        params.append(status)
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

def count_transactions(user_id: int, filter_category: str = None, date_from: str = None, date_to: str = None, search: str = None) -> int:
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

def add_transaction(user_id: int, date: str, desc: str, category_id: int, amount: float, typ: str, note: str = "", status: str = "paid", recurring_id: int = None):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO transactions(user_id, date, description, category_id, amount, type, note, status, recurring_id) VALUES(?,?,?,?,?,?,?,?,?)",
                    (user_id, date, desc, category_id, amount, typ, note, status, recurring_id))
        conn.commit()

def delete_transaction(trans_id: int, user_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (trans_id, user_id))
        conn.commit()

def update_transaction(trans_id: int, user_id: int, date: str, desc: str, category_id: int, amount: float, typ: str, note: str = "", status: str = "paid"):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE transactions
            SET date = ?, description = ?, category_id = ?, amount = ?, type = ?, note = ?, status = ?
            WHERE id = ? AND user_id = ?
        """, (date, desc, category_id, amount, typ, note, status, trans_id, user_id))
        conn.commit()

# --- Resumo e Utilitários ---
def calculate_filtered_summary(user_id: int, filter_category: str = None, date_from: str = None, date_to: str = None, search: str = None) -> Dict[str, float]:
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

    with get_conn() as conn:
        cur = conn.cursor()
        # Pagos
        cur.execute(base_q + " AND t.status = 'paid' AND t.type = 'income'", params)
        paid_inc = cur.fetchone()[0] or 0.0
        cur.execute(base_q + " AND t.status = 'paid' AND t.type = 'expense'", params)
        paid_exp = cur.fetchone()[0] or 0.0
        # Totais
        cur.execute(base_q + " AND t.type = 'income'", params)
        total_inc = cur.fetchone()[0] or 0.0
        cur.execute(base_q + " AND t.type = 'expense'", params)
        total_exp = cur.fetchone()[0] or 0.0
        
    return {
        "paid_income": paid_inc, "paid_expense": paid_exp, "paid_bal": paid_inc - paid_exp,
        "total_income": total_inc, "total_expense": total_exp, "total_bal": total_inc - total_exp
    }

def to_df(rows: List[sqlite3.Row]) -> pd.DataFrame:
    if not rows: return pd.DataFrame()
    df = pd.DataFrame([dict(r) for r in rows])
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    return df

# --- Dashboard ---
def get_spending_by_category(user_id: int, date_from: str = None, date_to: str = None) -> List[Dict[str, Any]]:
    q = "SELECT c.name, SUM(t.amount) as total FROM transactions t JOIN categories c ON t.category_id = c.id WHERE t.type = 'expense' AND t.user_id = ?"
    params = [user_id]
    if date_from: q += " AND date(t.date) >= date(?)"; params.append(date_from)
    if date_to: q += " AND date(t.date) <= date(?)"; params.append(date_to)
    q += " GROUP BY c.name HAVING total > 0 ORDER BY total DESC"
    
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, params)
        return [{"category": r['name'], "total": r['total']} for r in cur.fetchall()]

def get_daily_summary(user_id: int, days: int = 30) -> List[Dict[str, Any]]:
    q = f"""SELECT date(t.date) as day,
                   SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END) as income,
                   SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END) as expense
            FROM transactions t WHERE date(t.date) >= date('now', '-{days} days') AND t.user_id = ?
            GROUP BY day ORDER BY day ASC"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, (user_id,))
        return [{"date": r['day'], "income": r['income'], "expense": r['expense']} for r in cur.fetchall()]

def get_month_summary(user_id: int, month: str) -> Dict[str, float]:
    base = "SELECT SUM(amount) FROM transactions WHERE user_id = ? AND strftime('%Y-%m', date) = ? AND status = 'paid'"
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(base + " AND type = 'income'", (user_id, month))
        inc = cur.fetchone()[0] or 0.0
        cur.execute(base + " AND type = 'expense'", (user_id, month))
        exp = cur.fetchone()[0] or 0.0
    return {"income": inc, "expenses": exp, "balance": inc - exp}

def get_month_transactions(user_id: int, month: str) -> List[Dict[str, Any]]:
    q = "SELECT t.*, c.name as category FROM transactions t LEFT JOIN categories c ON t.category_id = c.id WHERE t.user_id = ? AND strftime('%Y-%m', t.date) = ?"
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, (user_id, month))
        return [{"id": r['id'], "title": r['description'], "start": r['date'], "category": r['category'], "amount": r['amount'], "type": r['type']} for r in cur.fetchall()]

# --- Orçamentos (Budget) ---
def set_budget(user_id: int, category_id: int, amount: float, month: str):
    if amount <= 0: return delete_budget(user_id, category_id, month)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO budgets (user_id, category_id, amount, month) VALUES (?, ?, ?, ?) ON CONFLICT(category_id, month, user_id) DO UPDATE SET amount = excluded.amount", (user_id, category_id, amount, month))
        conn.commit()

def delete_budget(user_id: int, category_id: int, month: str) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM budgets WHERE user_id = ? AND category_id = ? AND month = ?", (user_id, category_id, month))
        conn.commit()
        return cur.rowcount

def get_budgets_with_spending(user_id: int, month: str) -> List[Dict[str, Any]]:
    q = """SELECT c.id, c.name, b.amount as budgeted, COALESCE(SUM(t.amount), 0) as spent
           FROM categories c LEFT JOIN budgets b ON c.id = b.category_id AND b.month = ? AND b.user_id = ?
           LEFT JOIN transactions t ON c.id = t.category_id AND t.type = 'expense' AND strftime('%Y-%m', t.date) = ? AND t.user_id = ?
           WHERE c.user_id = ? GROUP BY c.id, c.name, b.amount ORDER BY c.name"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, (month, user_id, month, user_id, user_id))
        return [{"category_id": r[0], "category_name": r[1], "budgeted": r[2] or 0, "spent": r[3], "remaining": (r[2] or 0) - r[3]} for r in cur.fetchall()]

# --- Salário ---
def set_salary_info(user_id: int, salary: float, bonus: float):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO salary_info (user_id, salary, bonus) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET salary = excluded.salary, bonus = excluded.bonus", (user_id, salary, bonus))
        conn.commit()

def get_salary_info(user_id: int) -> Dict[str, float]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT salary, bonus FROM salary_info WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return {"salary": row['salary'], "bonus": row['bonus']} if row else {"salary": 0.0, "bonus": 0.0}

# --- Cofrinho ---
def create_saving(user_id: int, name: str, bank: str = None, bank_code: str = None, balance: float = 0.0, cdi_rate: float = None, currency: str = 'BRL') -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO savings (user_id, name, bank, bank_code, balance, cdi_rate, currency) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, name, bank, bank_code, balance, cdi_rate, currency))
        conn.commit()
        return cur.lastrowid

def get_savings_for_user(user_id: int) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM savings WHERE user_id = ? ORDER BY id DESC", (user_id,))
        return [dict(r) for r in cur.fetchall()]

def update_saving_rate(saving_id: int, rate: float):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE savings SET cdi_rate = ?, last_rate_update = ? WHERE id = ?", (rate, datetime.utcnow().isoformat(), saving_id))
        conn.commit()

# --- Recebíveis ---
def add_receivable(user_id: int, debtor_name: str, description: str, amount: float, date: str, status: str = 'pending', recurring_id: int = None):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO receivables (user_id, debtor_name, description, amount, date, status, recurring_id) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, debtor_name, description, amount, date, status, recurring_id))
        conn.commit()

def get_receivables_by_user(user_id: int, status: str = None) -> List[sqlite3.Row]:
    q = "SELECT * FROM receivables WHERE user_id = ? AND recurring_id IS NULL"
    params = [user_id]
    if status: q += " AND status = ?"; params.append(status)
    q += " ORDER BY date DESC"
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(q, params)
        return cur.fetchall()

def get_paid_receivables_history(user_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM receivables WHERE user_id = ? AND status = 'paid' ORDER BY date DESC", (user_id,))
        return cur.fetchall()

def update_receivable_status(receivable_id: int, user_id: int, new_status: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE receivables SET status = ? WHERE id = ? AND user_id = ? AND recurring_id IS NULL", (new_status, receivable_id, user_id))
        conn.commit()

# --- Dívidas Recorrentes ---
def add_recurring_receivable(user_id: int, debtor_name: str, description: str, amount: float, day_of_month: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO recurring_receivables (user_id, debtor_name, description, amount, day_of_month) VALUES (?, ?, ?, ?, ?)", (user_id, debtor_name, description, amount, day_of_month))
        conn.commit()

def get_recurring_receivables_by_user(user_id: int) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM recurring_receivables WHERE user_id = ? ORDER BY day_of_month", (user_id,))
        return [dict(r) for r in cur.fetchall()]

def settle_transactions_for_month(user_id: int, month_str: str):
    with get_conn() as conn:
        cur = conn.cursor()
        # 1. Marcar pendentes
        cur.execute("UPDATE transactions SET status = 'paid' WHERE user_id = ? AND status = 'pendente' AND strftime('%Y-%m', date) = ?", (user_id, month_str))
        # 2. Gerar recorrentes
        cur.execute("SELECT * FROM recurring_expenses WHERE user_id = ?", (user_id,))
        rules = cur.fetchall()
        cur.execute("SELECT recurring_id FROM transactions WHERE user_id = ? AND recurring_id IS NOT NULL AND strftime('%Y-%m', date) = ?", (user_id, month_str))
        paid_ids = {r[0] for r in cur.fetchall()}
        for r in rules:
            if r['id'] not in paid_ids:
                pay_date = f"{month_str}-{str(r['day_of_month']).zfill(2)}"
                cur.execute("INSERT INTO transactions (user_id, date, description, amount, type, category_id, status, recurring_id) VALUES (?, ?, ?, ?, 'expense', ?, 'paid', ?)", (user_id, pay_date, r['description'], r['amount'], r['category_id'], r['id']))
        conn.commit()