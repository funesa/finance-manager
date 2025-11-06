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
    password = PasswordField('Senha', validators=[DataRequired()])
    confirm_password = PasswordField('Confirme a Senha',
                                   validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrar')

class RequestResetForm(FlaskForm):
    email = StringField('Email',
                       validators=[DataRequired(), Email()])
    submit = SubmitField('Solicitar Redefinição de Senha')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nova Senha', validators=[DataRequired()])
    confirm_password = PasswordField('Confirme a Nova Senha',
                                   validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Redefinir Senha')