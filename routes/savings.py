"""
Savings (Cofrinho) routes and functionality for the web interface.
"""
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
import os
from datetime import datetime  # <-- ADICIONE ESTA IMPORTAÇÃO

# CORRIGIDO: Importando o 'database.py' da raiz
import database as db

def configure_savings(app):
    """Configure savings routes for the Flask app."""
    
    from flask import Blueprint
    savings = Blueprint('savings', __name__)

    @savings.route("/savings")
    @login_required
    def index():
        savings_list = db.get_savings_for_user(current_user.id)
        return render_template('cofrinho.html',
                            savings=savings_list,
                            has_api=bool(os.getenv('CDI_API_URL')),
                            # --- CORREÇÃO AQUI ---
                            datetime=datetime
                            )

    @savings.route("/savings/add", methods=['POST'])
    @login_required
    def add():
        name = request.form.get('name')
        bank = request.form.get('bank')
        bank_code = request.form.get('bank_code')
        balance = float(request.form.get('balance', 0))
        
        if name:
            db.create_saving(current_user.id, name, bank, bank_code, balance)
            flash('Cofrinho criado com sucesso!', 'success')
        else:
            flash('Nome é obrigatório.', 'danger')
            
        return redirect(url_for('savings.index'))

    @savings.route("/savings/update_rates", methods=['POST'])
    @login_required
    def update_rates():
        api_url = os.getenv('CDI_API_URL')
        if not api_url:
            flash('URL da API de CDI não configurada.', 'danger')
            return redirect(url_for('savings.index'))
            
        updated = db.update_all_savings_rates(current_user.id, api_url)
        if updated > 0:
            flash(f'Taxas atualizadas com sucesso! ({updated} cofrinhos)', 'success')
        else:
            flash('Nenhuma taxa atualizada.', 'info')
            
        return redirect(url_for('savings.index'))

    # Register blueprint
    app.register_blueprint(savings)