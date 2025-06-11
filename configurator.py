#!/usr/bin/env python
"""
Configurator Script for EV Connect App

This script creates a station, its manager, and a regular user after database pruning.
It can be used to quickly set up a test environment with predetermined credentials.
All credentials are stored in a credentials.txt file for easy reference.
"""

import os
import sys
import requests
from datetime import datetime

# Add the current path to PYTHONPATH to import app modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import app modules
from app import create_app, db
from app.models import User, Station, ChargingPoint
from config import Config

# Create the application with the correct configuration
app = create_app(Config)

# Orion-LD configuration
ORION_ENDPOINT = "http://localhost:1026/v2/entities"
FIWARE_SERVICE = "ev_charging"
FIWARE_SERVICEPATH = "/"

# Headers for Orion-LD requests
ORION_HEADERS = {
    'Content-Type': 'application/json',
    'Fiware-Service': FIWARE_SERVICE,
    'Fiware-ServicePath': FIWARE_SERVICEPATH
}

# Predefined station data
STATION_DATA = {
    "name": "EV Connect Test Station",
    "company": "EV Connect",
    "vat_number": "12345678901",
    "address": "Via Test 123, Napoli",
    "latitude": 40.8417,
    "longitude": 14.2483,
    "email": "teststation@evconnect.it",
    "phone": "+390815551234"
}

# Predefined station manager data
STATION_MANAGER_DATA = {
    "username": "station_manager",
    "email": "stationmanager@evconnect.it",
    "password": "stationpwd123",
    "name": "Manager",
    "surname": "Test"
}

# Predefined regular user data
USER_DATA = {
    "username": "test_user",
    "email": "user@evconnect.it",
    "password": "userpwd123", 
    "name": "User",
    "surname": "Test"
}

# Charging points data
CHARGING_POINTS = [
    {"identifier": "DEV1", "power_type": "AC", "power_level": 22.0},
    {"identifier": "DEV2", "power_type": "DC", "power_level": 50.0},
    {"identifier": "DEV3", "power_type": "DC", "power_level": 150.0}
]

def create_station():
    """Create a test station and store it in the database"""
    with app.app_context():
        # Check if the station already exists
        existing_station = Station.query.filter_by(name=STATION_DATA["name"]).first()
        if existing_station:
            print(f"Station '{STATION_DATA['name']}' already exists with ID {existing_station.id}")
            return existing_station
        
        # Create the station
        station = Station(
            name=STATION_DATA["name"],
            company=STATION_DATA["company"],
            vat_number=STATION_DATA["vat_number"],
            address=STATION_DATA["address"],
            latitude=STATION_DATA["latitude"],
            longitude=STATION_DATA["longitude"],
            email=STATION_DATA["email"],
            phone=STATION_DATA["phone"]
        )
        
        # Add to database
        db.session.add(station)
        db.session.commit()
        
        print(f"Created station: {station.name} with ID {station.id}")
        
        # Create the station entity in Orion-LD
        create_station_entity_in_orion(station)
        
        return station

def create_station_manager(station):
    """Create a station manager and associate it with the station"""
    with app.app_context():
        # Check if the manager already exists
        existing_user = User.query.filter_by(email=STATION_MANAGER_DATA["email"]).first()
        if existing_user:
            print(f"Station manager '{STATION_MANAGER_DATA['email']}' already exists")
            
            # Ensure the existing user is associated with the station
            if existing_user.station_id != station.id:
                existing_user.station_id = station.id
                db.session.commit()
                print(f"Associated user with station ID {station.id}")
            
            return existing_user
        
        # Create a new station manager
        user = User(
            username=STATION_MANAGER_DATA["username"],
            email=STATION_MANAGER_DATA["email"],
            is_station_manager=True,
            name=STATION_MANAGER_DATA["name"],
            surname=STATION_MANAGER_DATA["surname"],
            station_id=station.id
        )
        
        user.set_password(STATION_MANAGER_DATA["password"])
        db.session.add(user)
        db.session.commit()
        
        print(f"Created station manager: {user.username} with ID {user.id}")
        
        return user

def create_regular_user():
    """Create a regular user for testing"""
    with app.app_context():
        # Check if the user already exists
        existing_user = User.query.filter_by(email=USER_DATA["email"]).first()
        if existing_user:
            print(f"Regular user '{USER_DATA['email']}' already exists")
            return existing_user
        
        # Create a new user
        user = User(
            username=USER_DATA["username"],
            email=USER_DATA["email"],
            is_station_manager=False,
            name=USER_DATA["name"],
            surname=USER_DATA["surname"]
        )
        
        user.set_password(USER_DATA["password"])
        db.session.add(user)
        db.session.commit()
        
        print(f"Created regular user: {user.username} with ID {user.id}")
        
        # Create the user entity in Orion-LD
        create_user_entity_in_orion(user)
        
        return user

def create_charging_points(station):
    """Create charging points for the station"""
    with app.app_context():
        created_points = []
        
        for point_data in CHARGING_POINTS:
            # Check if the charging point already exists
            existing_point = ChargingPoint.query.filter_by(identifier=point_data["identifier"]).first()
            if existing_point:
                print(f"Charging point '{point_data['identifier']}' already exists")
                created_points.append(existing_point)
                continue
            
            # Create new charging point
            point = ChargingPoint(
                identifier=point_data["identifier"],
                power_type=point_data["power_type"],
                power_level=point_data["power_level"],
                status="available",
                station_id=station.id
            )
            
            db.session.add(point)
            db.session.commit()
            
            print(f"Created charging point {point.identifier} with ID {point.id}")
            created_points.append(point)
            
            # Create the device entity in Orion-LD
            create_device_entity_in_orion(point, station)
        
        return created_points

def create_station_entity_in_orion(station):
    """Create a station entity in Orion-LD"""
    try:
        station_entity = {
            "id": f"urn:ngsi-ld:ChargingStation:{station.id}",
            "type": "ChargingStation",
            "name": {
                "type": "Text",
                "value": station.name
            },
            "address": {
                "type": "Text",
                "value": station.address
            },
            "location": {
                "type": "geo:json",
                "value": {
                    "type": "Point",
                    "coordinates": [station.longitude, station.latitude]
                }
            },
            "company": {
                "type": "Text",
                "value": station.company
            },
            "email": {
                "type": "Text",
                "value": station.email
            },
            "phone": {
                "type": "Text",
                "value": station.phone
            },
            "status": {
                "type": "Text",
                "value": "active"
            },
            "devices": {
                "type": "Array",
                "value": []
            }
        }
        
        response = requests.post(
            ORION_ENDPOINT,
            headers=ORION_HEADERS,
            json=station_entity
        )
        
        if response.status_code != 201:
            print(f"Error creating station entity in Orion-LD: {response.text}")
        else:
            print(f"Station entity {station.name} created in Orion-LD")
    
    except Exception as e:
        print(f"Exception creating station entity in Orion-LD: {str(e)}")

def create_device_entity_in_orion(device, station):
    """Create a device entity in Orion-LD"""
    try:
        station_entity_id = f"urn:ngsi-ld:ChargingStation:{station.id}"
        
        # Create device in Orion-LD
        device_entity = {
            "id": f"urn:ngsi-ld:ChargingDevice:{device.id}",
            "type": "ChargingDevice",
            "refStation": {
                "type": "Relationship",
                "value": station_entity_id
            },
            "deviceId": {
                "type": "Text",
                "value": device.identifier
            },
            "deviceType": {
                "type": "Text",
                "value": device.power_type
            },
            "powerLevel": {
                "type": "Float",
                "value": float(device.power_level)
            },
            "status": {
                "type": "Text",
                "value": "available"
            }
        }
        
        # Register the device as a separate entity
        device_response = requests.post(
            ORION_ENDPOINT,
            headers=ORION_HEADERS,
            json=device_entity
        )
        
        if device_response.status_code != 201:
            print(f"Error creating device in Orion-LD: {device_response.text}")
            return
        
        # Update the device array in the station
        station_update = {
            "devices": {
                "type": "Array",
                "value": [f"urn:ngsi-ld:ChargingDevice:{device.id}"]
            }
        }
        
        # Update the station entity with append
        update_url = f"{ORION_ENDPOINT}/urn:ngsi-ld:ChargingStation:{station.id}/attrs"
        update_headers = ORION_HEADERS.copy()
        
        update_response = requests.patch(
            update_url,
            headers=update_headers,
            json=station_update
        )
        
        if update_response.status_code != 204:
            print(f"Error updating station in Orion-LD: {update_response.text}")
        else:
            print(f"Device {device.identifier} added to station entity in Orion-LD")
    
    except Exception as e:
        print(f"Exception creating device entity in Orion-LD: {str(e)}")

def create_user_entity_in_orion(user):
    """Create a user entity in Orion-LD"""
    try:
        user_entity = {
            "id": f"urn:ngsi-ld:User:{user.id}",
            "type": "User",
            "name": {
                "type": "Text",
                "value": f"{user.name} {user.surname}"
            },
            "email": {
                "type": "Text",
                "value": user.email
            },
            "trust_score": {
                "type": "Number",
                "value": user.trust_score
            }
        }
        
        response = requests.post(
            ORION_ENDPOINT,
            headers=ORION_HEADERS,
            json=user_entity
        )
        
        if response.status_code != 201:
            print(f"Error creating user entity in Orion-LD: {response.text}")
        else:
            print(f"User entity {user.email} created in Orion-LD")
    
    except Exception as e:
        print(f"Exception creating user entity in Orion-LD: {str(e)}")

def save_credentials_to_file():
    """Save all credentials to a text file"""
    with open('ev_connect_credentials.txt', 'w') as file:
        file.write("EV Connect Test Credentials\n")
        file.write("=========================\n\n")
        
        file.write("Station Information:\n")
        file.write("-----------------\n")
        for key, value in STATION_DATA.items():
            file.write(f"{key.capitalize()}: {value}\n")
        file.write("\n")
        
        file.write("Station Manager Account:\n")
        file.write("----------------------\n")
        file.write(f"Email: {STATION_MANAGER_DATA['email']}\n")
        file.write(f"Password: {STATION_MANAGER_DATA['password']}\n")
        file.write(f"Name: {STATION_MANAGER_DATA['name']} {STATION_MANAGER_DATA['surname']}\n")
        file.write("\n")
        
        file.write("Regular User Account:\n")
        file.write("------------------\n")
        file.write(f"Email: {USER_DATA['email']}\n")
        file.write(f"Password: {USER_DATA['password']}\n")
        file.write(f"Name: {USER_DATA['name']} {USER_DATA['surname']}\n")
        
    print(f"Credentials saved to {os.path.abspath('ev_connect_credentials.txt')}")

def main():
    """Run the configurator script"""
    print("Starting EV Connect configurator...")
    print("===================================\n")
    
    # Create station
    station = create_station()
    
    # Create station manager
    create_station_manager(station)
    
    # Create regular user
    create_regular_user()
    
    # Create charging points for the station
    create_charging_points(station)
    
    # Save credentials to file
    save_credentials_to_file()
    
    print("\nSetup completed successfully!")
    print(f"Credentials file saved at: {os.path.abspath('ev_connect_credentials.txt')}")

if __name__ == "__main__":
    main()