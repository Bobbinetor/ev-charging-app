from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, FloatField, SelectField, SelectMultipleField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Regexp, Optional
from wtforms.widgets import CheckboxInput, ListWidget
from email_validator import validate_email, EmailNotValidError
from app.models import User, Station

def custom_email_validator():
    def _validate(form, field):
        try:
            validate_email(
                field.data,
                test_environment=True  # This allows .test domains
            )
        except EmailNotValidError as e:
            raise ValidationError(str(e))
    return _validate

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), custom_email_validator()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Ricordami')
    submit = SubmitField('Accedi')

class RegistrationUserForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired(), Length(min=2, max=64)])
    surname = StringField('Cognome', validators=[DataRequired(), Length(min=2, max=64)])
    email = StringField('Email', validators=[DataRequired(), custom_email_validator()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='La password deve contenere almeno 8 caratteri')
    ])
    password2 = PasswordField('Conferma Password', validators=[
        DataRequired(),
        EqualTo('password', message='Le password devono coincidere')
    ])
    accept_terms = BooleanField('Accetto i Termini e Condizioni', validators=[
        DataRequired(message='Devi accettare i termini e condizioni per continuare')
    ])
    submit = SubmitField('Registrati')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Email già registrata. Utilizza un\'altra email o accedi.')

class RegistrationStationForm(FlaskForm):
    station_name = StringField('Nome Stazione', validators=[DataRequired(), Length(min=2, max=100)])
    company = StringField('Azienda', validators=[DataRequired(), Length(min=2, max=100)])
    vat_number = StringField('Partita IVA', validators=[
        DataRequired(),
        Regexp('^[0-9]{11}$', message='Inserisci una partita IVA valida (11 cifre)')
    ])
    address = StringField('Indirizzo', validators=[DataRequired(), Length(min=5, max=200)])
    latitude = FloatField('Latitudine', validators=[DataRequired()])
    longitude = FloatField('Longitudine', validators=[DataRequired()])
    
    # Nuovi campi per mobilità sostenibile
    station_type = SelectField('Tipo Stazione', choices=[
        ('electric', 'Solo Elettrica'),
        ('hydrogen', 'Solo Idrogeno'),
        ('hybrid', 'Ibrida (Elettrica + Idrogeno)')
    ], validators=[DataRequired()])
    
    fuel_types = SelectMultipleField('Tipi di Carburante', choices=[
        ('electric', 'Elettrico'),
        ('hydrogen', 'Idrogeno')
    ], validators=[DataRequired(message='Seleziona almeno un tipo di carburante')], 
    widget=ListWidget(prefix_label=False), option_widget=CheckboxInput())
    
    # Campi specifici per elettrico (opzionali)
    electric_power = FloatField('Potenza Massima (kW)', validators=[Optional()], description='Solo per stazioni elettriche')
    connector_types = SelectMultipleField('Tipi di Connettori', choices=[
        ('type2', 'Type 2'),
        ('ccs', 'CCS'),
        ('chademo', 'CHAdeMO')
    ], validators=[Optional()], 
    widget=ListWidget(prefix_label=False), option_widget=CheckboxInput())
    
    # Campi specifici per idrogeno (opzionali)
    hydrogen_storage_capacity = FloatField('Capacità Stoccaggio H2 (kg)', validators=[Optional()], description='Solo per stazioni idrogeno')
    hydrogen_purity = FloatField('Purezza Idrogeno (%)', validators=[Optional()], description='Valore tra 99.9 e 99.99')
    max_dispensing_pressure = SelectField('Pressione Massima (bar)', choices=[
        ('', 'Non applicabile'),
        ('350', '350 bar'),
        ('700', '700 bar'),
        ('700', '350 e 700 bar')
    ], validators=[Optional()])
    
    email = StringField('Email', validators=[DataRequired(), custom_email_validator()])
    phone = StringField('Telefono', validators=[
        DataRequired(),
        Regexp('^[+]?[0-9]{10,15}$', message='Inserisci un numero di telefono valido')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='La password deve contenere almeno 8 caratteri')
    ])
    password2 = PasswordField('Conferma Password', validators=[
        DataRequired(),
        EqualTo('password', message='Le password devono coincidere')
    ])
    accept_terms = BooleanField('Accetto i Termini e Condizioni', validators=[
        DataRequired(message='Devi accettare i termini e condizioni per continuare')
    ])
    submit = SubmitField('Registra Stazione')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Email già registrata. Utilizza un\'altra email o accedi.')
    
    def validate_vat_number(self, vat_number):
        station = Station.query.filter_by(vat_number=vat_number.data).first()
        if station is not None:
            raise ValidationError('Partita IVA già registrata nel sistema.')

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), custom_email_validator()])
    submit = SubmitField('Richiedi reset password')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='La password deve contenere almeno 8 caratteri')
    ])
    password2 = PasswordField('Conferma Password', validators=[
        DataRequired(),
        EqualTo('password', message='Le password devono coincidere')
    ])
    submit = SubmitField('Reimposta Password')