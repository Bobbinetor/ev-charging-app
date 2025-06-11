# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Application Overview

This is a Flask-based EV charging station management system with IoT integration through FIWARE/Orion-LD. The app supports dual user types (charging users and station managers) with a trust-based reputation system and real-time booking management.

## Common Development Commands

### Setup and Running
```bash
# Install dependencies
pip install -r requirements.txt

# Start infrastructure (PostgreSQL, MongoDB, Orion-LD)
docker-compose up -d

# Apply database migrations
flask db upgrade

# Run development server (http://127.0.0.1:5050)
python run.py

# Generate new migration after model changes
flask db migrate -m "description"
```

### Testing
```bash
# Run tests
pytest
```

## Architecture

**Pattern**: Flask application factory with Blueprint-based modules
- **Entry Point**: `run.py`
- **App Factory**: `app/__init__.py`
- **Configuration**: `config.py`

### Key Models and Relationships
- **User**: Authentication + trust scoring (users vs station managers)
- **Station**: Charging station management (1:N with ChargingPoint)
- **ChargingPoint**: Individual charging devices
- **Booking**: Reservation system with trust score impact
- **ChargingSession**: Active charging sessions
- **TrustRecord**: User reputation tracking

### Dual Data Architecture
- **PostgreSQL**: Persistent app data (users, bookings, stations)
- **Orion-LD**: Real-time IoT context data (charging status, availability)
- **Synchronization**: Service layer manages data consistency between systems

## Key Integration Points

### FIWARE/Orion-LD Context Broker
- URL: `http://localhost:1026`
- Service: `evcharging`
- Used for real-time charging point status and IoT data

### Authentication System
- Flask-Login with role-based access
- Separate registration flows: `/auth/register/user` and `/auth/register/station`
- Trust scoring affects booking privileges

### Booking System
Key endpoints in `app/auth/routes.py`:
- `POST /auth/user/book_charging` - Create booking
- `GET /auth/api/stations` - Available stations
- `POST /auth/booking/cancel/<id>` - Cancel booking
- `POST /auth/api/station/bookings/<id>/mark` - Mark booking outcome (affects trust)

## Development Patterns

### Service Layer
Booking logic abstracted in `app/services/booking_service.py` - use this pattern for complex business logic rather than putting everything in routes.

### Database Migrations
Well-structured migration history shows evolution:
- Basic user/station models → booking system → trust scoring
- Always test migrations both upgrade and downgrade

### Error Handling
Comprehensive error handling with database rollbacks - follow existing patterns in routes for transaction management.

### Form Validation
Custom validators in `app/auth/forms.py` - extend existing patterns rather than creating new validation approaches.

## Configuration

### Environment Variables
```python
SECRET_KEY = 'override-in-production'
DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/evcharging'
ORION_URL = 'http://localhost:1026'
FIWARE_SERVICE = 'evcharging'
```

### Docker Services
- PostgreSQL: port 5432
- MongoDB: port 27017 (FIWARE backend)
- Orion-LD: port 1026 (context broker)

## Important Files for New Feature Development

- `app/models.py` - All database models
- `app/auth/routes.py` - Main application logic
- `app/services/booking_service.py` - Business logic abstraction
- `app/auth/forms.py` - Form validation
- `config.py` - Application configuration
- `migrations/versions/` - Database schema evolution