# src/web/routes/auth.py
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app
)
# --- ATUALIZADO ---
from flask_login import login_user, logout_user, current_user, login_required
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

import database as db
# --- CORREÇÃO AQUI ---
# Trocado de 'from forms import' para 'from web.forms import'
# --- ATUALIZADO ---
from web.forms import (
    LoginForm,
    RegistrationForm,
    RequestResetForm,
    ResetPasswordForm,
    ChangePasswordForm  # <-- 1. IMPORT ADICIONADO
)

# Crie o Blueprint
auth_bp = Blueprint('auth', 
                    __name__, 
                    template_folder='../templates')

# --- Funções de Token (Movidas de web.py) ---

def get_reset_token(user, expires_sec=1800):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps({'user_id': user.id})

def verify_reset_token(token):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token, max_age=1800) # Token válido por 30 minutos
        user_id = data.get('user_id')
    except Exception:
        return None
    return db.get_user_by_id(user_id)

def send_reset_email(user):
    token = get_reset_token(user)
    reset_link = url_for('auth.reset_token', token=token, _external=True)
    
    # --- SIMULAÇÃO DE ENVIO DE EMAIL ---
    print("--- SIMULAÇÃO DE RESET DE SENHA ---")
    print(f"Para: {user.email}")
    print(f"Clique neste link para redefinir sua senha (válido por 30 min):")
    print(reset_link)
    print("-----------------------------------")
    # -----------------------------------

# --- Rotas de Autenticação (Movidas de web.py) ---

@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            db.create_user(email=form.email.data, password=form.password.data)
            flash('Sua conta foi criada! Você já pode fazer login.', 'success')
            return redirect(url_for('.login'))
        except Exception as e:
            flash(f'Erro ao criar conta: {e}', 'danger')
    return render_template('register.html', 
                           title='Registrar', 
                           form=form, 
                           active_page="register",
                           datetime=datetime)

@auth_bp.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.get_user_by_email(form.email.data)
        
        if user and user.verify_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
        else:
            flash('Login sem sucesso. Verifique o email e a senha.', 'danger')
    return render_template('login.html', 
                           title='Login', 
                           form=form, 
                           active_page="login",
                           datetime=datetime)

@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('.login'))

@auth_bp.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = db.get_user_by_email(form.email.data)
        if user:
            send_reset_email(user)
        flash('Um link para redefinição de senha foi enviado (VERIFIQUE O CONSOLE DO TERMINAL).', 'info')
        return redirect(url_for('.login'))
    return render_template('reset_request.html', 
                           title='Resetar Senha', 
                           form=form,
                           datetime=datetime)

@auth_bp.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    user = verify_reset_token(token)
    if user is None:
        flash('Este é um link inválido ou expirado.', 'warning')
        return redirect(url_for('.reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        db.update_user_password(user.id, form.password.data)
        flash('Sua senha foi atualizada! Você jÃ¡ pode fazer login.', 'success')
        return redirect(url_for('.login'))
    return render_template('reset_token.html', 
                           title='Resetar Senha', 
                           form=form,
                           datetime=datetime)


# --- 2. NOVA ROTA ADICIONADA AQUI ---
@auth_bp.route("/change_password", methods=['GET', 'POST'])
@login_required # Essencial: só usuários logados podem acessar
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        # 1. Verificar se a senha atual está correta
        if current_user.verify_password(form.current_password.data):
            # 2. Atualizar a senha no banco
            db.update_user_password(current_user.id, form.password.data)
            flash('Sua senha foi alterada com sucesso!', 'success')
            return redirect(url_for('.change_password'))
        else:
            flash('Senha atual incorreta.', 'danger')
    
    return render_template('change_password.html',
                           title='Mudar Senha',
                           form=form,
                           active_page="change_password", # Para destacar o link no menu
                           datetime=datetime)


# --- Função de Configuração (Chamada pelo __init__.py) ---

def configure_auth(app, login_manager):
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.get_user_by_id(int(user_id))

    login_manager.init_app(app)
    app.register_blueprint(auth_bp)