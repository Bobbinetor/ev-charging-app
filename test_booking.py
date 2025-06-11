from flask import Flask, jsonify, request
import requests
import json
import sys

def test_booking_endpoint():
    """
    Test script per verificare il funzionamento dell'endpoint di prenotazione
    """
    # URL dell'endpoint di prenotazione
    url = "http://localhost:5000/auth/user/book_charging"

    # Dati di prenotazione (gli stessi che invia il frontend)
    booking_data = {
        "station_id": 1,  # Assicurati che questo ID esista nel tuo database
        "time_slot": "2025-05-16 14:30",
        "duration": 30
    }

    # Headers per la richiesta
    headers = {
        "Content-Type": "application/json"
    }

    # Per fare il test con autenticazione, avvia la tua app Flask e accedi dal browser
    # Poi copia il valore del cookie di sessione dal browser (usando gli strumenti di sviluppo)
    # e sostituiscilo nella variabile session_cookie
    session_cookie = "inserisci_qui_il_tuo_cookie_di_sessione"

    # Aggiungi il cookie alla richiesta se fornito
    cookies = {}
    if session_cookie != "inserisci_qui_il_tuo_cookie_di_sessione":
        cookies["session"] = session_cookie

    try:
        # Effettua la richiesta
        response = requests.post(url, headers=headers, json=booking_data, cookies=cookies)
        
        # Stampa la risposta
        print("Codice di stato:", response.status_code)
        print("Risposta:", json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        # Verifica il risultato
        if response.status_code == 200 and response.json().get("success"):
            print("\n✅ Test riuscito! La prenotazione è stata effettuata con successo.")
        else:
            print("\n❌ Test fallito.")
            if "error" in response.json():
                print("Errore:", response.json()["error"])
                
    except requests.exceptions.RequestException as e:
        print(f"Errore di connessione: {e}")
    except json.JSONDecodeError:
        print("Errore: La risposta non è in formato JSON valido")
        print("Risposta grezza:", response.text)
    except Exception as e:
        print(f"Errore generico: {e}")

if __name__ == "__main__":
    test_booking_endpoint()