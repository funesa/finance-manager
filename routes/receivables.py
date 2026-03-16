# routes/receivables.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from dateutil.relativedelta import relativedelta
import locale
import database as db

receivables_bp = Blueprint('receivables', __name__)

@receivables_bp.route("/receivables")
@login_required
def index():
    try:
        try:
            locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        except locale.Error:
            locale.setlocale(locale.LC_TIME, '')

        month_val = request.args.get('month')
        if month_val:
            try: target_date = datetime.strptime(month_val, '%Y-%m')
            except ValueError: target_date = datetime.now()
        else: target_date = datetime.now()

        target_month_str = target_date.strftime('%Y-%m')
        target_month_display = target_date.strftime('%b/%Y').capitalize()
        
        prev_month_str = (target_date - relativedelta(months=1)).strftime('%Y-%m')
        next_month_str = (target_date + relativedelta(months=1)).strftime('%Y-%m')
        next_month_display = (target_date + relativedelta(months=1)).strftime('%b/%Y').capitalize()

        recurring_rules = db.get_recurring_receivables_by_user(current_user.id)
        paid_in_target_month_ids = db.get_paid_recurring_ids_for_month(current_user.id, target_month_str)
        pending_recurring_list = [rule for rule in recurring_rules if rule['id'] not in paid_in_target_month_ids]
        
        pending_manual = db.get_receivables_by_user(current_user.id, status='pending')
        paid_history = db.get_paid_receivables_history(current_user.id)
        
        total_pending_target_month = sum(float(rule.get('amount', 0)) for rule in pending_recurring_list)
        for row in pending_manual:
            try:
                val = float(row['amount'])
                if row['date'] <= target_month_str + "-31": total_pending_target_month += val
            except: continue
        
        total_pending_all_time = sum(float(row['amount']) for row in pending_manual)
        total_pending_all_time += sum(float(rule.get('amount', 0)) for rule in pending_recurring_list)

        return render_template('receivables.html', 
                               pending_manual_receivables=pending_manual,
                               pending_recurring=pending_recurring_list,
                               all_recurring_rules=recurring_rules,
                               paid_history=paid_history,
                               total_pending_this_month=total_pending_target_month,
                               total_pending_all_time=total_pending_all_time,
                               target_month_display=target_month_display,
                               target_month_str=target_month_str,
                               prev_month_str=prev_month_str,
                               next_month_str=next_month_str,
                               datetime=datetime
                               )
    except Exception as e:
        flash(f"Erro ao carregar recebíveis: {e}", "danger")
        return redirect(url_for('dashboard.index'))

@receivables_bp.route("/receivables/add_manual", methods=["POST"])
@login_required
def add_manual():
    try:
        debtor = request.form.get('debtor_name')
        desc = request.form.get('description')
        amount = float(request.form.get('amount'))
        date = request.form.get('date')
        db.add_receivable(current_user.id, debtor, desc, amount, date)
        flash("Conta a receber adicionada!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/receivables/mark_manual_paid/<int:receivable_id>", methods=["POST"])
@login_required
def mark_manual_paid(receivable_id):
    try:
        db.update_receivable_status(receivable_id, current_user.id, 'paid')
        flash("Conta marcada como paga!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/receivables/delete_manual/<int:receivable_id>", methods=["POST"])
@login_required
def delete_manual(receivable_id):
    try:
        db.delete_receivable(receivable_id, current_user.id)
        flash("Registro apagado!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/receivables/add_recurring", methods=["POST"])
@login_required
def add_recurring():
    try:
        debtor = request.form.get('recurring_debtor_name')
        desc = request.form.get('recurring_description')
        amount = float(request.form.get('recurring_amount'))
        day = int(request.form.get('recurring_day'))
        db.add_recurring_receivable(current_user.id, debtor, desc, amount, day)
        flash("Regra recorrente criada!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/receivables/pay_recurring/<int:recurring_id>", methods=["POST"])
@login_required
def pay_recurring(recurring_id):
    try:
        rule = db.get_recurring_receivable_by_id(recurring_id, current_user.id)
        if rule:
            db.add_receivable(current_user.id, rule['debtor_name'], rule['description'], rule['amount'], datetime.now().strftime('%Y-%m-%d'), status='paid', recurring_id=recurring_id)
            flash("Pagamento registrado!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for('receivables.index'))

@receivables_bp.route("/receivables/delete_recurring/<int:recurring_id>", methods=["POST"])
@login_required
def delete_recurring(recurring_id):
    try:
        db.delete_recurring_receivable(recurring_id, current_user.id)
        flash("Regra removida!", "success")
    except Exception as e: flash(f"Erro: {e}", "danger")
    return redirect(url_for('receivables.index'))