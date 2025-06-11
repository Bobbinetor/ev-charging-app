#!/usr/bin/env python3

import requests
import json
from bs4 import BeautifulSoup

# URL base del server Flask
BASE_URL = "http://127.0.0.1:5050"

def login_as_station_manager():
    """Login come gestore stazione"""
    print("🔐 Login come gestore stazione...")
    
    # Ottieni la pagina di login
    session = requests.Session()
    response = session.get(f"{BASE_URL}/auth/login")
    soup = BeautifulSoup(response.content, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
    
    # Login con credenziali gestore stazione (da test registration)
    login_data = {
        'csrf_token': csrf_token,
        'email': 'test.station@example.com',
        'password': 'test12345',
        'remember_me': False
    }
    
    response = session.post(f"{BASE_URL}/auth/login", data=login_data, allow_redirects=False)
    
    if response.status_code == 302 and 'dashboard' in response.headers.get('Location', ''):
        print("✅ Login riuscito!")
        return session
    else:
        print(f"❌ Login fallito: {response.status_code}")
        print(response.text)
        return None

def test_dashboard_access(session):
    """Testa l'accesso alla dashboard"""
    print("📊 Test accesso dashboard...")
    
    response = session.get(f"{BASE_URL}/auth/station/dashboard")
    
    if response.status_code == 200:
        print("✅ Dashboard accessibile")
        
        # Verifica presenza del nuovo form guidato
        if 'Passaggio 1: Seleziona Tipo Carburante' in response.text:
            print("✅ Form guidato presente")
            return True
        else:
            print("❌ Form guidato non trovato")
            return False
    else:
        print(f"❌ Errore accesso dashboard: {response.status_code}")
        return False

def test_add_electric_device(session):
    """Testa aggiunta device elettrico"""
    print("⚡ Test aggiunta device elettrico...")
    
    device_data = {
        'device_id': 'StazioneTestElettrica_EV_50kW_01',
        'fuel_type': 'electric',
        'power_type': 'DC',
        'power_level': 50.0,
        'connector_type': 'ccs',
        'voltage': 400
    }
    
    response = session.post(
        f"{BASE_URL}/auth/station/add_device",
        json=device_data,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"✅ Device elettrico aggiunto: {data.get('device_identifier')}")
            return True
        else:
            print(f"❌ Errore aggiunta device: {data.get('error')}")
            return False
    else:
        print(f"❌ Errore HTTP: {response.status_code}")
        print(response.text)
        return False

def test_add_hydrogen_device(session):
    """Testa aggiunta device idrogeno (se disponibile)"""
    print("🔋 Test aggiunta device idrogeno...")
    
    device_data = {
        'device_id': 'StazioneTestElettrica_H2_700bar_01',
        'fuel_type': 'hydrogen',
        'dispensing_pressure': 700,
        'flow_rate': 1.5,
        'connector_type': 'h70',
        'purity_level': 99.97
    }
    
    response = session.post(
        f"{BASE_URL}/auth/station/add_device",
        json=device_data,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"✅ Device idrogeno aggiunto: {data.get('device_identifier')}")
            return True
        else:
            print(f"❌ Errore aggiunta device: {data.get('error')}")
            return False
    else:
        print(f"❌ Errore HTTP: {response.status_code}")
        print(response.text)
        return False

def test_device_list(session):
    """Testa la lista dei device"""
    print("📋 Test lista device...")
    
    # Assumiamo che la stazione abbia ID 7 (dalla registrazione test)
    response = session.get(f"{BASE_URL}/auth/api/station/7/devices")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            devices = data.get('devices', [])
            print(f"✅ Trovati {len(devices)} device:")
            for device in devices:
                print(f"  - {device['identifier']} ({device['fuel_type']})")
            return True
        else:
            print(f"❌ Errore API: {data.get('error')}")
            return False
    else:
        print(f"❌ Errore HTTP: {response.status_code}")
        return False

def main():
    print("=== TEST AGGIUNTA DEVICE GUIDATA ===")
    
    # Step 1: Login
    session = login_as_station_manager()
    if not session:
        print("❌ Impossibile continuare senza login")
        return
    
    # Step 2: Test dashboard
    dashboard_ok = test_dashboard_access(session)
    
    # Step 3: Test aggiunta device elettrico
    electric_ok = test_add_electric_device(session)
    
    # Step 4: Test aggiunta device idrogeno (se stazione supporta idrogeno)
    hydrogen_ok = test_add_hydrogen_device(session)
    
    # Step 5: Test lista device
    list_ok = test_device_list(session)
    
    # Risultati finali
    print(f"\n=== RISULTATI ===")
    print(f"Dashboard: {'✅' if dashboard_ok else '❌'}")
    print(f"Device elettrico: {'✅' if electric_ok else '❌'}")
    print(f"Device idrogeno: {'✅' if hydrogen_ok else '❌'}")
    print(f"Lista device: {'✅' if list_ok else '❌'}")
    
    if all([dashboard_ok, electric_ok, hydrogen_ok, list_ok]):
        print("\n🎉 TUTTI I TEST SONO PASSATI!")
    else:
        print("\n⚠️ Alcuni test hanno fallito")

if __name__ == "__main__":
    main()