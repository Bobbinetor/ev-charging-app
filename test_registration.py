#!/usr/bin/env python3

import requests
import json
from bs4 import BeautifulSoup

# URL base del server Flask
BASE_URL = "http://127.0.0.1:5050"

def test_station_registration():
    """Test completo della registrazione di una stazione elettrica"""
    
    # 1. Ottieni la pagina di registrazione per estrarre il token CSRF
    print("1. Caricamento pagina di registrazione...")
    response = requests.get(f"{BASE_URL}/auth/register/station")
    if response.status_code != 200:
        print(f"Errore nel caricamento della pagina: {response.status_code}")
        return False
    
    # Estrai il token CSRF
    soup = BeautifulSoup(response.content, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
    print(f"Token CSRF ottenuto: {csrf_token}")
    
    # 2. Prepara i dati di registrazione per una stazione elettrica
    form_data = {
        'csrf_token': csrf_token,
        'station_name': 'Stazione Test Elettrica',
        'company': 'Test Company SRL',
        'vat_number': '12345678901',
        'address': 'Via Test 123, Milano',
        'latitude': '45.4642',
        'longitude': '9.1900',
        'email': 'test.station@example.com',
        'phone': '+390212345678',
        'station_type': 'electric',
        'fuel_types': ['electric'],
        'electric_power': '50',
        'connector_types': ['type2', 'ccs'],
        'password': 'test12345',
        'password2': 'test12345',
        'accept_terms': 'y'
    }
    
    print("2. Invio dati di registrazione...")
    print(f"Dati: {json.dumps(form_data, indent=2)}")
    
    # 3. Invia la registrazione
    cookies = response.cookies
    response = requests.post(
        f"{BASE_URL}/auth/register/station",
        data=form_data,
        cookies=cookies,
        allow_redirects=False
    )
    
    print(f"Risposta: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 302:
        print("✅ Registrazione completata con successo! Redirect verso login.")
        print(f"Location: {response.headers.get('Location')}")
        return True
    else:
        print(f"❌ Errore nella registrazione:")
        print(response.text)
        return False

def test_hybrid_station_registration():
    """Test completo della registrazione di una stazione ibrida"""
    
    # 1. Ottieni la pagina di registrazione
    print("\n=== TEST STAZIONE IBRIDA ===")
    print("1. Caricamento pagina di registrazione...")
    response = requests.get(f"{BASE_URL}/auth/register/station")
    if response.status_code != 200:
        print(f"Errore nel caricamento della pagina: {response.status_code}")
        return False
    
    # Estrai il token CSRF
    soup = BeautifulSoup(response.content, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
    
    # 2. Dati per stazione ibrida
    form_data = {
        'csrf_token': csrf_token,
        'station_name': 'Stazione Test Ibrida',
        'company': 'Green Energy SRL',
        'vat_number': '98765432109',
        'address': 'Viale Sostenibilità 456, Roma',
        'latitude': '41.9028',
        'longitude': '12.4964',
        'email': 'hybrid.station@greentech.com',
        'phone': '+390687654321',
        'station_type': 'hybrid',
        'fuel_types': ['electric', 'hydrogen'],
        'electric_power': '150',
        'connector_types': ['type2', 'ccs', 'chademo'],
        'hydrogen_storage_capacity': '500',
        'hydrogen_purity': '99.95',
        'max_dispensing_pressure': '700',
        'password': 'hybrid12345',
        'password2': 'hybrid12345',
        'accept_terms': 'y'
    }
    
    print("2. Invio dati di registrazione ibrida...")
    
    # 3. Invia la registrazione
    cookies = response.cookies
    response = requests.post(
        f"{BASE_URL}/auth/register/station",
        data=form_data,
        cookies=cookies,
        allow_redirects=False
    )
    
    print(f"Risposta: {response.status_code}")
    
    if response.status_code == 302:
        print("✅ Registrazione stazione ibrida completata con successo!")
        return True
    else:
        print(f"❌ Errore nella registrazione ibrida:")
        print(response.text)
        return False

def check_orion_entities():
    """Verifica le entità create in Orion-LD"""
    print("\n=== VERIFICA ENTITÀ ORION-LD ===")
    
    orion_url = "http://localhost:1026/v2/entities"
    headers = {
        'Fiware-Service': 'sustainable_mobility',
        'Fiware-ServicePath': '/'
    }
    
    try:
        response = requests.get(orion_url, headers=headers)
        if response.status_code == 200:
            entities = response.json()
            print(f"✅ Trovate {len(entities)} entità in Orion-LD:")
            for entity in entities:
                print(f"  - {entity['id']} (tipo: {entity['type']})")
            return True
        else:
            print(f"❌ Errore nell'accesso a Orion-LD: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Errore di connessione a Orion-LD: {e}")
        return False

if __name__ == "__main__":
    print("=== TEST REGISTRAZIONE STAZIONE ===")
    
    # Test 1: Stazione elettrica
    success1 = test_station_registration()
    
    # Test 2: Stazione ibrida  
    success2 = test_hybrid_station_registration()
    
    # Test 3: Verifica entità Orion-LD
    success3 = check_orion_entities()
    
    print(f"\n=== RISULTATI ===")
    print(f"Stazione elettrica: {'✅' if success1 else '❌'}")
    print(f"Stazione ibrida: {'✅' if success2 else '❌'}")
    print(f"Entità Orion-LD: {'✅' if success3 else '❌'}")
    
    if all([success1, success2, success3]):
        print("\n🎉 TUTTI I TEST SONO PASSATI!")
    else:
        print("\n⚠️  Alcuni test hanno fallito, controllare i log sopra.")