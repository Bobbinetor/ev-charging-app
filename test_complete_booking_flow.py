#!/usr/bin/env python3
"""
Test completo a 360 gradi per tutti i flussi di prenotazione
Verifica il controllo incrociato tra frontend e backend
"""

import requests
import json
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# URL base del server Flask
BASE_URL = "http://127.0.0.1:5050"

class BookingFlowTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, success, details=""):
        """Registra il risultato di un test"""
        status = "✅" if success else "❌"
        self.test_results.append({
            'name': test_name,
            'success': success,
            'details': details
        })
        print(f"{status} {test_name}{': ' + details if details else ''}")
        
    def login_as_user(self, email="mario.rossi@email.com", password="password123"):
        """Login come utente normale"""
        print("\n🔐 Login come utente normale...")
        
        try:
            # Ottieni la pagina di login
            response = self.session.get(f"{BASE_URL}/auth/login")
            soup = BeautifulSoup(response.content, 'html.parser')
            csrf_token = soup.find('input', {'name': 'csrf_token'})['value']
            
            # Login
            login_data = {
                'csrf_token': csrf_token,
                'email': email,
                'password': password,
                'remember_me': False
            }
            
            response = self.session.post(f"{BASE_URL}/auth/login", data=login_data, allow_redirects=False)
            
            if response.status_code == 302 and 'dashboard' in response.headers.get('Location', ''):
                self.log_test("Login utente", True, f"Autenticato come {email}")
                return True
            else:
                self.log_test("Login utente", False, f"Errore: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Login utente", False, f"Eccezione: {str(e)}")
            return False
    
    def test_specs_api(self):
        """Testa l'API delle specifiche disponibili"""
        print("\n🔧 Test API specifiche tecniche...")
        
        tests = [
            ("Specifiche elettriche globali", "/auth/api/specs/available?fuel_type=electric"),
            ("Specifiche idrogeno globali", "/auth/api/specs/available?fuel_type=hydrogen"),
            ("Specifiche Milano", "/auth/api/specs/available?fuel_type=electric&city=Milano"),
            ("Specifiche Roma", "/auth/api/specs/available?fuel_type=electric&city=Roma"),
            ("Specifiche Torino H2", "/auth/api/specs/available?fuel_type=hydrogen&city=Torino"),
        ]
        
        for test_name, url in tests:
            try:
                response = self.session.get(f"{BASE_URL}{url}")
                data = response.json()
                
                if response.status_code == 200 and data.get('success'):
                    # Verifica struttura della risposta
                    has_electric = 'electric_specs' in data
                    has_hydrogen = 'hydrogen_specs' in data
                    
                    fuel_type = url.split('fuel_type=')[1].split('&')[0] if 'fuel_type=' in url else 'all'
                    
                    if fuel_type == 'electric' and has_electric:
                        specs = data['electric_specs']
                        connectors_count = len(specs.get('connectors', []))
                        power_levels_count = len(specs.get('power_levels', []))
                        self.log_test(test_name, True, f"{connectors_count} connettori, {power_levels_count} livelli di potenza")
                    elif fuel_type == 'hydrogen' and has_hydrogen:
                        specs = data['hydrogen_specs']
                        pressures_count = len(specs.get('pressures', []))
                        flows_count = len(specs.get('flow_rates', []))
                        self.log_test(test_name, True, f"{pressures_count} pressioni, {flows_count} flussi")
                    else:
                        self.log_test(test_name, True, "Risposta valida")
                else:
                    self.log_test(test_name, False, f"Errore API: {data.get('error', 'Unknown')}")
                    
            except Exception as e:
                self.log_test(test_name, False, f"Eccezione: {str(e)}")
    
    def test_station_api(self):
        """Testa l'API delle stazioni con filtri"""
        print("\n🏭 Test API stazioni con filtri...")
        
        tests = [
            ("Tutte le stazioni", "/auth/api/stations"),
            ("Stazioni elettriche", "/auth/api/stations?fuel_type=electric"),
            ("Stazioni idrogeno", "/auth/api/stations?fuel_type=hydrogen"),
            ("Stazioni con CCS", "/auth/api/stations?fuel_type=electric&connector_type=ccs"),
            ("Stazioni >100kW", "/auth/api/stations?fuel_type=electric&min_power=100"),
            ("Stazioni H2 700bar", "/auth/api/stations?fuel_type=hydrogen&pressure=700"),
            ("Stazioni Milano", "/auth/api/stations?city=Milano"),
            ("Stazioni Roma con time slot", f"/auth/api/stations?city=Roma&time_slot={datetime.now().strftime('%Y-%m-%d %H:%M')}&duration=30"),
        ]
        
        for test_name, url in tests:
            try:
                response = self.session.get(f"{BASE_URL}{url}")
                data = response.json()
                
                if response.status_code == 200 and data.get('success'):
                    stations_count = len(data.get('stations', []))
                    available_count = sum(1 for s in data.get('stations', []) if s.get('available'))
                    
                    self.log_test(test_name, True, f"{stations_count} stazioni trovate, {available_count} disponibili")
                    
                    # Verifica che le stazioni corrispondano ai filtri
                    if 'fuel_type=electric' in url:
                        electric_stations = [s for s in data.get('stations', []) if 'electric' in s.get('fuel_types', [])]
                        if len(electric_stations) == stations_count:
                            self.log_test(f"{test_name} - Filtro carburante", True, "Tutte le stazioni supportano elettrico")
                        else:
                            self.log_test(f"{test_name} - Filtro carburante", False, f"Solo {len(electric_stations)}/{stations_count} supportano elettrico")
                            
                else:
                    self.log_test(test_name, False, f"Errore API: {data.get('error', 'Unknown')}")
                    
            except Exception as e:
                self.log_test(test_name, False, f"Eccezione: {str(e)}")
    
    def test_booking_flow_electric(self):
        """Testa il flusso completo di prenotazione elettrica"""
        print("\n⚡ Test flusso prenotazione elettrica...")
        
        # Trova una stazione elettrica
        try:
            response = self.session.get(f"{BASE_URL}/auth/api/stations?fuel_type=electric")
            data = response.json()
            
            if not data.get('success') or not data.get('stations'):
                self.log_test("Trova stazione elettrica", False, "Nessuna stazione elettrica trovata")
                return
                
            station = data['stations'][0]
            station_id = station['id']
            station_name = station['name']
            
            self.log_test("Trova stazione elettrica", True, f"Selezionata: {station_name}")
            
            # Test verifica disponibilità
            future_time = (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')
            
            booking_data = {
                'station_id': station_id,
                'time_slot': future_time,
                'duration': 30,
                'check_only': True,
                'fuel_type': 'electric',
                'connector_type': 'ccs',
                'min_power': 50
            }
            
            response = self.session.post(
                f"{BASE_URL}/auth/user/book_charging",
                json=booking_data,
                headers={'Content-Type': 'application/json'}
            )
            
            check_data = response.json()
            if check_data.get('success'):
                self.log_test("Verifica disponibilità elettrica", True, f"Dispositivi disponibili: {check_data.get('available_devices', 0)}")
                
                # Procedi con prenotazione effettiva
                del booking_data['check_only']
                
                response = self.session.post(
                    f"{BASE_URL}/auth/user/book_charging",
                    json=booking_data,
                    headers={'Content-Type': 'application/json'}
                )
                
                booking_result = response.json()
                if booking_result.get('success'):
                    booking_id = booking_result.get('booking_id')
                    device_id = booking_result.get('details', {}).get('device_id', 'Unknown')
                    self.log_test("Prenotazione elettrica", True, f"ID: {booking_id}, Device: {device_id}")
                    return booking_id
                else:
                    self.log_test("Prenotazione elettrica", False, f"Errore: {booking_result.get('error')}")
            else:
                self.log_test("Verifica disponibilità elettrica", False, f"Errore: {check_data.get('error')}")
                
        except Exception as e:
            self.log_test("Flusso prenotazione elettrica", False, f"Eccezione: {str(e)}")
        
        return None
    
    def test_booking_flow_hydrogen(self):
        """Testa il flusso completo di prenotazione idrogeno"""
        print("\n🔋 Test flusso prenotazione idrogeno...")
        
        # Trova una stazione idrogeno
        try:
            response = self.session.get(f"{BASE_URL}/auth/api/stations?fuel_type=hydrogen")
            data = response.json()
            
            if not data.get('success') or not data.get('stations'):
                self.log_test("Trova stazione idrogeno", False, "Nessuna stazione idrogeno trovata")
                return
                
            station = data['stations'][0]
            station_id = station['id']
            station_name = station['name']
            
            self.log_test("Trova stazione idrogeno", True, f"Selezionata: {station_name}")
            
            # Test verifica disponibilità
            future_time = (datetime.now() + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M')
            
            booking_data = {
                'station_id': station_id,
                'time_slot': future_time,
                'duration': 5,
                'check_only': True,
                'fuel_type': 'hydrogen',
                'connector_type': '700',
                'min_flow': 1.5
            }
            
            response = self.session.post(
                f"{BASE_URL}/auth/user/book_charging",
                json=booking_data,
                headers={'Content-Type': 'application/json'}
            )
            
            check_data = response.json()
            if check_data.get('success'):
                self.log_test("Verifica disponibilità idrogeno", True, f"Dispositivi disponibili: {check_data.get('available_devices', 0)}")
                
                # Procedi con prenotazione effettiva
                del booking_data['check_only']
                
                response = self.session.post(
                    f"{BASE_URL}/auth/user/book_charging",
                    json=booking_data,
                    headers={'Content-Type': 'application/json'}
                )
                
                booking_result = response.json()
                if booking_result.get('success'):
                    booking_id = booking_result.get('booking_id')
                    device_id = booking_result.get('details', {}).get('device_id', 'Unknown')
                    self.log_test("Prenotazione idrogeno", True, f"ID: {booking_id}, Device: {device_id}")
                    return booking_id
                else:
                    self.log_test("Prenotazione idrogeno", False, f"Errore: {booking_result.get('error')}")
            else:
                self.log_test("Verifica disponibilità idrogeno", False, f"Errore: {check_data.get('error')}")
                
        except Exception as e:
            self.log_test("Flusso prenotazione idrogeno", False, f"Eccezione: {str(e)}")
        
        return None
    
    def test_booking_validation(self):
        """Testa la validazione delle prenotazioni"""
        print("\n🚫 Test validazione prenotazioni...")
        
        # Test con dati invalidi
        invalid_tests = [
            ("Stazione inesistente", {"station_id": 9999, "time_slot": "2025-12-25 10:00", "duration": 30, "fuel_type": "electric"}),
            ("Formato data invalido", {"station_id": 1, "time_slot": "invalid-date", "duration": 30, "fuel_type": "electric"}),
            ("Data nel passato", {"station_id": 1, "time_slot": "2020-01-01 10:00", "duration": 30, "fuel_type": "electric"}),
            ("Durata negativa", {"station_id": 1, "time_slot": "2025-12-25 10:00", "duration": -10, "fuel_type": "electric"}),
            ("Tipo carburante non supportato", {"station_id": 1, "time_slot": "2025-12-25 10:00", "duration": 30, "fuel_type": "nuclear"}),
        ]
        
        for test_name, booking_data in invalid_tests:
            try:
                response = self.session.post(
                    f"{BASE_URL}/auth/user/book_charging",
                    json=booking_data,
                    headers={'Content-Type': 'application/json'}
                )
                
                result = response.json()
                if not result.get('success'):
                    self.log_test(f"Validazione: {test_name}", True, "Correttamente rifiutata")
                else:
                    self.log_test(f"Validazione: {test_name}", False, "Doveva essere rifiutata ma è stata accettata")
                    
            except Exception as e:
                self.log_test(f"Validazione: {test_name}", False, f"Eccezione: {str(e)}")
    
    def test_cross_validation(self):
        """Testa il controllo incrociato frontend-backend"""
        print("\n🔄 Test controllo incrociato frontend-backend...")
        
        # Test: cercare di prenotare device elettrico con parametri idrogeno
        try:
            response = self.session.get(f"{BASE_URL}/auth/api/stations?fuel_type=electric")
            data = response.json()
            
            if data.get('success') and data.get('stations'):
                station_id = data['stations'][0]['id']
                
                # Tentativo di prenotazione con parametri inconsistenti
                booking_data = {
                    'station_id': station_id,
                    'time_slot': (datetime.now() + timedelta(hours=4)).strftime('%Y-%m-%d %H:%M'),
                    'duration': 30,
                    'fuel_type': 'electric',  # Elettrico
                    'connector_type': 'h70',  # Ma connettore idrogeno!
                    'min_flow': 2.0           # E parametro idrogeno!
                }
                
                response = self.session.post(
                    f"{BASE_URL}/auth/user/book_charging",
                    json=booking_data,
                    headers={'Content-Type': 'application/json'}
                )
                
                result = response.json()
                if not result.get('success'):
                    self.log_test("Controllo incrociato parametri", True, "Parametri inconsistenti correttamente rifiutati")
                else:
                    self.log_test("Controllo incrociato parametri", False, "Parametri inconsistenti accettati erroneamente")
                    
        except Exception as e:
            self.log_test("Controllo incrociato parametri", False, f"Eccezione: {str(e)}")
    
    def test_user_bookings(self):
        """Testa il recupero delle prenotazioni utente"""
        print("\n📋 Test recupero prenotazioni utente...")
        
        try:
            response = self.session.get(f"{BASE_URL}/auth/user/bookings")
            data = response.json()
            
            if data.get('success'):
                bookings_count = len(data.get('bookings', []))
                self.log_test("Recupero prenotazioni", True, f"{bookings_count} prenotazioni trovate")
                
                # Verifica struttura dati prenotazioni
                for booking in data.get('bookings', [])[:3]:  # Testa solo le prime 3
                    required_fields = ['id', 'start_time', 'station_name', 'device_id']
                    missing_fields = [field for field in required_fields if field not in booking]
                    
                    if not missing_fields:
                        self.log_test(f"Struttura prenotazione {booking['id']}", True, "Tutti i campi richiesti presenti")
                    else:
                        self.log_test(f"Struttura prenotazione {booking['id']}", False, f"Campi mancanti: {missing_fields}")
            else:
                self.log_test("Recupero prenotazioni", False, f"Errore API: {data.get('error')}")
                
        except Exception as e:
            self.log_test("Recupero prenotazioni", False, f"Eccezione: {str(e)}")
    
    def print_summary(self):
        """Stampa il riepilogo dei test"""
        print("\n" + "="*80)
        print("📊 RIEPILOGO TEST COMPLETO FLUSSI DI PRENOTAZIONE")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results if test['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📈 STATISTICHE:")
        print(f"   Test totali: {total_tests}")
        print(f"   ✅ Passati: {passed_tests}")
        print(f"   ❌ Falliti: {failed_tests}")
        print(f"   📊 Percentuale successo: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ TEST FALLITI:")
            for test in self.test_results:
                if not test['success']:
                    print(f"   • {test['name']}: {test['details']}")
        
        print(f"\n✅ TEST PASSATI:")
        for test in self.test_results:
            if test['success']:
                print(f"   • {test['name']}")
        
        if passed_tests == total_tests:
            print("\n🎉 TUTTI I TEST SONO PASSATI! Sistema di prenotazione completamente funzionale.")
        else:
            print(f"\n⚠️  {failed_tests} test da correggere per avere un sistema perfetto.")
        
        print("="*80)
    
    def run_all_tests(self):
        """Esegue tutti i test"""
        print("🚀 INIZIO TEST COMPLETO FLUSSI DI PRENOTAZIONE")
        print("="*80)
        
        # Login
        if not self.login_as_user():
            print("❌ Impossibile procedere senza login")
            return
        
        # Test API
        self.test_specs_api()
        self.test_station_api()
        
        # Test flussi prenotazione
        self.test_booking_flow_electric()
        self.test_booking_flow_hydrogen()
        
        # Test validazione
        self.test_booking_validation()
        self.test_cross_validation()
        
        # Test gestione prenotazioni
        self.test_user_bookings()
        
        # Riepilogo
        self.print_summary()

def main():
    tester = BookingFlowTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()