from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from app.main import bp

@bp.route('/')
@bp.route('/index')
def index():
    return render_template('index.html', title='Home')

@bp.route('/terms')
def terms():
    return render_template('main/terms.html', title='Termini e Condizioni')

@bp.route('/privacy')
def privacy():
    return render_template('main/privacy.html', title='Privacy Policy')

@bp.route('/user/profile')
@login_required
def user_profile():
    if current_user.is_station_manager:
        return redirect(url_for('auth.station_dashboard'))
    return render_template('user/profile.html', title='Profilo Utente')

@bp.route('/station/dashboard')
@login_required
def station_dashboard():
    if not current_user.is_station_manager:
        return redirect(url_for('main.user_dashboard'))
    return render_template('station/dashboard.html', title='Dashboard Stazione')