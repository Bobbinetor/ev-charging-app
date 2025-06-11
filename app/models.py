from datetime import datetime
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import enum

class FuelType(enum.Enum):
    ELECTRIC = "electric"
    HYDROGEN = "hydrogen"
    HYBRID = "hybrid"

class ConnectorType(enum.Enum):
    # Elettrico
    TYPE2 = "type2"
    CCS = "ccs"
    CHADEMO = "chademo"
    # Idrogeno
    H70 = "h70"  # 700 bar
    H35 = "h35"  # 350 bar

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(64))
    surname = db.Column(db.String(64))
    is_station_manager = db.Column(db.Boolean, default=False)
    trust_score = db.Column(db.Integer, default=0)
    charging_sessions = db.relationship('ChargingSession', backref='user', lazy='dynamic')
    station_id = db.Column(db.Integer, db.ForeignKey('station.id'))
    station = db.relationship('Station', backref='manager', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Station(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    company = db.Column(db.String(100))
    vat_number = db.Column(db.String(11), unique=True)
    address = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    # Nuovi campi per supportare multi-carburante
    fuel_types = db.Column(db.JSON)  # ["electric", "hydrogen"]
    station_type = db.Column(db.String(32), default='electric')  # electric, hydrogen, hybrid
    # Campi specifici per elettrico
    electric_power = db.Column(db.Float)  # kW potenza massima
    connector_types = db.Column(db.JSON)  # ["type2", "ccs", "chademo"]
    # Campi specifici per idrogeno
    hydrogen_storage_capacity = db.Column(db.Float)  # kg
    hydrogen_purity = db.Column(db.Float)  # %
    max_dispensing_pressure = db.Column(db.Integer)  # bar
    charging_points = db.relationship('ChargingPoint', backref='station', lazy='dynamic')

    def __repr__(self):
        return f'<Station {self.name}>'

class ChargingPoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(64), unique=True)
    
    # Campi generici per tutti i tipi
    fuel_type = db.Column(db.Enum(FuelType), nullable=False)
    connector_type = db.Column(db.Enum(ConnectorType))
    status = db.Column(db.String(32))  # available, occupied, maintenance
    station_id = db.Column(db.Integer, db.ForeignKey('station.id'))
    
    # Campi specifici per elettrico
    power_type = db.Column(db.String(32))  # AC/DC
    power_level = db.Column(db.Float)  # kW
    voltage = db.Column(db.Float)  # V
    current = db.Column(db.Float)  # A
    
    # Campi specifici per idrogeno
    dispensing_pressure = db.Column(db.Integer)  # bar (350 o 700)
    flow_rate = db.Column(db.Float)  # kg/min
    temperature_range_min = db.Column(db.Float)  # °C
    temperature_range_max = db.Column(db.Float)  # °C
    purity_level = db.Column(db.Float)  # %
    
    # Campi per digital twin - sensori in tempo reale
    current_temperature = db.Column(db.Float)
    current_pressure = db.Column(db.Float)
    current_flow = db.Column(db.Float)
    last_telemetry_update = db.Column(db.DateTime)
    
    charging_sessions = db.relationship('ChargingSession', backref='charging_point', lazy='dynamic')

    def __repr__(self):
        return f'<ChargingPoint {self.identifier}>'

class ChargingSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    
    # Campi generici
    fuel_type = db.Column(db.Enum(FuelType))
    
    # Campi specifici per elettrico
    energy_consumed = db.Column(db.Float)  # kWh
    peak_power = db.Column(db.Float)  # kW
    average_power = db.Column(db.Float)  # kW
    
    # Campi specifici per idrogeno
    hydrogen_dispensed = db.Column(db.Float)  # kg
    dispensing_pressure = db.Column(db.Integer)  # bar
    dispensing_temperature = db.Column(db.Float)  # °C
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    charging_point_id = db.Column(db.Integer, db.ForeignKey('charging_point.id'))

    def __repr__(self):
        return f'<ChargingSession {self.id}>'

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_time = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_start = db.Column(db.DateTime, nullable=False)
    scheduled_end = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(32), default='reserved')  # reserved, completed, cancelled
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('station.id'), nullable=False)
    charging_point_id = db.Column(db.Integer, db.ForeignKey('charging_point.id'), nullable=False)
    
    # Relazioni
    user = db.relationship('User', backref=db.backref('bookings', lazy='dynamic'))
    station = db.relationship('Station', backref=db.backref('bookings', lazy='dynamic'))
    charging_point = db.relationship('ChargingPoint', backref=db.backref('bookings', lazy='dynamic'))
    
    def __repr__(self):
        return f'<Booking {self.id}: {self.scheduled_start} - {self.scheduled_end}>'

class TrustRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, nullable=False)  # Changed from db.ForeignKey('booking.id')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('station.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    score_change = db.Column(db.Integer)  # +1 or -1
    user_trust_score_after_change = db.Column(db.Integer) # Stores the user's total trust score after this event

    # Changed relationship definition due to removed foreign key
    # booking = db.relationship('Booking', backref=db.backref('trust_records', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('trust_records', lazy='dynamic'))
    station = db.relationship('Station', backref=db.backref('trust_records', lazy='dynamic'))

@login.user_loader
def load_user(id):
    return User.query.get(int(id))