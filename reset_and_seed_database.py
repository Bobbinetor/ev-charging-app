#!/usr/bin/env python3
"""
Script per resettare il database e Orion-LD e creare dati di test completi
per la piattaforma di mobilità sostenibile.
"""

import sys
import os
import requests
import json
from datetime import datetime, timezone

# Aggiungi il path dell'app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Station, ChargingPoint, FuelType, ConnectorType
from app.services.digital_twin_service import create_device_digital_twin, create_station_digital_twin

def reset_orion_ld():
    """Reset completo di Orion-LD"""
    print("🗑️  Resetting Orion-LD...")
    
    # URL per eliminare tutte le entità
    orion_url = "http://localhost:1026/v2/entities"
    headers = {
        'Fiware-Service': 'sustainable_mobility',
        'Fiware-ServicePath': '/'
    }
    
    try:
        # Ottieni tutte le entità
        response = requests.get(orion_url, headers=headers)
        if response.status_code == 200:
            entities = response.json()
            print(f"   📊 Trovate {len(entities)} entità da eliminare")
            
            # Elimina ogni entità
            for entity in entities:
                delete_url = f"{orion_url}/{entity['id']}"
                delete_response = requests.delete(delete_url, headers=headers)
                if delete_response.status_code == 204:
                    print(f"   ✅ Eliminata entità: {entity['id']}")
                else:
                    print(f"   ❌ Errore eliminazione {entity['id']}: {delete_response.status_code}")
        
        print("   ✅ Orion-LD resettato con successo")
        
    except Exception as e:
        print(f"   ⚠️  Avviso: Impossibile resettare Orion-LD: {str(e)}")
        print("   📝 Assicurati che Orion-LD sia in esecuzione con 'docker-compose up -d'")

def reset_database():
    """Reset completo del database"""
    print("🗑️  Resetting database...")
    
    try:
        # Drop e ricrea tutte le tabelle
        db.drop_all()
        db.create_all()
        print("   ✅ Database resettato con successo")
        
    except Exception as e:
        print(f"   ❌ Errore reset database: {str(e)}")
        return False
    
    return True

def create_test_user():
    """Crea utente di test"""
    print("👤 Creando utente di test...")
    
    try:
        user = User(
            username="test_user",
            email="user@test.com",
            name="Marco",
            surname="Rossi",
            is_station_manager=False,
            trust_score=0
        )
        user.set_password("password123")
        
        db.session.add(user)
        db.session.commit()
        
        print(f"   ✅ Utente creato: {user.email} (password: password123)")
        return user
        
    except Exception as e:
        print(f"   ❌ Errore creazione utente: {str(e)}")
        db.session.rollback()
        return None

def create_electric_station():
    """Crea stazione elettrica di test"""
    print("⚡ Creando stazione elettrica...")
    
    try:
        # Crea stazione
        station = Station(
            name="Roma EUR Electric Hub",
            company="E-Mobility Italia S.p.A.",
            vat_number="12345678901",
            address="Via Cristoforo Colombo 100, Roma EUR",
            latitude=41.8338,
            longitude=12.4677,
            email="info@emobility.it",
            phone="+39 06 12345678",
            fuel_types=["electric"],
            station_type="electric"
        )
        
        # Crea manager della stazione
        manager = User(
            username="electric_manager",
            email="manager@emobility.it", 
            name="Luigi",
            surname="Verdi",
            is_station_manager=True
        )
        manager.set_password("manager123")
        
        db.session.add(station)
        db.session.add(manager)
        db.session.flush()
        
        # Associa manager alla stazione
        manager.station_id = station.id
        
        # Crea dispositivi elettrici
        devices = [
            {
                "identifier": "ROMA_EUR_EV_01",
                "fuel_type": FuelType.ELECTRIC,
                "connector_type": ConnectorType.TYPE2,
                "power_type": "AC",
                "power_level": 22.0,
                "voltage": 400.0,
                "current": 32.0
            },
            {
                "identifier": "ROMA_EUR_EV_02", 
                "fuel_type": FuelType.ELECTRIC,
                "connector_type": ConnectorType.CCS,
                "power_type": "DC",
                "power_level": 150.0,
                "voltage": 800.0,
                "current": 200.0
            },
            {
                "identifier": "ROMA_EUR_EV_03",
                "fuel_type": FuelType.ELECTRIC,
                "connector_type": ConnectorType.CHADEMO,
                "power_type": "DC", 
                "power_level": 50.0,
                "voltage": 400.0,
                "current": 125.0
            }
        ]
        
        created_devices = []
        for device_data in devices:
            device = ChargingPoint(
                identifier=device_data["identifier"],
                fuel_type=device_data["fuel_type"],
                connector_type=device_data["connector_type"],
                power_type=device_data["power_type"],
                power_level=device_data["power_level"],
                voltage=device_data["voltage"],
                current=device_data["current"],
                status="available",
                station_id=station.id
            )
            db.session.add(device)
            created_devices.append(device)
        
        db.session.commit()
        
        print(f"   ✅ Stazione elettrica creata: {station.name}")
        print(f"   👤 Manager: {manager.email} (password: manager123)")
        print(f"   🔌 Dispositivi creati: {len(created_devices)}")
        
        # Crea digital twin
        create_station_digital_twin(station.id)
        for device in created_devices:
            create_device_digital_twin(device.id)
        
        return station, manager, created_devices
        
    except Exception as e:
        print(f"   ❌ Errore creazione stazione elettrica: {str(e)}")
        db.session.rollback()
        return None, None, []

def create_hydrogen_station():
    """Crea stazione idrogeno di test"""
    print("🔋 Creando stazione idrogeno...")
    
    try:
        # Crea stazione
        station = Station(
            name="Milano H2 Hub",
            company="Hydrogen Power Italy S.r.l.",
            vat_number="98765432109",
            address="Via Brera 15, Milano Centro",
            latitude=45.4654,
            longitude=9.1859,
            email="info@h2power.it",
            phone="+39 02 87654321",
            fuel_types=["hydrogen"],
            station_type="hydrogen",
            hydrogen_storage_capacity=1000.0,
            hydrogen_purity=99.97,
            max_dispensing_pressure=700
        )
        
        # Crea manager della stazione
        manager = User(
            username="hydrogen_manager",
            email="manager@h2power.it",
            name="Anna",
            surname="Bianchi", 
            is_station_manager=True
        )
        manager.set_password("h2manager123")
        
        db.session.add(station)
        db.session.add(manager)
        db.session.flush()
        
        # Associa manager alla stazione
        manager.station_id = station.id
        
        # Crea dispositivi idrogeno
        devices = [
            {
                "identifier": "MILANO_H2_01",
                "fuel_type": FuelType.HYDROGEN,
                "connector_type": ConnectorType.H70,
                "dispensing_pressure": 700,
                "flow_rate": 2.0,
                "temperature_range_min": -40.0,
                "temperature_range_max": 85.0,
                "purity_level": 99.97
            },
            {
                "identifier": "MILANO_H2_02",
                "fuel_type": FuelType.HYDROGEN,
                "connector_type": ConnectorType.H35,
                "dispensing_pressure": 350,
                "flow_rate": 1.5,
                "temperature_range_min": -40.0,
                "temperature_range_max": 85.0,
                "purity_level": 99.95
            }
        ]
        
        created_devices = []
        for device_data in devices:
            device = ChargingPoint(
                identifier=device_data["identifier"],
                fuel_type=device_data["fuel_type"],
                connector_type=device_data["connector_type"],
                dispensing_pressure=device_data["dispensing_pressure"],
                flow_rate=device_data["flow_rate"],
                temperature_range_min=device_data["temperature_range_min"],
                temperature_range_max=device_data["temperature_range_max"],
                purity_level=device_data["purity_level"],
                status="available",
                station_id=station.id
            )
            db.session.add(device)
            created_devices.append(device)
        
        db.session.commit()
        
        print(f"   ✅ Stazione idrogeno creata: {station.name}")
        print(f"   👤 Manager: {manager.email} (password: h2manager123)")
        print(f"   🔋 Dispositivi creati: {len(created_devices)}")
        
        # Crea digital twin
        create_station_digital_twin(station.id)
        for device in created_devices:
            create_device_digital_twin(device.id)
        
        return station, manager, created_devices
        
    except Exception as e:
        print(f"   ❌ Errore creazione stazione idrogeno: {str(e)}")
        db.session.rollback()
        return None, None, []

def create_hybrid_station():
    """Crea stazione ibrida di test"""
    print("🔄 Creando stazione ibrida...")
    
    try:
        # Crea stazione
        station = Station(
            name="Bologna Multimodal Energy",
            company="Future Mobility S.r.l.",
            vat_number="11223344556",
            address="Via dell'Indipendenza 50, Bologna",
            latitude=44.4938,
            longitude=11.3387,
            email="info@futuremobility.it",
            phone="+39 051 11111111",
            fuel_types=["electric", "hydrogen"],
            station_type="hybrid",
            hydrogen_storage_capacity=500.0,
            hydrogen_purity=99.97,
            max_dispensing_pressure=700
        )
        
        # Crea manager della stazione
        manager = User(
            username="hybrid_manager",
            email="manager@futuremobility.it",
            name="Roberto",
            surname="Neri",
            is_station_manager=True
        )
        manager.set_password("hybrid123")
        
        db.session.add(station)
        db.session.add(manager)
        db.session.flush()
        
        # Associa manager alla stazione
        manager.station_id = station.id
        
        # Crea dispositivi ibridi
        devices = [
            # Dispositivi elettrici
            {
                "identifier": "BOLOGNA_EV_01",
                "fuel_type": FuelType.ELECTRIC,
                "connector_type": ConnectorType.CCS,
                "power_type": "DC",
                "power_level": 150.0,
                "voltage": 400.0,
                "current": 200.0
            },
            {
                "identifier": "BOLOGNA_EV_02",
                "fuel_type": FuelType.ELECTRIC,
                "connector_type": ConnectorType.TYPE2,
                "power_type": "AC",
                "power_level": 22.0,
                "voltage": 400.0,
                "current": 32.0
            },
            # Dispositivo idrogeno
            {
                "identifier": "BOLOGNA_H2_01",
                "fuel_type": FuelType.HYDROGEN,
                "connector_type": ConnectorType.H70,
                "dispensing_pressure": 700,
                "flow_rate": 2.0,
                "temperature_range_min": -40.0,
                "temperature_range_max": 85.0,
                "purity_level": 99.97
            }
        ]
        
        created_devices = []
        for device_data in devices:
            if device_data["fuel_type"] == FuelType.ELECTRIC:
                device = ChargingPoint(
                    identifier=device_data["identifier"],
                    fuel_type=device_data["fuel_type"],
                    connector_type=device_data["connector_type"],
                    power_type=device_data["power_type"],
                    power_level=device_data["power_level"],
                    voltage=device_data["voltage"],
                    current=device_data["current"],
                    status="available",
                    station_id=station.id
                )
            else:  # HYDROGEN
                device = ChargingPoint(
                    identifier=device_data["identifier"],
                    fuel_type=device_data["fuel_type"],
                    connector_type=device_data["connector_type"],
                    dispensing_pressure=device_data["dispensing_pressure"],
                    flow_rate=device_data["flow_rate"],
                    temperature_range_min=device_data["temperature_range_min"],
                    temperature_range_max=device_data["temperature_range_max"],
                    purity_level=device_data["purity_level"],
                    status="available",
                    station_id=station.id
                )
            
            db.session.add(device)
            created_devices.append(device)
        
        db.session.commit()
        
        print(f"   ✅ Stazione ibrida creata: {station.name}")
        print(f"   👤 Manager: {manager.email} (password: hybrid123)")
        print(f"   🔄 Dispositivi creati: {len(created_devices)} (elettrici + idrogeno)")
        
        # Crea digital twin
        create_station_digital_twin(station.id)
        for device in created_devices:
            create_device_digital_twin(device.id)
        
        return station, manager, created_devices
        
    except Exception as e:
        print(f"   ❌ Errore creazione stazione ibrida: {str(e)}")
        db.session.rollback()
        return None, None, []

def print_summary(user, stations, managers, devices_count):
    """Stampa riepilogo finale"""
    print("\n" + "="*60)
    print("🎉 SETUP COMPLETATO CON SUCCESSO!")
    print("="*60)
    
    print(f"\n👤 UTENTE DI TEST:")
    print(f"   📧 Email: {user.email}")
    print(f"   🔑 Password: password123")
    print(f"   🌐 URL Login: http://localhost:5050/auth/login")
    
    print(f"\n🏭 STAZIONI CREATE ({len(stations)}):")
    for i, (station, manager) in enumerate(zip(stations, managers), 1):
        station_type_icon = {
            'electric': '⚡',
            'hydrogen': '🔋', 
            'hybrid': '🔄'
        }.get(station.station_type, '🏢')
        
        print(f"\n   {i}. {station_type_icon} {station.name}")
        print(f"      📧 Manager: {manager.email}")
        print(f"      🔑 Password: {'manager123' if 'electric' in manager.email else 'h2manager123' if 'h2power' in manager.email else 'hybrid123'}")
        print(f"      📍 {station.address}")
        print(f"      ⛽ Carburanti: {', '.join(station.fuel_types or ['electric'])}")
    
    print(f"\n📊 STATISTICHE:")
    print(f"   🔌 Dispositivi totali: {devices_count}")
    print(f"   🌐 Digital Twin: Attivi in Orion-LD")
    print(f"   🔗 FIWARE Service: sustainable_mobility")
    
    print(f"\n🚀 NEXT STEPS:")
    print(f"   1. Avvia app: python run.py")
    print(f"   2. Apri browser: http://localhost:5050")
    print(f"   3. Testa login utente e manager")
    print(f"   4. Verifica Orion-LD: curl -H 'Fiware-Service: sustainable_mobility' http://localhost:1026/v2/entities")
    
    print("\n" + "="*60)

def main():
    """Funzione principale"""
    print("🏭 RESET E SETUP DATABASE MOBILITÀ SOSTENIBILE")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        # 1. Reset Orion-LD
        reset_orion_ld()
        
        # 2. Reset Database
        if not reset_database():
            print("❌ Impossibile continuare senza database funzionante")
            return
        
        # 3. Crea utente di test
        user = create_test_user()
        if not user:
            print("❌ Impossibile creare utente di test")
            return
        
        # 4. Crea stazioni
        stations = []
        managers = []
        total_devices = 0
        
        # Stazione elettrica
        station1, manager1, devices1 = create_electric_station()
        if station1:
            stations.append(station1)
            managers.append(manager1)
            total_devices += len(devices1)
        
        # Stazione idrogeno
        station2, manager2, devices2 = create_hydrogen_station()
        if station2:
            stations.append(station2)
            managers.append(manager2)
            total_devices += len(devices2)
        
        # Stazione ibrida
        station3, manager3, devices3 = create_hybrid_station()
        if station3:
            stations.append(station3)
            managers.append(manager3)
            total_devices += len(devices3)
        
        # 5. Riepilogo finale
        if stations:
            print_summary(user, stations, managers, total_devices)
        else:
            print("❌ Nessuna stazione creata con successo")

if __name__ == "__main__":
    main()