# forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from database import get_user_by_email

class RegistrationForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email(message='Email inválido.')])
    password = PasswordField('Senha', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar Senha',
                                     validators=[DataRequired(), EqualTo('password', message='As senhas não conferem.')])
    submit = SubmitField('Registrar')

    def validate_email(self, email):
        user = get_user_by_email(email.data)
        if user:
            raise ValidationError('Este email já está em uso. Por favor, escolha outro.')

class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email(message='Email inválido.')])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember = BooleanField('Lembrar-me')
    submit = SubmitField('Login')

class RequestResetForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email(message='Email inválido.')])
    submit = SubmitField('Solicitar Redefinição de Senha')

    def validate_email(self, email):
        user = get_user_by_email(email.data)
        if user is None:
            raise ValidationError('Não existe conta com este email. Você deve se registrar primeiro.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nova Senha', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar Nova Senha',
                                     validators=[DataRequired(), EqualTo('password', message='As senhas não conferem.')])
    submit = SubmitField('Redefinir Senha')