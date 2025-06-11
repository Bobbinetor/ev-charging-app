"""
Servizio per la gestione delle prenotazioni di stazioni di mobilità sostenibile,
sia nel database locale che in Orion-LD.
Supporta sia stazioni elettriche che a idrogeno.
"""

import requests
import json
from datetime import datetime
from app import db
from app.models import Booking, Station, ChargingPoint, User, ChargingSession, FuelType

# Configurazione dell'endpoint Orion-LD
ORION_ENDPOINT = "http://localhost:1026/v2/entities"
FIWARE_SERVICE = "sustainable_mobility"
FIWARE_SERVICEPATH = "/"

# Headers per le richieste a Orion-LD
ORION_HEADERS = {
    'Content-Type': 'application/json',
    'Fiware-Service': FIWARE_SERVICE,
    'Fiware-ServicePath': FIWARE_SERVICEPATH
}

def create_booking(user_id, station_id, charging_point_id, scheduled_start, scheduled_end):
    """
    Crea una prenotazione nel database e in Orion-LD
    
    Args:
        user_id: ID dell'utente che effettua la prenotazione
        station_id: ID della stazione di ricarica
        charging_point_id: ID del punto di ricarica
        scheduled_start: Data e ora di inizio prenotazione (datetime)
        scheduled_end: Data e ora di fine prenotazione (datetime)
        
    Returns:
        L'oggetto booking creato o None in caso di errore
    """
    try:
        # Verifica che utente, stazione e punto di ricarica esistano
        user = User.query.get(user_id)
        station = Station.query.get(station_id)
        charging_point = ChargingPoint.query.get(charging_point_id)
        
        if not user or not station or not charging_point:
            print("Errore: Utente, stazione o punto di ricarica non trovati")
            return None
            
        # Verifica che il punto di ricarica appartenga alla stazione
        if charging_point.station_id != station_id:
            print("Errore: Il punto di ricarica non appartiene alla stazione specificata")
            return None
            
        # Verifica che il punto di ricarica sia disponibile per l'orario richiesto
        if not is_charging_point_available(charging_point_id, scheduled_start, scheduled_end):
            print("Errore: Il punto di ricarica non è disponibile nell'orario richiesto")
            return None
            
        # Crea la prenotazione nel database
        booking = Booking(
            user_id=user_id,
            station_id=station_id,
            charging_point_id=charging_point_id,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            status='reserved'
        )
        
        db.session.add(booking)
        db.session.commit()
        
        # Crea l'entità booking in Orion-LD
        create_booking_entity_in_orion(booking)
        
        # Aggiorna lo stato del punto di ricarica
        update_charging_point_status(charging_point_id, 'reserved')
        
        return booking
        
    except Exception as e:
        print(f"Errore nella creazione della prenotazione: {str(e)}")
        db.session.rollback()
        return None

def is_charging_point_available(charging_point_id, start_time, end_time):
    """
    Verifica se un punto di ricarica è disponibile nell'intervallo di tempo specificato.
    Controlla sia le prenotazioni (Booking) che le sessioni attive (ChargingSession).
    
    Args:
        charging_point_id: ID del punto di ricarica
        start_time: Data e ora di inizio (datetime)
        end_time: Data e ora di fine (datetime)
        
    Returns:
        True se disponibile, False altrimenti
    """
    # Prenotazioni sovrapposte
    overlapping_bookings = Booking.query.filter(
        Booking.charging_point_id == charging_point_id,
        Booking.status == 'reserved',
        Booking.scheduled_end > start_time,
        Booking.scheduled_start < end_time
    ).count()
    # Sessioni di ricarica sovrapposte
    overlapping_sessions = ChargingSession.query.filter(
        ChargingSession.charging_point_id == charging_point_id,
        ChargingSession.end_time > start_time,
        ChargingSession.start_time < end_time
    ).count()
    # Se ci sono prenotazioni o sessioni sovrapposte, il punto non è disponibile
    return (overlapping_bookings + overlapping_sessions) == 0

def update_charging_point_status(charging_point_id, status):
    """
    Aggiorna lo stato di un punto di ricarica
    
    Args:
        charging_point_id: ID del punto di ricarica
        status: Nuovo stato (available, reserved, occupied, maintenance)
    """
    try:
        # Aggiorna nel database
        charging_point = ChargingPoint.query.get(charging_point_id)
        if charging_point:
            charging_point.status = status
            db.session.commit()
            
            # Aggiorna in Orion-LD
            device_id = f"urn:ngsi-ld:ChargingDevice:{charging_point_id}"
            update_device_status_in_orion(device_id, status)
    except Exception as e:
        print(f"Errore nell'aggiornamento dello stato del punto di ricarica: {str(e)}")
        db.session.rollback()

def create_booking_entity_in_orion(booking):
    """
    Crea un'entità booking in Orion-LD
    
    Args:
        booking: L'oggetto Booking da sincronizzare con Orion-LD
    """
    try:
        # Crea l'ID dell'entità
        booking_entity_id = f"urn:ngsi-ld:Booking:{booking.id}"
        
        # Determina il tipo di stazione basato sul tipo di carburante del punto
        charging_point = ChargingPoint.query.get(booking.charging_point_id)
        if charging_point.fuel_type == FuelType.HYDROGEN:
            station_entity_id = f"urn:ngsi-ld:HydrogenStation:{booking.station_id}"
            device_entity_id = f"urn:ngsi-ld:HydrogenDispenser:{booking.charging_point_id}"
        else:
            station_entity_id = f"urn:ngsi-ld:ChargingStation:{booking.station_id}"
            device_entity_id = f"urn:ngsi-ld:ChargingDevice:{booking.charging_point_id}"
        
        user_entity_id = f"urn:ngsi-ld:User:{booking.user_id}"
        
        # Formatta le date in ISO 8601
        start_iso = booking.scheduled_start.isoformat()
        end_iso = booking.scheduled_end.isoformat()
        booking_time_iso = booking.booking_time.isoformat()
        
        # Crea l'entità booking in Orion-LD
        booking_entity = {
            "id": booking_entity_id,
            "type": "Booking",
            "bookingTime": {
                "type": "DateTime",
                "value": booking_time_iso
            },
            "scheduledStart": {
                "type": "DateTime",
                "value": start_iso
            },
            "scheduledEnd": {
                "type": "DateTime",
                "value": end_iso
            },
            "status": {
                "type": "Text",
                "value": booking.status
            },
            "refUser": {
                "type": "Relationship",
                "value": user_entity_id
            },
            "refStation": {
                "type": "Relationship",
                "value": station_entity_id
            },
            "refChargingDevice": {
                "type": "Relationship",
                "value": device_entity_id
            }
        }
        
        # Invia la richiesta a Orion-LD
        response = requests.post(
            ORION_ENDPOINT,
            headers=ORION_HEADERS,
            json=booking_entity
        )
        
        if response.status_code == 201:
            print(f"Entità booking {booking_entity_id} creata in Orion-LD")
        elif response.status_code == 422 and "Already Exists" in response.text:
            # L'entità esiste già, aggiorniamola invece di crearla
            print(f"Entità booking {booking_entity_id} già esistente, aggiornamento...")
            update_response = requests.patch(
                f"{ORION_ENDPOINT}/{booking_entity_id}/attrs",
                headers=ORION_HEADERS,
                json={
                    "status": {"type": "Text", "value": booking.status},
                    "scheduledStart": {"type": "DateTime", "value": start_iso},
                    "scheduledEnd": {"type": "DateTime", "value": end_iso}
                }
            )
            if update_response.status_code == 204:
                print(f"Entità booking {booking_entity_id} aggiornata in Orion-LD")
            else:
                print(f"Errore aggiornamento booking in Orion-LD: {update_response.text}")
        else:
            print(f"Errore creazione entità booking in Orion-LD: {response.text}")
            
    except Exception as e:
        print(f"Eccezione nella creazione dell'entità booking: {str(e)}")

def update_device_status_in_orion(device_id, status):
    """
    Aggiorna lo stato di un dispositivo in Orion-LD
    
    Args:
        device_id: ID dell'entità dispositivo in Orion-LD
        status: Nuovo stato del dispositivo
    """
    try:
        # Prepara l'aggiornamento
        status_update = {
            "status": {
                "type": "Text",
                "value": status
            }
        }
        
        # Aggiorna l'entità dispositivo
        update_url = f"{ORION_ENDPOINT}/{device_id}/attrs"
        update_response = requests.patch(
            update_url,
            headers=ORION_HEADERS,
            json=status_update
        )
        
        if update_response.status_code != 204:
            print(f"Errore aggiornamento stato dispositivo in Orion-LD: {update_response.text}")
        else:
            print(f"Stato dispositivo {device_id} aggiornato in Orion-LD")
            
    except Exception as e:
        print(f"Eccezione nell'aggiornamento dello stato del dispositivo: {str(e)}")

def get_booking(booking_id):
    """
    Recupera una prenotazione dal database
    
    Args:
        booking_id: ID della prenotazione
        
    Returns:
        L'oggetto Booking o None se non trovato
    """
    return Booking.query.get(booking_id)

def cancel_booking(booking_id):
    """
    Annulla una prenotazione
    
    Args:
        booking_id: ID della prenotazione
        
    Returns:
        True se l'operazione è riuscita, False altrimenti
    """
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return False
            
        # Aggiorna lo stato nel database
        booking.status = 'cancelled'
        db.session.commit()
        
        # Aggiorna lo stato in Orion-LD
        booking_entity_id = f"urn:ngsi-ld:Booking:{booking_id}"
        update_booking_status_in_orion(booking_entity_id, 'cancelled')
        
        # Aggiorna lo stato del punto di ricarica
        update_charging_point_status(booking.charging_point_id, 'available')
        
        return True
        
    except Exception as e:
        print(f"Errore nell'annullamento della prenotazione: {str(e)}")
        db.session.rollback()
        return False

def update_booking_status_in_orion(booking_id, status):
    """
    Aggiorna lo stato di una prenotazione in Orion-LD
    
    Args:
        booking_id: ID dell'entità booking in Orion-LD
        status: Nuovo stato della prenotazione
    """
    try:
        # Prepara l'aggiornamento
        status_update = {
            "status": {
                "type": "Text",
                "value": status
            }
        }
        
        # Aggiorna l'entità booking
        update_url = f"{ORION_ENDPOINT}/{booking_id}/attrs"
        update_response = requests.patch(
            update_url,
            headers=ORION_HEADERS,
            json=status_update
        )
        
        if update_response.status_code != 204:
            print(f"Errore aggiornamento stato prenotazione in Orion-LD: {update_response.text}")
        else:
            print(f"Stato prenotazione {booking_id} aggiornato in Orion-LD")
            
    except Exception as e:
        print(f"Eccezione nell'aggiornamento dello stato della prenotazione: {str(e)}")

def get_user_bookings(user_id):
    """
    Recupera tutte le prenotazioni di un utente
    
    Args:
        user_id: ID dell'utente
        
    Returns:
        Lista di prenotazioni
    """
    return Booking.query.filter_by(user_id=user_id).all()

def get_station_bookings(station_id):
    """
    Recupera tutte le prenotazioni di una stazione
    
    Args:
        station_id: ID della stazione
        
    Returns:
        Lista di prenotazioni
    """
    return Booking.query.filter_by(station_id=station_id).all()