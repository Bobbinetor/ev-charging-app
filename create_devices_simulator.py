#!/usr/bin/env python3
"""
Script per creare e simulare dispositivi di mobilità sostenibile
con digital twin completo per elettrico e idrogeno.
"""

import sys
import os
import time
import threading
import random
from datetime import datetime, timezone

# Aggiungi il path dell'app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Station, ChargingPoint, FuelType, ConnectorType
from app.services.digital_twin_service import (
    create_device_digital_twin, 
    create_station_digital_twin,
    update_device_telemetry,
    simulate_telemetry_data
)

class DeviceSimulator:
    def __init__(self):
        self.app = create_app()
        self.running = False
        self.simulation_threads = []

    def create_electric_station_with_devices(self, name, company, address, lat, lng, num_devices=4):
        """
        Crea una stazione elettrica con dispositivi di ricarica
        """
        with self.app.app_context():
            try:
                # Crea stazione
                station = Station(
                    name=name,
                    company=company,
                    address=address,
                    latitude=lat,
                    longitude=lng,
                    fuel_types=["electric"],
                    station_type="electric",
                    email=f"info@{company.lower().replace(' ', '')}.it",
                    phone="+39 06 12345678"
                )
                
                db.session.add(station)
                db.session.flush()  # Per ottenere l'ID
                
                print(f"✅ Stazione elettrica creata: {name} (ID: {station.id})")
                
                # Crea dispositivi di ricarica
                connectors = [ConnectorType.TYPE2, ConnectorType.CCS, ConnectorType.CHADEMO]
                devices = []
                
                for i in range(num_devices):
                    connector = random.choice(connectors)
                    is_fast = connector in [ConnectorType.CCS, ConnectorType.CHADEMO]
                    
                    device = ChargingPoint(
                        identifier=f"{name.replace(' ', '_').upper()}_EV_{i+1:02d}",
                        fuel_type=FuelType.ELECTRIC,
                        connector_type=connector,
                        status="available",
                        station_id=station.id,
                        power_type="DC" if is_fast else "AC",
                        power_level=random.choice([22, 50, 150, 350]) if is_fast else random.choice([7.4, 11, 22]),
                        voltage=random.choice([400, 800]) if is_fast else 230,
                        current=random.choice([125, 200, 500]) if is_fast else random.choice([16, 32])
                    )
                    
                    db.session.add(device)
                    devices.append(device)
                
                db.session.commit()
                
                # Crea digital twin
                create_station_digital_twin(station.id)
                
                for device in devices:
                    create_device_digital_twin(device.id)
                    print(f"  📱 Dispositivo elettrico: {device.identifier} ({device.power_level}kW {device.connector_type.value})")
                
                return station, devices
                
            except Exception as e:
                print(f"❌ Errore creazione stazione elettrica: {str(e)}")
                db.session.rollback()
                return None, []

    def create_hydrogen_station_with_devices(self, name, company, address, lat, lng, num_devices=2):
        """
        Crea una stazione idrogeno con distributori
        """
        with self.app.app_context():
            try:
                # Crea stazione
                station = Station(
                    name=name,
                    company=company,
                    address=address,
                    latitude=lat,
                    longitude=lng,
                    fuel_types=["hydrogen"],
                    station_type="hydrogen",
                    hydrogen_storage_capacity=1000,  # kg
                    hydrogen_purity=99.97,  # %
                    max_dispensing_pressure=700,  # bar
                    email=f"h2@{company.lower().replace(' ', '')}.it",
                    phone="+39 06 87654321"
                )
                
                db.session.add(station)
                db.session.flush()
                
                print(f"✅ Stazione idrogeno creata: {name} (ID: {station.id})")
                
                # Crea distributori idrogeno
                devices = []
                
                for i in range(num_devices):
                    pressure = random.choice([350, 700])  # bar
                    connector = ConnectorType.H35 if pressure == 350 else ConnectorType.H70
                    
                    device = ChargingPoint(
                        identifier=f"{name.replace(' ', '_').upper()}_H2_{i+1:02d}",
                        fuel_type=FuelType.HYDROGEN,
                        connector_type=connector,
                        status="available",
                        station_id=station.id,
                        dispensing_pressure=pressure,
                        flow_rate=random.uniform(1.0, 2.5),  # kg/min
                        temperature_range_min=-40,
                        temperature_range_max=85,
                        purity_level=99.97
                    )
                    
                    db.session.add(device)
                    devices.append(device)
                
                db.session.commit()
                
                # Crea digital twin
                create_station_digital_twin(station.id)
                
                for device in devices:
                    create_device_digital_twin(device.id)
                    print(f"  🔋 Distributore idrogeno: {device.identifier} ({device.dispensing_pressure} bar)")
                
                return station, devices
                
            except Exception as e:
                print(f"❌ Errore creazione stazione idrogeno: {str(e)}")
                db.session.rollback()
                return None, []

    def create_hybrid_station_with_devices(self, name, company, address, lat, lng):
        """
        Crea una stazione ibrida con dispositivi elettrici e idrogeno
        """
        with self.app.app_context():
            try:
                # Crea stazione
                station = Station(
                    name=name,
                    company=company,
                    address=address,
                    latitude=lat,
                    longitude=lng,
                    fuel_types=["electric", "hydrogen"],
                    station_type="hybrid",
                    hydrogen_storage_capacity=500,  # kg
                    hydrogen_purity=99.97,  # %
                    max_dispensing_pressure=700,  # bar
                    email=f"hybrid@{company.lower().replace(' ', '')}.it",
                    phone="+39 06 11111111"
                )
                
                db.session.add(station)
                db.session.flush()
                
                print(f"✅ Stazione ibrida creata: {name} (ID: {station.id})")
                
                devices = []
                
                # Dispositivi elettrici
                for i in range(2):
                    device = ChargingPoint(
                        identifier=f"{name.replace(' ', '_').upper()}_EV_{i+1:02d}",
                        fuel_type=FuelType.ELECTRIC,
                        connector_type=ConnectorType.CCS,
                        status="available",
                        station_id=station.id,
                        power_type="DC",
                        power_level=150,
                        voltage=400,
                        current=200
                    )
                    db.session.add(device)
                    devices.append(device)
                
                # Dispositori idrogeno
                for i in range(1):
                    device = ChargingPoint(
                        identifier=f"{name.replace(' ', '_').upper()}_H2_{i+1:02d}",
                        fuel_type=FuelType.HYDROGEN,
                        connector_type=ConnectorType.H70,
                        status="available",
                        station_id=station.id,
                        dispensing_pressure=700,
                        flow_rate=2.0,
                        temperature_range_min=-40,
                        temperature_range_max=85,
                        purity_level=99.97
                    )
                    db.session.add(device)
                    devices.append(device)
                
                db.session.commit()
                
                # Crea digital twin
                create_station_digital_twin(station.id)
                
                for device in devices:
                    create_device_digital_twin(device.id)
                    if device.fuel_type == FuelType.ELECTRIC:
                        print(f"  ⚡ Dispositivo elettrico: {device.identifier} ({device.power_level}kW)")
                    else:
                        print(f"  🔋 Distributore idrogeno: {device.identifier} ({device.dispensing_pressure} bar)")
                
                return station, devices
                
            except Exception as e:
                print(f"❌ Errore creazione stazione ibrida: {str(e)}")
                db.session.rollback()
                return None, []

    def start_telemetry_simulation(self, device_id, fuel_type, interval=5):
        """
        Avvia simulazione telemetria per un dispositivo
        """
        def simulate():
            while self.running:
                try:
                    with self.app.app_context():
                        telemetry = simulate_telemetry_data(fuel_type)
                        success = update_device_telemetry(device_id, telemetry)
                        if success:
                            print(f"📊 Telemetria aggiornata per dispositivo {device_id}: {telemetry}")
                        time.sleep(interval)
                except Exception as e:
                    print(f"❌ Errore simulazione telemetria: {str(e)}")
                    time.sleep(interval)
        
        thread = threading.Thread(target=simulate, daemon=True)
        self.simulation_threads.append(thread)
        thread.start()

    def start_simulation(self, devices, interval=10):
        """
        Avvia simulazione per tutti i dispositivi
        """
        self.running = True
        print(f"\n🚀 Avvio simulazione telemetria (intervallo: {interval}s)")
        
        for device in devices:
            self.start_telemetry_simulation(device.id, device.fuel_type, interval)
        
        print(f"📡 Simulazione attiva per {len(devices)} dispositivi")

    def stop_simulation(self):
        """
        Ferma la simulazione
        """
        self.running = False
        print("\n⏹️  Simulazione fermata")

def main():
    print("🏭 === SIMULATORE INFRASTRUTTURA MOBILITÀ SOSTENIBILE ===\n")
    
    simulator = DeviceSimulator()
    all_devices = []
    
    try:
        # Stazioni elettriche
        print("⚡ Creazione stazioni elettriche...")
        station1, devices1 = simulator.create_electric_station_with_devices(
            "Roma EUR Electric Hub", "E-Mobility Italia", 
            "Via Cristoforo Colombo 100, Roma", 41.8338, 12.4677, 6
        )
        all_devices.extend(devices1)
        
        station2, devices2 = simulator.create_electric_station_with_devices(
            "Milano Centrale EV", "Green Energy S.p.A.", 
            "Piazza Duca d'Aosta 1, Milano", 45.4866, 9.2045, 4
        )
        all_devices.extend(devices2)
        
        # Stazioni idrogeno
        print("\n🔋 Creazione stazioni idrogeno...")
        station3, devices3 = simulator.create_hydrogen_station_with_devices(
            "Torino H2 Station", "Hydrogen Power Italy", 
            "Corso Francia 200, Torino", 45.0878, 7.6561, 3
        )
        all_devices.extend(devices3)
        
        station4, devices4 = simulator.create_hydrogen_station_with_devices(
            "Napoli Hydrogen Hub", "Clean Energy Sud", 
            "Via Marina 100, Napoli", 40.8396, 14.2536, 2
        )
        all_devices.extend(devices4)
        
        # Stazione ibrida
        print("\n🔄 Creazione stazione ibrida...")
        station5, devices5 = simulator.create_hybrid_station_with_devices(
            "Bologna Multimodal Energy", "Future Mobility S.r.l.", 
            "Via dell'Indipendenza 50, Bologna", 44.4938, 11.3387
        )
        all_devices.extend(devices5)
        
        print(f"\n✅ Infrastruttura creata con successo!")
        print(f"📊 Totale: {len(all_devices)} dispositivi in {5} stazioni")
        print(f"   ⚡ Elettrici: {len([d for d in all_devices if d.fuel_type == FuelType.ELECTRIC])}")
        print(f"   🔋 Idrogeno: {len([d for d in all_devices if d.fuel_type == FuelType.HYDROGEN])}")
        
        # Avvia simulazione
        choice = input("\n🤖 Vuoi avviare la simulazione telemetrica in tempo reale? (y/n): ")
        if choice.lower() == 'y':
            interval = input("📡 Intervallo di aggiornamento in secondi (default: 10): ")
            try:
                interval = int(interval) if interval else 10
            except:
                interval = 10
            
            simulator.start_simulation(all_devices, interval)
            
            print("\n💡 Premi CTRL+C per fermare la simulazione")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                simulator.stop_simulation()
        
        print("\n🎉 Simulazione completata con successo!")
        
    except Exception as e:
        print(f"❌ Errore durante l'esecuzione: {str(e)}")
        simulator.stop_simulation()

if __name__ == "__main__":
    main()