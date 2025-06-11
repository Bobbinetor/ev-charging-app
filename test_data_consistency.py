#!/usr/bin/env python3
"""
Test per verificare la consistenza dei dati tra Database e Orion-LD
"""

import requests
import json
import sys
import os
from datetime import datetime

# Aggiungi il path dell'app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Station, ChargingPoint, FuelType, ConnectorType

# Configurazione Orion-LD
ORION_URL = "http://localhost:1026/v2/entities"
ORION_HEADERS = {
    'Fiware-Service': 'ev_charging',
    'Fiware-ServicePath': '/'
}

class DataConsistencyTester:
    def __init__(self):
        self.app = create_app()
        self.issues = []
        
    def log_issue(self, category, description, severity="warning"):
        """Registra un problema di consistenza"""
        self.issues.append({
            'category': category,
            'description': description,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        })
        
        icon = "🔴" if severity == "error" else "🟡" if severity == "warning" else "🔵"
        print(f"{icon} [{category}] {description}")
    
    def log_success(self, category, description):
        """Registra un controllo passato"""
        print(f"✅ [{category}] {description}")
    
    def get_orion_entities(self):
        """Recupera tutte le entità da Orion-LD"""
        try:
            response = requests.get(ORION_URL, headers=ORION_HEADERS)
            if response.status_code == 200:
                return response.json()
            else:
                self.log_issue("Orion Connection", f"Errore connessione Orion-LD: {response.status_code}", "error")
                return []
        except Exception as e:
            self.log_issue("Orion Connection", f"Impossibile connettersi a Orion-LD: {str(e)}", "error")
            return []
    
    def test_station_consistency(self):
        """Verifica consistenza delle stazioni"""
        print("\n🏭 Test consistenza stazioni...")
        
        with self.app.app_context():
            # Ottieni stazioni dal database
            db_stations = Station.query.all()
            
            # Ottieni entità da Orion-LD
            orion_entities = self.get_orion_entities()
            station_entities = [e for e in orion_entities if e['type'] in ['ChargingStation', 'HydrogenStation']]
            
            print(f"   Database: {len(db_stations)} stazioni")
            print(f"   Orion-LD: {len(station_entities)} entità stazione")
            
            # Verifica che ogni stazione DB abbia la corrispondente entità
            for station in db_stations:
                station_type = "HydrogenStation" if (station.station_type == 'hydrogen' or 'hydrogen' in (station.fuel_types or [])) else "ChargingStation"
                entity_id = f"urn:ngsi-ld:{station_type}:{station.id}"
                
                orion_entity = next((e for e in station_entities if e['id'] == entity_id), None)
                
                if orion_entity:
                    self.log_success("Station Sync", f"Stazione {station.name} sincronizzata")
                    
                    # Verifica campi specifici
                    self.verify_station_fields(station, orion_entity)
                else:
                    self.log_issue("Station Sync", f"Stazione {station.name} (ID: {station.id}) mancante in Orion-LD", "error")
            
            # Verifica entità orfane in Orion-LD
            for entity in station_entities:
                entity_id = entity['id']
                station_id = entity_id.split(':')[-1]
                
                try:
                    db_station = Station.query.get(int(station_id))
                    if not db_station:
                        self.log_issue("Orphan Entity", f"Entità Orion-LD {entity_id} non ha corrispondente nel DB", "warning")
                except ValueError:
                    self.log_issue("Entity ID", f"ID entità non valido: {entity_id}", "warning")
    
    def verify_station_fields(self, db_station, orion_entity):
        """Verifica la consistenza dei campi della stazione"""
        # Verifica nome
        orion_name = orion_entity.get('name', {}).get('value', '')
        if orion_name != db_station.name:
            self.log_issue("Field Mismatch", f"Nome stazione {db_station.id}: DB='{db_station.name}' vs Orion='{orion_name}'", "warning")
        
        # Verifica tipo carburante
        orion_fuel_types = orion_entity.get('fuelTypes', {}).get('value', [])
        db_fuel_types = db_station.fuel_types or ['electric']
        
        if set(orion_fuel_types) != set(db_fuel_types):
            self.log_issue("Field Mismatch", f"Tipi carburante stazione {db_station.id}: DB={db_fuel_types} vs Orion={orion_fuel_types}", "warning")
    
    def test_device_consistency(self):
        """Verifica consistenza dei dispositivi"""
        print("\n🔌 Test consistenza dispositivi...")
        
        with self.app.app_context():
            # Ottieni dispositivi dal database
            db_devices = ChargingPoint.query.all()
            
            # Ottieni entità da Orion-LD
            orion_entities = self.get_orion_entities()
            device_entities = [e for e in orion_entities if e['type'] in ['ChargingDevice', 'HydrogenDispenser']]
            
            print(f"   Database: {len(db_devices)} dispositivi")
            print(f"   Orion-LD: {len(device_entities)} entità dispositivo")
            
            # Verifica che ogni dispositivo DB abbia la corrispondente entità
            for device in db_devices:
                device_type = "HydrogenDispenser" if device.fuel_type == FuelType.HYDROGEN else "ChargingDevice"
                entity_id = f"urn:ngsi-ld:{device_type}:{device.id}"
                
                orion_entity = next((e for e in device_entities if e['id'] == entity_id), None)
                
                if orion_entity:
                    self.log_success("Device Sync", f"Dispositivo {device.identifier} sincronizzato")
                    
                    # Verifica campi specifici
                    self.verify_device_fields(device, orion_entity)
                else:
                    self.log_issue("Device Sync", f"Dispositivo {device.identifier} (ID: {device.id}) mancante in Orion-LD", "error")
            
            # Verifica entità orfane in Orion-LD
            for entity in device_entities:
                entity_id = entity['id']
                device_id = entity_id.split(':')[-1]
                
                try:
                    db_device = ChargingPoint.query.get(int(device_id))
                    if not db_device:
                        self.log_issue("Orphan Entity", f"Entità Orion-LD {entity_id} non ha corrispondente nel DB", "warning")
                except ValueError:
                    self.log_issue("Entity ID", f"ID entità non valido: {entity_id}", "warning")
    
    def verify_device_fields(self, db_device, orion_entity):
        """Verifica la consistenza dei campi del dispositivo"""
        # Verifica identifier
        orion_identifier = orion_entity.get('identifier', {}).get('value', '')
        if orion_identifier != db_device.identifier:
            self.log_issue("Field Mismatch", f"Identificatore dispositivo {db_device.id}: DB='{db_device.identifier}' vs Orion='{orion_identifier}'", "warning")
        
        # Verifica tipo carburante
        orion_fuel_type = orion_entity.get('fuelType', {}).get('value', '')
        db_fuel_type = db_device.fuel_type.value
        
        if orion_fuel_type != db_fuel_type:
            self.log_issue("Field Mismatch", f"Tipo carburante dispositivo {db_device.id}: DB='{db_fuel_type}' vs Orion='{orion_fuel_type}'", "warning")
        
        # Verifica campi specifici per tipo
        if db_device.fuel_type == FuelType.ELECTRIC:
            # Verifica potenza
            orion_power = orion_entity.get('powerLevel', {}).get('value')
            if orion_power != db_device.power_level:
                self.log_issue("Field Mismatch", f"Potenza dispositivo {db_device.id}: DB={db_device.power_level} vs Orion={orion_power}", "warning")
        
        elif db_device.fuel_type == FuelType.HYDROGEN:
            # Verifica pressione
            orion_pressure = orion_entity.get('dispensingPressure', {}).get('value')
            if orion_pressure != db_device.dispensing_pressure:
                self.log_issue("Field Mismatch", f"Pressione dispositivo {db_device.id}: DB={db_device.dispensing_pressure} vs Orion={orion_pressure}", "warning")
    
    def test_data_integrity(self):
        """Verifica l'integrità dei dati"""
        print("\n🔍 Test integrità dati...")
        
        with self.app.app_context():
            # Verifica relazioni stazione-dispositivi
            stations = Station.query.all()
            
            for station in stations:
                devices = ChargingPoint.query.filter_by(station_id=station.id).all()
                
                # Verifica che tutti i dispositivi abbiano il tipo di carburante supportato dalla stazione
                station_fuel_types = station.fuel_types or ['electric']
                
                for device in devices:
                    device_fuel_type = device.fuel_type.value
                    
                    if device_fuel_type not in station_fuel_types:
                        self.log_issue("Data Integrity", 
                                     f"Dispositivo {device.identifier} ha carburante '{device_fuel_type}' "
                                     f"ma stazione {station.name} supporta solo {station_fuel_types}", 
                                     "error")
                    else:
                        self.log_success("Data Integrity", f"Dispositivo {device.identifier} compatibile con stazione {station.name}")
                
                # Verifica che le stazioni ibride abbiano almeno un dispositivo per tipo
                if station.station_type == 'hybrid':
                    electric_devices = [d for d in devices if d.fuel_type == FuelType.ELECTRIC]
                    hydrogen_devices = [d for d in devices if d.fuel_type == FuelType.HYDROGEN]
                    
                    if not electric_devices:
                        self.log_issue("Data Integrity", f"Stazione ibrida {station.name} non ha dispositivi elettrici", "warning")
                    
                    if not hydrogen_devices:
                        self.log_issue("Data Integrity", f"Stazione ibrida {station.name} non ha dispositivi idrogeno", "warning")
    
    def test_booking_constraints(self):
        """Verifica i vincoli delle prenotazioni"""
        print("\n📅 Test vincoli prenotazioni...")
        
        with self.app.app_context():
            from app.models import ChargingSession
            
            # Verifica che tutte le sessioni di ricarica abbiano dispositivi validi
            sessions = ChargingSession.query.all()
            
            for session in sessions:
                device = ChargingPoint.query.get(session.charging_point_id)
                
                if not device:
                    self.log_issue("Booking Constraint", f"Sessione {session.id} riferisce dispositivo inesistente {session.charging_point_id}", "error")
                    continue
                
                station = Station.query.get(device.station_id)
                if not station:
                    self.log_issue("Booking Constraint", f"Dispositivo {device.id} riferisce stazione inesistente {device.station_id}", "error")
                    continue
                
                # Verifica coerenza tipo carburante sessione-dispositivo
                if session.fuel_type != device.fuel_type:
                    self.log_issue("Booking Constraint", 
                                 f"Sessione {session.id} ha carburante {session.fuel_type.value} "
                                 f"ma dispositivo {device.identifier} ha {device.fuel_type.value}", 
                                 "error")
                else:
                    self.log_success("Booking Constraint", f"Sessione {session.id} coerente con dispositivo {device.identifier}")
    
    def print_summary(self):
        """Stampa il riepilogo dei problemi trovati"""
        print("\n" + "="*80)
        print("📊 RIEPILOGO TEST CONSISTENZA DATI")
        print("="*80)
        
        if not self.issues:
            print("\n🎉 NESSUN PROBLEMA DI CONSISTENZA TROVATO!")
            print("   Tutti i dati sono sincronizzati correttamente tra Database e Orion-LD.")
        else:
            errors = [i for i in self.issues if i['severity'] == 'error']
            warnings = [i for i in self.issues if i['severity'] == 'warning']
            infos = [i for i in self.issues if i['severity'] == 'info']
            
            print(f"\n📈 STATISTICHE:")
            print(f"   🔴 Errori: {len(errors)}")
            print(f"   🟡 Warning: {len(warnings)}")
            print(f"   🔵 Info: {len(infos)}")
            print(f"   📊 Totale problemi: {len(self.issues)}")
            
            if errors:
                print(f"\n🔴 ERRORI CRITICI:")
                for issue in errors:
                    print(f"   • [{issue['category']}] {issue['description']}")
            
            if warnings:
                print(f"\n🟡 WARNING:")
                for issue in warnings:
                    print(f"   • [{issue['category']}] {issue['description']}")
            
            if infos:
                print(f"\n🔵 INFORMAZIONI:")
                for issue in infos:
                    print(f"   • [{issue['category']}] {issue['description']}")
        
        print("="*80)
    
    def run_all_tests(self):
        """Esegue tutti i test di consistenza"""
        print("🔍 INIZIO TEST CONSISTENZA DATI DATABASE-ORION")
        print("="*80)
        
        self.test_station_consistency()
        self.test_device_consistency()
        self.test_data_integrity()
        self.test_booking_constraints()
        
        self.print_summary()

def main():
    tester = DataConsistencyTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()