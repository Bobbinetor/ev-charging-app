"""
Servizio per la gestione del digital twin dei dispositivi di mobilità sostenibile.
Gestisce la sincronizzazione dei dati telemetrici in tempo reale con Orion-LD.
"""

import requests
import json
import random
import time
from datetime import datetime, timezone
from app import db
from app.models import ChargingPoint, Station, FuelType, ConnectorType

# Configurazione Orion-LD
ORION_ENDPOINT = "http://localhost:1026/v2/entities"
FIWARE_SERVICE = "ev_charging"
FIWARE_SERVICEPATH = "/"

ORION_HEADERS = {
    'Content-Type': 'application/json',
    'Fiware-Service': FIWARE_SERVICE,
    'Fiware-ServicePath': FIWARE_SERVICEPATH
}

def create_electric_device_entity(charging_point):
    """
    Crea un'entità digital twin per un dispositivo elettrico in Orion-LD
    """
    device_id = f"urn:ngsi-ld:ChargingDevice:{charging_point.id}"
    
    entity = {
        "id": device_id,
        "type": "ChargingDevice",
        "identifier": {
            "type": "Text",
            "value": charging_point.identifier
        },
        "fuelType": {
            "type": "Text",
            "value": charging_point.fuel_type.value
        },
        "connectorType": {
            "type": "Text",
            "value": charging_point.connector_type.value if charging_point.connector_type else "unknown"
        },
        "powerType": {
            "type": "Text",
            "value": charging_point.power_type or "AC"
        },
        "powerLevel": {
            "type": "Number",
            "value": charging_point.power_level or 0
        },
        "voltage": {
            "type": "Number",
            "value": charging_point.voltage or 0
        },
        "current": {
            "type": "Number",
            "value": charging_point.current or 0
        },
        "status": {
            "type": "Text",
            "value": charging_point.status
        },
        "refStation": {
            "type": "Relationship",
            "value": f"urn:ngsi-ld:ChargingStation:{charging_point.station_id}"
        },
        # Dati telemetrici in tempo reale
        "currentPower": {
            "type": "Number",
            "value": 0,
            "metadata": {
                "timestamp": {
                    "type": "DateTime",
                    "value": datetime.now(timezone.utc).isoformat()
                }
            }
        },
        "currentVoltage": {
            "type": "Number",
            "value": charging_point.voltage or 0,
            "metadata": {
                "timestamp": {
                    "type": "DateTime", 
                    "value": datetime.now(timezone.utc).isoformat()
                }
            }
        },
        "currentCurrent": {
            "type": "Number",
            "value": 0,
            "metadata": {
                "timestamp": {
                    "type": "DateTime",
                    "value": datetime.now(timezone.utc).isoformat()
                }
            }
        },
        "temperature": {
            "type": "Number",
            "value": 25.0,
            "metadata": {
                "timestamp": {
                    "type": "DateTime",
                    "value": datetime.now(timezone.utc).isoformat()
                }
            }
        }
    }
    
    return entity

def create_hydrogen_device_entity(charging_point):
    """
    Crea un'entità digital twin per un distributore di idrogeno in Orion-LD
    """
    device_id = f"urn:ngsi-ld:HydrogenDispenser:{charging_point.id}"
    
    entity = {
        "id": device_id,
        "type": "HydrogenDispenser",
        "identifier": {
            "type": "Text",
            "value": charging_point.identifier
        },
        "fuelType": {
            "type": "Text",
            "value": charging_point.fuel_type.value
        },
        "connectorType": {
            "type": "Text",
            "value": charging_point.connector_type.value if charging_point.connector_type else "H70"
        },
        "dispensingPressure": {
            "type": "Number",
            "value": charging_point.dispensing_pressure or 700
        },
        "flowRate": {
            "type": "Number",
            "value": charging_point.flow_rate or 1.5
        },
        "temperatureRangeMin": {
            "type": "Number",
            "value": charging_point.temperature_range_min or -40
        },
        "temperatureRangeMax": {
            "type": "Number",
            "value": charging_point.temperature_range_max or 85
        },
        "purityLevel": {
            "type": "Number",
            "value": charging_point.purity_level or 99.97
        },
        "status": {
            "type": "Text",
            "value": charging_point.status
        },
        "refStation": {
            "type": "Relationship",
            "value": f"urn:ngsi-ld:HydrogenStation:{charging_point.station_id}"
        },
        # Dati telemetrici in tempo reale
        "currentPressure": {
            "type": "Number",
            "value": charging_point.dispensing_pressure or 700,
            "metadata": {
                "timestamp": {
                    "type": "DateTime",
                    "value": datetime.now(timezone.utc).isoformat()
                }
            }
        },
        "currentTemperature": {
            "type": "Number",
            "value": -33.0,
            "metadata": {
                "timestamp": {
                    "type": "DateTime",
                    "value": datetime.now(timezone.utc).isoformat()
                }
            }
        },
        "currentFlow": {
            "type": "Number",
            "value": 0,
            "metadata": {
                "timestamp": {
                    "type": "DateTime",
                    "value": datetime.now(timezone.utc).isoformat()
                }
            }
        },
        "hydrogenPurity": {
            "type": "Number",
            "value": 99.97,
            "metadata": {
                "timestamp": {
                    "type": "DateTime",
                    "value": datetime.now(timezone.utc).isoformat()
                }
            }
        },
        "tankLevel": {
            "type": "Number",
            "value": 85.0,
            "metadata": {
                "timestamp": {
                    "type": "DateTime",
                    "value": datetime.now(timezone.utc).isoformat()
                }
            }
        }
    }
    
    return entity

def create_station_entity(station):
    """
    Crea un'entità stazione in Orion-LD
    """
    if station.station_type == 'hydrogen' or 'hydrogen' in (station.fuel_types or []):
        station_id = f"urn:ngsi-ld:HydrogenStation:{station.id}"
        entity_type = "HydrogenStation"
    else:
        station_id = f"urn:ngsi-ld:ChargingStation:{station.id}"
        entity_type = "ChargingStation"
    
    entity = {
        "id": station_id,
        "type": entity_type,
        "name": {
            "type": "Text",
            "value": station.name
        },
        "company": {
            "type": "Text",
            "value": station.company or "Unknown"
        },
        "address": {
            "type": "Text",
            "value": station.address or "Unknown"
        },
        "location": {
            "type": "geo:json",
            "value": {
                "type": "Point",
                "coordinates": [station.longitude or 0, station.latitude or 0]
            }
        },
        "fuelTypes": {
            "type": "StructuredValue",
            "value": station.fuel_types or ["electric"]
        },
        "stationType": {
            "type": "Text",
            "value": station.station_type or "electric"
        }
    }
    
    # Campi specifici per stazioni elettriche
    if station.station_type == 'electric' or 'electric' in (station.fuel_types or []):
        entity.update({
            "electricPower": {
                "type": "Number",
                "value": station.electric_power or 50
            },
            "connectorTypes": {
                "type": "StructuredValue",
                "value": station.connector_types or ["type2"]
            }
        })
    
    # Campi specifici per stazioni idrogeno
    if station.station_type == 'hydrogen' or 'hydrogen' in (station.fuel_types or []):
        entity.update({
            "hydrogenStorageCapacity": {
                "type": "Number",
                "value": station.hydrogen_storage_capacity or 1000
            },
            "hydrogenPurity": {
                "type": "Number",
                "value": station.hydrogen_purity or 99.97
            },
            "maxDispensingPressure": {
                "type": "Number",
                "value": station.max_dispensing_pressure or 700
            }
        })
    
    return entity

def create_device_digital_twin(charging_point_id):
    """
    Crea il digital twin completo di un dispositivo in Orion-LD
    """
    try:
        charging_point = ChargingPoint.query.get(charging_point_id)
        if not charging_point:
            return False
        
        # Crea entità basata sul tipo di carburante
        if charging_point.fuel_type == FuelType.HYDROGEN:
            entity = create_hydrogen_device_entity(charging_point)
        else:
            entity = create_electric_device_entity(charging_point)
        
        # Invia a Orion-LD
        response = requests.post(
            ORION_ENDPOINT,
            headers=ORION_HEADERS,
            json=entity
        )
        
        if response.status_code in [201, 422]:  # 422 = già esiste
            print(f"Digital twin creato per dispositivo {charging_point.identifier}")
            return True
        else:
            print(f"Errore creazione digital twin: {response.text}")
            return False
            
    except Exception as e:
        print(f"Errore nella creazione del digital twin: {str(e)}")
        return False

def create_station_digital_twin(station_id):
    """
    Crea il digital twin di una stazione in Orion-LD
    """
    try:
        station = Station.query.get(station_id)
        if not station:
            return False
        
        entity = create_station_entity(station)
        
        response = requests.post(
            ORION_ENDPOINT,
            headers=ORION_HEADERS,
            json=entity
        )
        
        if response.status_code in [201, 422]:
            print(f"Digital twin stazione creato per {station.name}")
            return True
        else:
            print(f"Errore creazione digital twin stazione: {response.text}")
            return False
            
    except Exception as e:
        print(f"Errore nella creazione del digital twin stazione: {str(e)}")
        return False

def update_device_telemetry(charging_point_id, telemetry_data):
    """
    Aggiorna i dati telemetrici di un dispositivo
    """
    try:
        charging_point = ChargingPoint.query.get(charging_point_id)
        if not charging_point:
            return False
        
        # Aggiorna database locale
        charging_point.current_temperature = telemetry_data.get('temperature')
        charging_point.current_pressure = telemetry_data.get('pressure')
        charging_point.current_flow = telemetry_data.get('flow')
        charging_point.last_telemetry_update = datetime.now(timezone.utc)
        db.session.commit()
        
        # Determina ID entità
        if charging_point.fuel_type == FuelType.HYDROGEN:
            device_id = f"urn:ngsi-ld:HydrogenDispenser:{charging_point_id}"
        else:
            device_id = f"urn:ngsi-ld:ChargingDevice:{charging_point_id}"
        
        # Prepara aggiornamento per Orion-LD
        update_data = {}
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if 'temperature' in telemetry_data:
            update_data['currentTemperature'] = {
                "type": "Number",
                "value": telemetry_data['temperature'],
                "metadata": {"timestamp": {"type": "DateTime", "value": timestamp}}
            }
        
        if 'pressure' in telemetry_data:
            update_data['currentPressure'] = {
                "type": "Number",
                "value": telemetry_data['pressure'],
                "metadata": {"timestamp": {"type": "DateTime", "value": timestamp}}
            }
        
        if 'flow' in telemetry_data:
            update_data['currentFlow'] = {
                "type": "Number",
                "value": telemetry_data['flow'],
                "metadata": {"timestamp": {"type": "DateTime", "value": timestamp}}
            }
        
        # Aggiorna Orion-LD
        update_url = f"{ORION_ENDPOINT}/{device_id}/attrs"
        response = requests.patch(
            update_url,
            headers=ORION_HEADERS,
            json=update_data
        )
        
        return response.status_code == 204
        
    except Exception as e:
        print(f"Errore aggiornamento telemetria: {str(e)}")
        db.session.rollback()
        return False

def simulate_telemetry_data(fuel_type):
    """
    Simula dati telemetrici realistici basati sul tipo di carburante
    """
    if fuel_type == FuelType.HYDROGEN:
        return {
            'temperature': round(random.uniform(-40, -30), 2),  # Temperatura criogenica
            'pressure': random.randint(680, 720),  # Pressione variabile intorno a 700 bar
            'flow': round(random.uniform(0, 2.5), 2),  # Flusso kg/min
            'purity': round(random.uniform(99.95, 99.99), 2),  # Purezza H2
            'tank_level': round(random.uniform(20, 95), 1)  # Livello serbatoio %
        }
    else:  # ELECTRIC
        return {
            'temperature': round(random.uniform(20, 45), 2),  # Temperatura operativa
            'power': round(random.uniform(0, 350), 2),  # Potenza kW
            'voltage': round(random.uniform(380, 420), 1),  # Tensione V
            'current': round(random.uniform(0, 500), 1),  # Corrente A
            'energy': round(random.uniform(0, 100), 2)  # Energia erogata kWh
        }