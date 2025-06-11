from flask import Blueprint

# Blueprint registered in create_app under prefix '/auth'
bp = Blueprint('auth', __name__)

from app.auth import routes