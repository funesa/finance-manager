"""
Web interface forms using Flask-WTF.
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, BooleanField,
    SelectField, DecimalField, DateField
)
from wtforms.validators import (
    DataRequired, Length, Email, EqualTo, ValidationError,
    NumberRange
)
from datetime import datetime

class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember = BooleanField('Lembrar Login')
    submit = SubmitField('Entrar')

class RegistrationForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6, message='A senha deve ter pelo menos 6 caracteres.')])
    confirm_password = PasswordField('Confirme a Senha',
                                     validators=[DataRequired(), EqualTo('password', message='As senhas não coincidem.')])
    submit = SubmitField('Registrar')

class RequestResetForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    submit = SubmitField('Solicitar Redefinição de Senha')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nova Senha', validators=[DataRequired(), Length(min=6, message='A senha deve ter pelo menos 6 caracteres.')])
    confirm_password = PasswordField('Confirme a Nova Senha',
                                     validators=[DataRequired(), EqualTo('password', message='As senhas não coincidem.')])
    submit = SubmitField('Redefinir Senha')

# --- NOVO FORMULÁRIO ADICIONADO NO FINAL ---
class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Senha Atual', 
                                     validators=[DataRequired()])
    password = PasswordField('Nova Senha', 
                             validators=[DataRequired(), Length(min=6, message='A senha deve ter pelo menos 6 caracteres.')])
    confirm_password = PasswordField('Confirmar Nova Senha', 
                                     validators=[DataRequired(), EqualTo('password', message='As senhas não coincidem.')])
    submit = SubmitField('Mudar Senha')