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
        # O mês alvo (target) agora será tratado como o Mês de Referência (trabalho/competência)
        m = utils.get_month_range(request.args.get('month'))
        
        # O mês de recebimento principal para o trabalho deste mês é o próximo mês (dia 5, etc)
        payment_month_str = m['next_month']
        payment_month_display = m['next_month_display']

        recurring_rules = db.get_recurring_receivables_by_user(current_user.id)
        # Recorrentes pagas neste mês de recebimento alvo
        paid_in_month_ids = db.get_paid_recurring_ids_for_month(current_user.id, payment_month_str)
        
        pending_recurring = [r for r in recurring_rules if r['id'] not in paid_in_month_ids]
        pending_manual = db.get_receivables_by_user(current_user.id, status='pending')
        
        # --- Cálculo do Ciclo Atual (Dinheiro que entra no mês seguinte referente a este mês) ---
        # 1. Recorrentes que vencem no mês de pagamento alvo
        total_cycle = sum(float(r['amount']) for r in pending_recurring)
        # 2. Manuais cujo Mês de Referência é o mês alvo OU cujo Vencimento é o mês de pagamento alvo
        for r in pending_manual:
            ref = r.get('reference_month') or r['date'][:7]
            payout = r['date'][:7]
            if ref == m['month_str'] or payout == payment_month_str:
                total_cycle += float(r['amount'])
        
        # --- Atrasados + Próximos ---
        total_all_time = sum(float(r['amount']) for r in pending_manual) + sum(float(r['amount']) for r in pending_recurring)

        return render_template('receivables.html', 
                               pending_manual_receivables=pending_manual,
                               pending_recurring=pending_recurring,
                               all_recurring_rules=recurring_rules,
                               paid_history=db.get_paid_receivables_history(current_user.id),
                               total_pending_cycle=total_cycle,
                               total_pending_all_time=total_all_time,
                               target_month_display=m['display'],
                               target_month_str=m['month_str'],
                               payment_month_display=payment_month_display,
                               payment_month_str=payment_month_str,
                               prev_month_str=m['prev_month'],
                               next_month_str=m['next_month'],
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
        ref_month = request.form.get('reference_month')
        db.add_receivable(current_user.id, request.form.get('debtor_name'), request.form.get('description'), 
                          amount, request.form.get('date'), reference_month=ref_month)
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