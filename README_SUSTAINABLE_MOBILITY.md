# 🌿 Sustainable Mobility Platform - Estensione Idrogeno

## Panoramica delle Modifiche

Il progetto è stato esteso da una piattaforma dedicata esclusivamente alla **mobilità elettrica** a una **piattaforma di mobilità sostenibile** completa che supporta sia veicoli elettrici che a idrogeno.

## 🔧 Modifiche Implementate

### 1. **Modelli Database Estesi**

#### Nuovi Enum e Tipi
```python
class FuelType(enum.Enum):
    ELECTRIC = "electric"
    HYDROGEN = "hydrogen" 
    HYBRID = "hybrid"

class ConnectorType(enum.Enum):
    # Elettrico
    TYPE2 = "type2"
    CCS = "ccs"
    CHADEMO = "chademo"
    # Idrogeno
    H70 = "h70"  # 700 bar
    H35 = "h35"  # 350 bar
```

#### Station - Supporto Multi-Carburante
- `fuel_types`: JSON array con tipi supportati
- `station_type`: "electric", "hydrogen", "hybrid"
- `hydrogen_storage_capacity`: Capacità stoccaggio H2 (kg)
- `hydrogen_purity`: Purezza idrogeno (%)
- `max_dispensing_pressure`: Pressione massima (bar)

#### ChargingPoint - Dispositivi Universali
- `fuel_type`: Tipo carburante del dispositivo
- `connector_type`: Tipo connettore (elettrico/idrogeno)
- Campi elettrici: `power_level`, `voltage`, `current`
- Campi idrogeno: `dispensing_pressure`, `flow_rate`, `purity_level`
- **Digital Twin**: `current_temperature`, `current_pressure`, `current_flow`

#### ChargingSession - Sessioni Multi-Carburante
- `fuel_type`: Tipo carburante della sessione
- Elettrico: `energy_consumed`, `peak_power`, `average_power`
- Idrogeno: `hydrogen_dispensed`, `dispensing_pressure`, `dispensing_temperature`

### 2. **Digital Twin e Integrazione FIWARE**

#### Servizio Digital Twin (`digital_twin_service.py`)
- **Entità Orion-LD** separate per elettrico e idrogeno:
  - `urn:ngsi-ld:ChargingDevice:{id}` (elettrico)
  - `urn:ngsi-ld:HydrogenDispenser:{id}` (idrogeno)
  - `urn:ngsi-ld:ChargingStation:{id}` / `urn:ngsi-ld:HydrogenStation:{id}`

#### Telemetria in Tempo Reale
- **Elettrico**: potenza, tensione, corrente, temperatura
- **Idrogeno**: pressione, temperatura criogenica, flusso, purezza, livello serbatoio

#### Simulazione IoT
- Dati telemetrici realistici basati sul tipo di carburante
- Aggiornamento automatico in Orion-LD con timestamp

### 3. **Script Simulatore Completo**

#### `create_devices_simulator.py`
- **Creazione automatica** di stazioni elettriche, idrogeno e ibride
- **Configurazione dispositivi** con specifiche tecniche realistiche
- **Simulazione telemetrica** in tempo reale con threading
- **Digital twin completo** per ogni dispositivo

#### Funzionalità Simulator
```bash
python create_devices_simulator.py
```
- Crea 5 stazioni demo (Roma, Milano, Torino, Napoli, Bologna)
- Genera dispositivi con specifiche realistiche
- Avvia simulazione telemetrica opzionale
- Sincronizzazione con Orion-LD

### 4. **Homepage Rinnovata**

#### Nuovo Branding
- **Titolo**: "La mobilità sostenibile del futuro"
- **Sottotitolo**: "Rete integrata per veicoli elettrici e a idrogeno"
- **Brand**: "Sustainable Mobility Hub"

#### Nuove Feature Cards
- **Multi-carburante**: Supporto elettrico + idrogeno
- **Tecnologia H2**: Distributori ad alta pressione
- **Digital Twin**: Monitoraggio IoT FIWARE
- **Layout responsivo**: Grid CSS per 6 card

### 5. **Form Registrazione Estesi**

#### `RegistrationStationForm` Aggiornato
- **Tipo stazione**: Elettrica, Idrogeno, Ibrida
- **Tipi carburante**: Selezione multipla
- **Campi idrogeno**: Capacità stoccaggio, purezza, pressione
- **Validazione intelligente**: Campi condizionali

## 🏗️ Architettura Tecnica

### Database Migration
```sql
-- Nuovi campi Station
ALTER TABLE station ADD COLUMN fuel_types JSON;
ALTER TABLE station ADD COLUMN station_type VARCHAR(32);
ALTER TABLE station ADD COLUMN hydrogen_storage_capacity FLOAT;

-- Estensione ChargingPoint
ALTER TABLE charging_point ADD COLUMN fuel_type ENUM('ELECTRIC', 'HYDROGEN', 'HYBRID');
ALTER TABLE charging_point ADD COLUMN dispensing_pressure INTEGER;
ALTER TABLE charging_point ADD COLUMN current_temperature FLOAT;
```

### Orion-LD Entities
```json
{
  "id": "urn:ngsi-ld:HydrogenDispenser:1",
  "type": "HydrogenDispenser",
  "currentPressure": {"type": "Number", "value": 700},
  "currentTemperature": {"type": "Number", "value": -33.0},
  "hydrogenPurity": {"type": "Number", "value": 99.97},
  "tankLevel": {"type": "Number", "value": 85.0}
}
```

### Service Layer Esteso
- **`booking_service.py`**: Supporto prenotazioni multi-carburante
- **`digital_twin_service.py`**: Gestione completa digital twin
- Sincronizzazione bidirezionale PostgreSQL ↔ Orion-LD

## 📊 Dispositivi Supportati

### Elettrici
- **AC**: 7.4kW, 11kW, 22kW (Type 2)
- **DC Fast**: 50kW, 150kW, 350kW (CCS, CHAdeMO)
- **Tensioni**: 230V (AC), 400V/800V (DC)

### Idrogeno
- **Pressioni**: 350 bar (H35), 700 bar (H70)
- **Flusso**: 1.0-2.5 kg/min
- **Temperatura**: -40°C a 85°C
- **Purezza**: 99.95-99.99%

## 🚀 Come Utilizzare

### 1. Applicare Migration
```bash
# Aggiungere la migration al database
flask db upgrade
```

### 2. Avviare Infrastruttura
```bash
# Avviare stack FIWARE
docker-compose up -d

# Verificare Orion-LD
curl http://localhost:1026/version
```

### 3. Creare Infrastruttura Demo
```bash
# Eseguire simulator
python create_devices_simulator.py

# Avviare simulazione telemetrica
# Scegliere 'y' quando richiesto
```

### 4. Monitoraggio Digital Twin
```bash
# Consultare entità in Orion-LD
curl -H "Fiware-Service: sustainable_mobility" \
     http://localhost:1026/v2/entities?type=HydrogenDispenser

curl -H "Fiware-Service: sustainable_mobility" \
     http://localhost:1026/v2/entities?type=ChargingDevice
```

## 🌍 Impatto Ambientale

### Benefici della Piattaforma Ibrida
- **Decarbonizzazione completa**: Elettrico per auto private, H2 per mezzi pesanti
- **Interoperabilità**: Unica piattaforma per tutti i veicoli sostenibili
- **Ottimizzazione rete**: Gestione intelligente della domanda energetica
- **Scalabilità**: Supporto per future tecnologie (biocarburanti, e-fuels)

### Casi d'Uso
1. **Trasporto urbano**: Auto elettriche con ricarica capillare
2. **Logistica pesante**: Camion a idrogeno per lunghe percorrenze
3. **Trasporto pubblico**: Bus e treni ibridi elettrico/idrogeno
4. **Porti e aeroporti**: Infrastrutture multimodali sostenibili

## 📈 Roadmap Futura

### Prossimi Sviluppi
- [ ] **Integrazione V2G**: Vehicle-to-Grid per auto elettriche
- [ ] **Idrogeno verde**: Tracking della fonte di produzione H2
- [ ] **Predictive Analytics**: ML per ottimizzazione disponibilità
- [ ] **Blockchain**: Certificazione sostenibilità e carbon credits
- [ ] **AR/VR**: Interfacce immersive per operatori

### Espansioni Tecnologiche
- [ ] **Ammoniaca**: Supporto per carburanti alternativi
- [ ] **Batterie stazionarie**: Energy storage per stabilizzazione rete
- [ ] **Microgrids**: Gestione locale energia rinnovabile
- [ ] **IoT Edge**: Elaborazione dati in tempo reale sui dispositivi

---

**🔗 La piattaforma è ora pronta per supportare la transizione completa verso la mobilità sostenibile!**