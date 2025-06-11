#!/usr/bin/env python
"""
Script per popolare il database con stazioni di ricarica di test nella zona di Napoli.
Registra 15 stazioni con dati realistici e crea gli account manager associati.
Registra anche le entità in Orion-LD.
"""

import os
import sys
import random
import requests
from datetime import datetime

# Aggiungi il percorso corrente al PYTHONPATH per importare i moduli dell'app
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Importa i moduli dell'app
from app import create_app, db
from app.models import User, Station, ChargingPoint
from config import Config

# Crea l'applicazione con la configurazione corretta
app = create_app(Config)

# Configurazione dell'endpoint Orion-LD
ORION_ENDPOINT = "http://localhost:1026/v2/entities"
FIWARE_SERVICE = "ev_charging"
FIWARE_SERVICEPATH = "/"

# Headers per le richieste a Orion-LD
ORION_HEADERS = {
    'Content-Type': 'application/json',
    'Fiware-Service': FIWARE_SERVICE,
    'Fiware-ServicePath': FIWARE_SERVICEPATH
}

# Dati di esempio per le stazioni di Napoli
naples_stations = [
    # Nome, indirizzo, latitudine, longitudine
    ("EV Napoli Centro", "Via Toledo 45, Napoli", 40.8417, 14.2483),
    ("Green Power Vomero", "Via Scarlatti 30, Napoli", 40.8544, 14.2310),
    ("Charge Hub Chiaia", "Via Chiaia 150, Napoli", 40.8380, 14.2434),
    ("EcoCharge Posillipo", "Via Posillipo 35, Napoli", 40.8285, 14.2169),
    ("Napoli Carichi", "Piazza Garibaldi 15, Napoli", 40.8518, 14.2721),
    ("Fast Charge Mergellina", "Via Mergellina 23, Napoli", 40.8296, 14.2169),
    ("PowerStation Fuorigrotta", "Piazzale Tecchio 10, Napoli", 40.8270, 14.1922),
    ("EnergyPoint Bagnoli", "Via Diocleziano 185, Napoli", 40.8180, 14.1710),
    ("Green Energy San Lorenzo", "Corso Umberto I 90, Napoli", 40.8470, 14.2610),
    ("Eco Station Ponticelli", "Via Argine 325, Napoli", 40.8497, 14.3090),
    ("Charging Bay Nisida", "Via Nisida 12, Napoli", 40.7968, 14.1627),
    ("VoltyNaples Arenella", "Via Domenico Fontana 65, Napoli", 40.8520, 14.2350),
    ("Fast Hub Spaccanapoli", "Via Benedetto Croce 42, Napoli", 40.8465, 14.2551),
    ("Charge Avenue Lungomare", "Via Partenope 20, Napoli", 40.8300, 14.2480),
    ("PowerZone San Giovanni", "Corso San Giovanni a Teduccio 180, Napoli", 40.8340, 14.3050)
]

# Nomi delle aziende
companies = [
    "Enel X", "EnergieNapoli", "Repower", "GreenCharging", "EcoMobility", 
    "Neapolis Energy", "PowerMotive", "Vesuvio Energia", "SouthEV", "ChargeItalia"
]

# Dati per i device
device_types = ["AC", "DC"]
power_levels_ac = [7.4, 11, 22]
power_levels_dc = [50, 100, 150, 175]

def create_station_with_manager(station_data, index):
    """Crea una stazione e il relativo account manager"""
    name, address, lat, lng = station_data
    
    # Genera un ID fiscale (partita IVA) di esattamente 11 caratteri
    vat_number = f"{index:02d}01234567"[:11]
    
    # Seleziona un'azienda casuale
    company = random.choice(companies)
    
    # Crea un'email generica per la stazione con timestamp per evitare duplicati
    timestamp = int(datetime.now().timestamp())
    email = f"station{index}_{timestamp}@evconnect.test"
    
    # Numero di telefono generico
    phone = f"+39081555{1000 + index}"
    
    with app.app_context():
        # Verifica se la stazione esiste già con la stessa partita IVA
        existing_station = Station.query.filter_by(vat_number=vat_number).first()
        if existing_station:
            print(f"Stazione con partita IVA {vat_number} già esistente. Saltata.")
            return None
        
        # Verifica se esiste già un utente con quell'email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"Utente con email {email} già esistente. Utilizzo un altro indirizzo.")
            # Genera un timestamp ancora più diverso
            timestamp = int(datetime.now().timestamp() * 1000)
            email = f"station{index}_{timestamp}@evconnect.test"
        
        # Crea la stazione nel database
        station = Station(
            name=name,
            company=company,
            vat_number=vat_number,
            address=address,
            latitude=lat,
            longitude=lng,
            email=email,
            phone=phone
        )
        
        # Crea l'account manager
        username = f"station{index}_{timestamp}_admin"
        user = User(
            username=username,
            email=email,
            is_station_manager=True,
            name=f"Manager {index}",
            surname="Test"
        )
        
        # Imposta la password (uguale per tutti per i test)
        user.set_password("stationtest123")
        
        # Aggiungi al database
        db.session.add(station)
        db.session.add(user)
        db.session.commit()
        
        # Associa l'utente alla stazione
        user.station_id = station.id
        db.session.commit()
        
        print(f"Creata stazione: {name} con manager {username}")
        print(f"  - Email: {email}")
        print(f"  - Password: stationtest123")
        
        # Crea l'entità stazione in Orion-LD
        create_station_entity_in_orion(station)
        
        # Aggiungi dispositivi di ricarica casuali
        add_random_devices(station)
        
        return station

def create_station_entity_in_orion(station):
    """Crea un'entità stazione in Orion-LD"""
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
            print(f"Errore creazione entità stazione in Orion-LD: {response.text}")
        else:
            print(f"Entità stazione {station.name} creata in Orion-LD")
    
    except Exception as e:
        print(f"Eccezione nella creazione dell'entità stazione: {str(e)}")

def add_random_devices(station):
    """Aggiunge dispositivi di ricarica casuali alla stazione"""
    # Numero casuale di dispositivi (2-5)
    num_devices = random.randint(2, 5)
    
    with app.app_context():
        for i in range(num_devices):
            # Scegli casualmente il tipo di dispositivo
            power_type = random.choice(device_types)
            
            # In base al tipo, scegli un livello di potenza appropriato
            if power_type == "AC":
                power_level = random.choice(power_levels_ac)
            else:  # DC
                power_level = random.choice(power_levels_dc)
            
            # ID del dispositivo
            device_id = f"DEV{station.id}_{i+1}"
            
            # Crea il dispositivo nel database
            device = ChargingPoint(
                identifier=device_id,
                power_type=power_type,
                power_level=power_level,
                status="available",
                station_id=station.id
            )
            
            db.session.add(device)
            db.session.commit()
            
            print(f"Aggiunto dispositivo {device_id} alla stazione {station.name}")
            
            # Crea l'entità device in Orion-LD
            create_device_entity_in_orion(device, station)

def create_device_entity_in_orion(device, station):
    """Crea un'entità dispositivo in Orion-LD"""
    try:
        station_entity_id = f"urn:ngsi-ld:ChargingStation:{station.id}"
        
        # Crea il device in Orion-LD
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
        
        # Registra il device come entità separata
        device_response = requests.post(
            ORION_ENDPOINT,
            headers=ORION_HEADERS,
            json=device_entity
        )
        
        if device_response.status_code != 201:
            print(f"Errore creazione device in Orion-LD: {device_response.text}")
            return
        
        # Aggiorna l'array dei dispositivi nella stazione
        station_update = {
            "devices": {
                "type": "Array",
                "value": [f"urn:ngsi-ld:ChargingDevice:{device.id}"]
            }
        }
        
        # Aggiorna l'entità stazione con append
        update_url = f"{ORION_ENDPOINT}/urn:ngsi-ld:ChargingStation:{station.id}/attrs"
        update_headers = ORION_HEADERS.copy()
        
        update_response = requests.patch(
            update_url,
            headers=update_headers,
            json=station_update
        )
        
        if update_response.status_code != 204:
            print(f"Errore aggiornamento stazione in Orion-LD: {update_response.text}")
        else:
            print(f"Device {device.identifier} aggiunto all'entità stazione in Orion-LD")
    
    except Exception as e:
        print(f"Eccezione nella creazione dell'entità device: {str(e)}")

def main():
    """Funzione principale per popolare il database"""
    print("Inizio creazione stazioni di test nella zona di Napoli...")
    
    for i, station_data in enumerate(naples_stations):
        create_station_with_manager(station_data, i+1)
    
    print("\nOperazione completata.")
    print("\nCredenziali per accedere alle stazioni:")
    print("Email: stationX@evconnect.test (dove X va da 1 a 15)")
    print("Password: stationtest123")

if __name__ == "__main__":
    main()