from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from config import Config

# Inizializzazione delle estensioni
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Effettua il login per accedere a questa pagina.'
csrf = CSRFProtect()
mail = Mail()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Inizializzazione delle estensioni con l'app
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    
    # Return JSON 401 for unauthorized AJAX requests instead of redirect
    @login.unauthorized_handler
    def unauthorized_callback():
        return jsonify({'error': 'Login richiesto'}), 401
    
    csrf.init_app(app)
    mail.init_app(app)
    
    # Registrazione dei blueprint
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    # Gestione degli errori
    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)
    
    @app.before_first_request
    def create_tables():
        db.create_all()
    
    return app