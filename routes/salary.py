from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
import database as db

salary_bp = Blueprint('salary', __name__)

@salary_bp.route("/salary", methods=["GET", "POST"])
@login_required
def index():
    updated = False
    if request.method == "POST":
        try:
            salary = float(request.form.get("salary", 0))
            bonus = float(request.form.get("bonus", 0))
            db.set_salary_info(current_user.id, salary, bonus)
            updated = True
            flash("Dados de salário e benefícios atualizados!", "success")
        except Exception as e:
            flash(f"Erro ao salvar salário/benefícios: {e}", "danger")
            
    info = db.get_salary_info(current_user.id)
    return render_template(
        "salary.html",
        salary=info["salary"],
        bonus=info["bonus"],
        updated=updated,
        active_page="salary",
        datetime=datetime
    )