# routes/receivables.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import database as db
import utils

receivables_bp = Blueprint('receivables', __name__)

@receivables_bp.route("/receivables")
@login_required
def index():
    try:
        utils.setup_locale()
        m = utils.get_month_range(request.args.get('month'))

        recurring_rules = db.get_recurring_receivables_by_user(current_user.id)
        paid_in_month_ids = db.get_paid_recurring_ids_for_month(current_user.id, m['month_str'])
        
        pending_recurring = [r for r in recurring_rules if r['id'] not in paid_in_month_ids]
        pending_manual = db.get_receivables_by_user(current_user.id, status='pending')
        
        # --- Cálculo Mês Atual ---
        total_this_month = sum(float(r['amount']) for r in pending_recurring)
        total_this_month += sum(float(r['amount']) for r in pending_manual if r['date'][:7] <= m['month_str'])
        
        # --- Cálculo Mês Seguinte ---
        total_next_month = sum(float(r['amount']) for r in recurring_rules)
        total_next_month += sum(float(r['amount']) for r in pending_manual if r['date'][:7] == m['next_month'])

        total_all_time = sum(float(r['amount']) for r in pending_manual) + sum(float(r['amount']) for r in pending_recurring)

        return render_template('receivables.html', 
                               pending_manual_receivables=pending_manual,
                               pending_recurring=pending_recurring,
                               all_recurring_rules=recurring_rules,
                               paid_history=db.get_paid_receivables_history(current_user.id),
                               total_pending_this_month=total_this_month,
                               total_pending_next_month=total_next_month,
                               total_pending_all_time=total_all_time,
                               target_month_display=m['display'],
                               target_month_str=m['month_str'],
                               prev_month_str=m['prev_month'],
                               next_month_str=m['next_month'],
                               next_month_display=m['next_month_display'],
                               today=datetime.now().strftime('%Y-%m-%d'),
                               datetime=datetime)
    except Exception as e:
        flash(f"Erro ao carregar recebíveis: {e}", "danger")
        return redirect(url_for('dashboard.index'))

@receivables_bp.route("/receivables/add_manual", methods=["POST"])
@login_required
def add_manual():
    try:
        amount = utils.parse_amount(request.form.get('amount'))
        db.add_receivable(current_user.id, request.form.get('debtor_name'), request.form.get('description'), amount, request.form.get('date'))
        flash("Conta a receber adicionada!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/receivables/mark_manual_paid/<int:receivable_id>", methods=["POST"])
@login_required
def mark_manual_paid(receivable_id):
    try:
        db.update_receivable_status(receivable_id, current_user.id, 'paid')
        flash("Conta recebida!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/receivables/delete_manual/<int:receivable_id>", methods=["POST"])
@login_required
def delete_manual(receivable_id):
    db.delete_receivable(receivable_id, current_user.id)
    flash("Registro apagado!", "success")
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/receivables/add_recurring", methods=["POST"])
@login_required
def add_recurring():
    try:
        amount = utils.parse_amount(request.form.get('recurring_amount'))
        db.add_recurring_receivable(current_user.id, request.form.get('recurring_debtor_name'), 
                                   request.form.get('recurring_description'), amount, int(request.form.get('recurring_day')))
        flash("Regra recorrente criada!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/receivables/pay_recurring/<int:recurring_id>", methods=["POST"])
@login_required
def pay_recurring(recurring_id):
    try:
        rule = db.get_recurring_receivable_by_id(recurring_id, current_user.id)
        if rule:
            db.add_receivable(current_user.id, rule['debtor_name'], rule['description'], rule['amount'], 
                             datetime.now().strftime('%Y-%m-%d'), status='paid', recurring_id=recurring_id)
            flash("Pagamento registrado!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/receivables/delete_recurring/<int:recurring_id>", methods=["POST"])
@login_required
def delete_recurring(recurring_id):
    db.delete_recurring_receivable(recurring_id, current_user.id)
    flash("Regra removida!", "success")
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/api/receivable/<int:receivable_id>")
@login_required
def api_get_receivable(receivable_id):
    return jsonify(db.get_receivable_by_id(receivable_id, current_user.id) or {'error': 'Not found'})

@receivables_bp.route("/api/recurring_receivable/<int:rule_id>")
@login_required
def api_get_recurring_receivable(rule_id):
    return jsonify(db.get_recurring_receivable_by_id(rule_id, current_user.id) or {'error': 'Not found'})