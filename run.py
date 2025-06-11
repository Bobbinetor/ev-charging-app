
from app import create_app, db
from app.models import User, Station, ChargingPoint, ChargingSession

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'User': User, 
        'Station': Station, 
        'ChargingPoint': ChargingPoint, 
        'ChargingSession': ChargingSession
    }

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5050)