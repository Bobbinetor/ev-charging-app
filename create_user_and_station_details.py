#!/usr/bin/env python3
"""
Script per creare utenti e stazioni di test con dati realistici
per la piattaforma di mobilità sostenibile.
"""

import sys
import os
import requests
import json
import random
from datetime import datetime, timezone

# Aggiungi il path dell'app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Station, ChargingPoint, FuelType, ConnectorType
from app.services.digital_twin_service import create_device_digital_twin, create_station_digital_twin

# Dati realistici per le stazioni
STATION_DATA = [
    # Stazioni elettriche
    {
        "name": "Milano Porta Garibaldi EV Hub",
        "company": "Enel X Way",
        "vat_number": "97329390151",
        "address": "Piazza Sigmund Freud, 1, Milano",
        "latitude": 45.4859,
        "longitude": 9.1877,
        "email": "milano.garibaldi@enelx.com",
        "phone": "+39 02 83051234",
        "fuel_types": ["electric"],
        "station_type": "electric",
        "devices": [
            {"identifier": "MIL_GAR_AC_01", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.TYPE2, "power_type": "AC", "power_level": 22.0, "voltage": 400.0, "current": 32.0},
            {"identifier": "MIL_GAR_AC_02", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.TYPE2, "power_type": "AC", "power_level": 7.4, "voltage": 230.0, "current": 32.0},
            {"identifier": "MIL_GAR_DC_01", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.CCS, "power_type": "DC", "power_level": 150.0, "voltage": 800.0, "current": 187.5},
            {"identifier": "MIL_GAR_DC_02", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.CCS, "power_type": "DC", "power_level": 300.0, "voltage": 800.0, "current": 375.0},
        ]
    },
    {
        "name": "Roma Termini Fast Charge",
        "company": "BE Charge S.r.l.",
        "vat_number": "15087451006",
        "address": "Via Giovanni Giolitti, 34, Roma",
        "latitude": 41.9011,
        "longitude": 12.5020,
        "email": "roma.termini@becharge.com",
        "phone": "+39 06 44291234",
        "fuel_types": ["electric"],
        "station_type": "electric",
        "devices": [
            {"identifier": "ROM_TER_CCS_01", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.CCS, "power_type": "DC", "power_level": 50.0, "voltage": 400.0, "current": 125.0},
            {"identifier": "ROM_TER_CCS_02", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.CCS, "power_type": "DC", "power_level": 100.0, "voltage": 500.0, "current": 200.0},
            {"identifier": "ROM_TER_CHD_01", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.CHADEMO, "power_type": "DC", "power_level": 50.0, "voltage": 400.0, "current": 125.0},
            {"identifier": "ROM_TER_T2_01", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.TYPE2, "power_type": "AC", "power_level": 22.0, "voltage": 400.0, "current": 32.0},
            {"identifier": "ROM_TER_T2_02", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.TYPE2, "power_type": "AC", "power_level": 22.0, "voltage": 400.0, "current": 32.0},
        ]
    },
    
    # Stazioni idrogeno
    {
        "name": "Torino H2 Station",
        "company": "Snam4Mobility S.r.l.",
        "vat_number": "13271390158",
        "address": "Corso Giulio Cesare, 20, Torino",
        "latitude": 45.0845,
        "longitude": 7.6759,
        "email": "torino.h2@snam4mobility.it",
        "phone": "+39 011 6677890",
        "fuel_types": ["hydrogen"],
        "station_type": "hydrogen",
        "hydrogen_storage_capacity": 800.0,
        "hydrogen_purity": 99.97,
        "max_dispensing_pressure": 700,
        "devices": [
            {"identifier": "TOR_H2_H70_01", "fuel_type": FuelType.HYDROGEN, "connector_type": ConnectorType.H70, "dispensing_pressure": 700, "flow_rate": 2.0, "temperature_range_min": -40.0, "temperature_range_max": 85.0, "purity_level": 99.97},
            {"identifier": "TOR_H2_H35_01", "fuel_type": FuelType.HYDROGEN, "connector_type": ConnectorType.H35, "dispensing_pressure": 350, "flow_rate": 1.8, "temperature_range_min": -40.0, "temperature_range_max": 85.0, "purity_level": 99.95},
        ]
    },
    {
        "name": "Venezia Mestre H2 Refuel",
        "company": "Air Liquide Italia S.r.l.",
        "vat_number": "00486810134",
        "address": "Via Ca' Marcello, 67, Venezia Mestre",
        "latitude": 45.4963,
        "longitude": 12.2336,
        "email": "venezia.h2@airliquide.com",
        "phone": "+39 041 5380123",
        "fuel_types": ["hydrogen"],
        "station_type": "hydrogen",
        "hydrogen_storage_capacity": 1200.0,
        "hydrogen_purity": 99.99,
        "max_dispensing_pressure": 700,
        "devices": [
            {"identifier": "VEN_H2_H70_01", "fuel_type": FuelType.HYDROGEN, "connector_type": ConnectorType.H70, "dispensing_pressure": 700, "flow_rate": 2.5, "temperature_range_min": -40.0, "temperature_range_max": 85.0, "purity_level": 99.99},
            {"identifier": "VEN_H2_H70_02", "fuel_type": FuelType.HYDROGEN, "connector_type": ConnectorType.H70, "dispensing_pressure": 700, "flow_rate": 2.2, "temperature_range_min": -40.0, "temperature_range_max": 85.0, "purity_level": 99.99},
            {"identifier": "VEN_H2_H35_01", "fuel_type": FuelType.HYDROGEN, "connector_type": ConnectorType.H35, "dispensing_pressure": 350, "flow_rate": 1.5, "temperature_range_min": -40.0, "temperature_range_max": 85.0, "purity_level": 99.95},
        ]
    },
    
    # Stazioni ibride
    {
        "name": "Firenze Multimodal Energy Hub",
        "company": "NextChem Tech S.p.A.",
        "vat_number": "02398800589",
        "address": "Viale Spartaco Lavagnini, 58, Firenze",
        "latitude": 43.7847,
        "longitude": 11.2462,
        "email": "firenze.hub@nextchem.com",
        "phone": "+39 055 4781234",
        "fuel_types": ["electric", "hydrogen"],
        "station_type": "hybrid",
        "hydrogen_storage_capacity": 600.0,
        "hydrogen_purity": 99.97,
        "max_dispensing_pressure": 700,
        "devices": [
            # Dispositivi elettrici
            {"identifier": "FIR_EV_HPC_01", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.CCS, "power_type": "DC", "power_level": 350.0, "voltage": 800.0, "current": 437.5},
            {"identifier": "FIR_EV_AC_01", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.TYPE2, "power_type": "AC", "power_level": 22.0, "voltage": 400.0, "current": 32.0},
            {"identifier": "FIR_EV_AC_02", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.TYPE2, "power_type": "AC", "power_level": 22.0, "voltage": 400.0, "current": 32.0},
            # Dispositivi idrogeno
            {"identifier": "FIR_H2_H70_01", "fuel_type": FuelType.HYDROGEN, "connector_type": ConnectorType.H70, "dispensing_pressure": 700, "flow_rate": 2.0, "temperature_range_min": -40.0, "temperature_range_max": 85.0, "purity_level": 99.97},
            {"identifier": "FIR_H2_H35_01", "fuel_type": FuelType.HYDROGEN, "connector_type": ConnectorType.H35, "dispensing_pressure": 350, "flow_rate": 1.5, "temperature_range_min": -40.0, "temperature_range_max": 85.0, "purity_level": 99.95},
        ]
    },
    {
        "name": "Napoli Sustainable Mobility Center",
        "company": "ENI New Energy S.p.A.",
        "vat_number": "90002270073",
        "address": "Via Marina, 230, Napoli",
        "latitude": 40.8358,
        "longitude": 14.2488,
        "email": "napoli.center@eni.com",
        "phone": "+39 081 5551234",
        "fuel_types": ["electric", "hydrogen"],
        "station_type": "hybrid",
        "hydrogen_storage_capacity": 1000.0,
        "hydrogen_purity": 99.98,
        "max_dispensing_pressure": 700,
        "devices": [
            # Dispositivi elettrici
            {"identifier": "NAP_EV_UPC_01", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.CCS, "power_type": "DC", "power_level": 300.0, "voltage": 800.0, "current": 375.0},
            {"identifier": "NAP_EV_CCS_01", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.CCS, "power_type": "DC", "power_level": 150.0, "voltage": 500.0, "current": 300.0},
            {"identifier": "NAP_EV_CHD_01", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.CHADEMO, "power_type": "DC", "power_level": 100.0, "voltage": 400.0, "current": 250.0},
            {"identifier": "NAP_EV_T2_01", "fuel_type": FuelType.ELECTRIC, "connector_type": ConnectorType.TYPE2, "power_type": "AC", "power_level": 22.0, "voltage": 400.0, "current": 32.0},
            # Dispositivi idrogeno
            {"identifier": "NAP_H2_H70_01", "fuel_type": FuelType.HYDROGEN, "connector_type": ConnectorType.H70, "dispensing_pressure": 700, "flow_rate": 2.3, "temperature_range_min": -40.0, "temperature_range_max": 85.0, "purity_level": 99.98},
            {"identifier": "NAP_H2_H70_02", "fuel_type": FuelType.HYDROGEN, "connector_type": ConnectorType.H70, "dispensing_pressure": 700, "flow_rate": 2.0, "temperature_range_min": -40.0, "temperature_range_max": 85.0, "purity_level": 99.98},
        ]
    }
]

# Dati per utenti di test
USER_DATA = [
    {"username": "mario_rossi", "email": "mario.rossi@email.com", "name": "Mario", "surname": "Rossi", "password": "password123"},
    {"username": "anna_verdi", "email": "anna.verdi@email.com", "name": "Anna", "surname": "Verdi", "password": "password123"},
    {"username": "luca_bianchi", "email": "luca.bianchi@email.com", "name": "Luca", "surname": "Bianchi", "password": "password123"},
    {"username": "sara_ferrari", "email": "sara.ferrari@email.com", "name": "Sara", "surname": "Ferrari", "password": "password123"},
    {"username": "giovanni_russo", "email": "giovanni.russo@email.com", "name": "Giovanni", "surname": "Russo", "password": "password123"},
    {"username": "elena_romano", "email": "elena.romano@email.com", "name": "Elena", "surname": "Romano", "password": "password123"},
]

def reset_orion_ld():
    """Reset completo di Orion-LD"""
    print("🗑️  Resetting Orion-LD...")
    
    orion_url = "http://localhost:1026/v2/entities"
    headers = {
        'Fiware-Service': 'sustainable_mobility',
        'Fiware-ServicePath': '/'
    }
    
    try:
        response = requests.get(orion_url, headers=headers)
        if response.status_code == 200:
            entities = response.json()
            print(f"   📊 Trovate {len(entities)} entità da eliminare")
            
            for entity in entities:
                delete_url = f"{orion_url}/{entity['id']}"
                delete_response = requests.delete(delete_url, headers=headers)
                if delete_response.status_code == 204:
                    print(f"   ✅ Eliminata entità: {entity['id']}")
        
        print("   ✅ Orion-LD resettato con successo")
        
    except Exception as e:
        print(f"   ⚠️  Avviso: Impossibile resettare Orion-LD: {str(e)}")

def reset_database():
    """Reset completo del database"""
    print("🗑️  Resetting database...")
    
    try:
        db.drop_all()
        db.create_all()
        print("   ✅ Database resettato con successo")
        return True
        
    except Exception as e:
        print(f"   ❌ Errore reset database: {str(e)}")
        return False

def create_test_users():
    """Crea utenti di test"""
    print("👥 Creando utenti di test...")
    
    created_users = []
    
    try:
        for user_data in USER_DATA:
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                name=user_data["name"],
                surname=user_data["surname"],
                is_station_manager=False,
                trust_score=random.randint(70, 100)
            )
            user.set_password(user_data["password"])
            
            db.session.add(user)
            created_users.append(user)
        
        db.session.commit()
        
        print(f"   ✅ Creati {len(created_users)} utenti di test")
        for user in created_users:
            print(f"   👤 {user.email} (password: password123)")
        
        return created_users
        
    except Exception as e:
        print(f"   ❌ Errore creazione utenti: {str(e)}")
        db.session.rollback()
        return []

def create_station_with_devices(station_data):
    """Crea una stazione con i suoi dispositivi"""
    station_name = station_data["name"]
    print(f"🏭 Creando stazione: {station_name}")
    
    try:
        # Crea stazione
        station_params = {k: v for k, v in station_data.items() if k != "devices"}
        station = Station(**station_params)
        
        # Crea manager della stazione
        manager_email = f"manager.{station.id or random.randint(1000, 9999)}@{station.company.lower().replace(' ', '').replace('.', '')}.com"
        manager = User(
            username=f"manager_{station.name.lower().replace(' ', '_')}",
            email=manager_email,
            name="Manager",
            surname=station.company.split()[0],
            is_station_manager=True
        )
        manager.set_password("manager123")
        
        db.session.add(station)
        db.session.add(manager)
        db.session.flush()
        
        # Associa manager alla stazione
        manager.station_id = station.id
        
        # Crea dispositivi
        created_devices = []
        for device_data in station_data["devices"]:
            device_params = device_data.copy()
            device_params["station_id"] = station.id
            device_params["status"] = "available"
            
            device = ChargingPoint(**device_params)
            db.session.add(device)
            created_devices.append(device)
        
        db.session.commit()
        
        print(f"   ✅ Stazione creata: {station.name}")
        print(f"   👤 Manager: {manager.email} (password: manager123)")
        print(f"   🔌 Dispositivi creati: {len(created_devices)}")
        
        # Crea digital twin
        try:
            create_station_digital_twin(station.id)
            for device in created_devices:
                create_device_digital_twin(device.id)
            print(f"   🌐 Digital twin creati per stazione e {len(created_devices)} dispositivi")
        except Exception as e:
            print(f"   ⚠️  Avviso digital twin: {str(e)}")
        
        return station, manager, created_devices
        
    except Exception as e:
        print(f"   ❌ Errore creazione stazione {station_name}: {str(e)}")
        db.session.rollback()
        return None, None, []

def print_summary(users, stations_data):
    """Stampa riepilogo finale"""
    print("\\n" + "="*80)
    print("🎉 CREAZIONE DATI DI TEST COMPLETATA!")
    print("="*80)
    
    print(f"\\n👥 UTENTI CREATI ({len(users)}):")
    for user in users:
        print(f"   📧 {user.email} ({user.name} {user.surname}) - Trust: {user.trust_score}")
    print(f"   🔑 Password per tutti gli utenti: password123")
    
    print(f"\\n🏭 STAZIONI CREATE ({len(stations_data)}):")
    total_devices = 0
    for i, (station, manager, devices) in enumerate(stations_data, 1):
        if station:
            station_type_icon = {
                'electric': '⚡',
                'hydrogen': '🔋', 
                'hybrid': '🔄'
            }.get(station.station_type, '🏢')
            
            print(f"\\n   {i}. {station_type_icon} {station.name}")
            print(f"      🏢 {station.company}")
            print(f"      📧 Manager: {manager.email}")
            print(f"      📍 {station.address}")
            print(f"      ⛽ Carburanti: {', '.join(station.fuel_types)}")
            print(f"      🔌 Dispositivi: {len(devices)}")
            
            # Dettagli dispositivi
            for device in devices:
                if device.fuel_type == FuelType.ELECTRIC:
                    print(f"         • {device.identifier}: {device.connector_type.value.upper()} {device.power_level}kW ({device.power_type})")
                else:
                    print(f"         • {device.identifier}: {device.connector_type.value.upper()} {device.dispensing_pressure}bar ({device.flow_rate}kg/min)")
            
            total_devices += len(devices)
    
    print(f"\\n📊 STATISTICHE FINALI:")
    print(f"   👥 Utenti totali: {len(users)}")
    print(f"   🏭 Stazioni totali: {len([s for s, _, _ in stations_data if s])}")
    print(f"   🔌 Dispositivi totali: {total_devices}")
    print(f"   🌐 Digital Twin: Attivi in Orion-LD")
    
    print(f"\\n🚀 COME TESTARE:")
    print(f"   1. Avvia app: python run.py")
    print(f"   2. Apri browser: http://localhost:5050")
    print(f"   3. Testa login utenti con qualsiasi email sopra")
    print(f"   4. Testa login manager stazioni")
    print(f"   5. Verifica disponibilità e prenotazioni")
    
    print("\\n" + "="*80)

def main():
    """Funzione principale"""
    print("🚀 CREAZIONE DATI DI TEST DETTAGLIATI PER MOBILITÀ SOSTENIBILE")
    print("=" * 80)
    
    app = create_app()
    
    with app.app_context():
        # 1. Reset Orion-LD
        reset_orion_ld()
        
        # 2. Reset Database
        if not reset_database():
            print("❌ Impossibile continuare senza database funzionante")
            return
        
        # 3. Crea utenti di test
        users = create_test_users()
        if not users:
            print("❌ Impossibile creare utenti di test")
            return
        
        # 4. Crea stazioni con dispositivi
        stations_data = []
        for station_data in STATION_DATA:
            station, manager, devices = create_station_with_devices(station_data)
            stations_data.append((station, manager, devices))
        
        # 5. Riepilogo finale
        successful_stations = [s for s, _, _ in stations_data if s]
        if successful_stations:
            print_summary(users, stations_data)
        else:
            print("❌ Nessuna stazione creata con successo")

if __name__ == "__main__":
    main()