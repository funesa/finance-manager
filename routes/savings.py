from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
import os
from datetime import datetime
import database as db

savings_bp = Blueprint('savings', __name__)

@savings_bp.route("/savings")
@login_required
def index():
    savings_list = db.get_savings_for_user(current_user.id)
    return render_template('cofrinho.html',
                        savings=savings_list,
                        has_api=bool(os.getenv('CDI_API_URL')),
                        datetime=datetime
                        )

@savings_bp.route("/savings/add", methods=['POST'])
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

@savings_bp.route("/savings/update_rates", methods=['POST'])
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