# print(\"DEBUG: app.auth.routes.py is being loaded by Flask\") # Commented out debug print

from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
import requests
import json
from app.auth import bp
from app.auth.forms import (LoginForm, RegistrationUserForm, RegistrationStationForm,
                            ResetPasswordRequestForm, ResetPasswordForm)
# Ensure all necessary models are imported
from app.models import User, Station, ChargingPoint, TrustRecord, Booking, ChargingSession, FuelType, ConnectorType
from app import db, csrf # csrf should be imported here
from app.services.booking_service import create_booking, cancel_booking, get_user_bookings, get_station_bookings, is_charging_point_available
from datetime import datetime, timedelta
import logging
from sqlalchemy import or_, func # Add this import

# Configurazione dell'endpoint Orion-LD
ORION_ENDPOINT = "http://localhost:1026/v2/entities"
FIWARE_SERVICE = "ev_charging"
FIWARE_SERVICEPATH = "/"

# Headers per le richieste a Orion-LD
ORION_HEADERS = {
    'Content-Type': 'application/json',
    'Fiware-Service': FIWARE_SERVICE,
    'Fiware-ServicePath': FIWARE_SERVICEPATH,
    'Accept': 'application/json'
}

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_station_manager:
            return redirect(url_for('auth.station_dashboard'))
        return redirect(url_for('auth.user_dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Email o password non validi')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('auth.station_dashboard' if user.is_station_manager else 'auth.user_dashboard')
        return redirect(next_page)
    return render_template('auth/login.html', title='Accedi', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/register/user', methods=['GET', 'POST'])
def register_user():
    if current_user.is_authenticated:
        if current_user.is_station_manager:
            return redirect(url_for('auth.station_dashboard'))
        return redirect(url_for('auth.user_dashboard'))
    form = RegistrationUserForm()
    if form.validate_on_submit():
        user = User(
            username=f"{form.name.data}_{form.surname.data}",
            email=form.email.data,
            name=form.name.data,
            surname=form.surname.data,
            is_station_manager=False
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registrazione completata con successo!')
        return redirect(url_for('auth.login'))
    return render_template('auth/register_user.html', title='Registrazione Utente', form=form)

@bp.route('/register/station', methods=['GET', 'POST'])
def register_station():
    if current_user.is_authenticated:
        if current_user.is_station_manager:
            return redirect(url_for('auth.station_dashboard'))
        return redirect(url_for('auth.user_dashboard'))
    form = RegistrationStationForm()
    if form.validate_on_submit():
        # Prepara campi idrogeno se specificati
        hydrogen_storage = None
        hydrogen_purity = None
        max_pressure = None
        
        if 'hydrogen' in form.fuel_types.data:
            hydrogen_storage = form.hydrogen_storage_capacity.data
            hydrogen_purity = form.hydrogen_purity.data or 99.97
            max_pressure = int(form.max_dispensing_pressure.data) if form.max_dispensing_pressure.data else 700
        
        # Prepara campi elettrici se specificati
        electric_power = None
        connector_types = None
        
        if 'electric' in form.fuel_types.data:
            electric_power = form.electric_power.data
            connector_types = form.connector_types.data
        
        station = Station(
            name=form.station_name.data,
            company=form.company.data,
            vat_number=form.vat_number.data,
            address=form.address.data,
            latitude=form.latitude.data,
            longitude=form.longitude.data,
            email=form.email.data,
            phone=form.phone.data,
            # Nuovi campi multi-carburante
            station_type=form.station_type.data,
            fuel_types=form.fuel_types.data,
            # Campi elettrici
            electric_power=electric_power,
            connector_types=connector_types,
            # Campi idrogeno
            hydrogen_storage_capacity=hydrogen_storage,
            hydrogen_purity=hydrogen_purity,
            max_dispensing_pressure=max_pressure
        )
        user = User(
            username=f"{form.station_name.data}_admin",
            email=form.email.data,
            is_station_manager=True
        )
        user.set_password(form.password.data)
        db.session.add(station)
        db.session.add(user)
        db.session.commit()
        
        # Associate the station with the user
        user.station_id = station.id
        db.session.commit()
        
        # Create the station entity in Orion-LD con supporto multi-carburante
        from app.services.digital_twin_service import create_station_digital_twin
        try:
            # Usa il nuovo servizio digital twin
            success = create_station_digital_twin(station.id)
            if not success:
                print(f"Error creating station digital twin for station {station.id}")
        except Exception as e:
            print(f"Exception creating station digital twin: {str(e)}")
        
        flash('Registrazione della stazione completata con successo!')
        return redirect(url_for('auth.login'))
    return render_template('auth/register_station.html', title='Registrazione Stazione', form=form)

@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            flash('Controlla la tua email per le istruzioni sul reset della password')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', title='Reset Password', form=form)

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('La tua password è stata reimpostata.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)

@bp.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.is_station_manager:
        return redirect(url_for('auth.station_dashboard'))
    return render_template('user/dashboard.html', title='Dashboard Utente')

@bp.route('/station/dashboard')
@login_required
def station_dashboard():
    if not current_user.is_station_manager:
        return redirect(url_for('auth.user_dashboard'))
    return render_template('station/dashboard.html', title='Dashboard Stazione')

@bp.route('/terms')
def terms():
    return render_template('terms.html', title='Termini e Condizioni')

@bp.route('/privacy')
def privacy():
    return render_template('privacy.html', title='Privacy Policy')

@bp.route('/station/add_device', methods=['POST'])
@csrf.exempt
@login_required
def add_device():
    # Verifica che l'utente sia un gestore stazione
    if not current_user.is_station_manager or not current_user.station_id:
        return jsonify({'error': 'Accesso non autorizzato'}), 403

    # Ottieni i dati del dispositivo dal form
    data = request.json
    if not data:
        return jsonify({'error': 'Dati del dispositivo mancanti'}), 400
    
    device_id = data.get('device_id')
    fuel_type_str = data.get('fuel_type')
    
    if not device_id or not fuel_type_str:
        return jsonify({'error': 'ID device e tipo carburante sono obbligatori'}), 400
    
    # Verifica che il device_id non esista già
    existing_device = ChargingPoint.query.filter_by(identifier=device_id).first()
    if existing_device:
        return jsonify({'error': f'Device con ID {device_id} già esistente'}), 400
    
    # Determina il tipo di carburante
    try:
        fuel_type = FuelType.ELECTRIC if fuel_type_str == 'electric' else FuelType.HYDROGEN
    except:
        return jsonify({'error': 'Tipo carburante non valido'}), 400
    
    # Crea un nuovo device nel DB con i dati specifici per tipo
    try:
        if fuel_type == FuelType.ELECTRIC:
            # Device elettrico
            device = ChargingPoint(
                identifier=device_id,
                fuel_type=fuel_type,
                power_type=data.get('power_type'),
                power_level=data.get('power_level'),
                connector_type=ConnectorType(data.get('connector_type')) if data.get('connector_type') else None,
                voltage=data.get('voltage'),
                status='available',
                station_id=current_user.station_id
            )
        else:
            # Device idrogeno
            connector_map = {'h35': ConnectorType.H35, 'h70': ConnectorType.H70}
            device = ChargingPoint(
                identifier=device_id,
                fuel_type=fuel_type,
                dispensing_pressure=data.get('dispensing_pressure'),
                flow_rate=data.get('flow_rate'),
                connector_type=connector_map.get(data.get('connector_type')),
                purity_level=data.get('purity_level', 99.97),
                status='available',
                station_id=current_user.station_id
            )
        
        db.session.add(device)
        db.session.commit()
        
        # Crea digital twin del dispositivo in Orion-LD
        from app.services.digital_twin_service import create_device_digital_twin
        twin_success = create_device_digital_twin(device.id)
        
        if twin_success:
            return jsonify({
                'success': True, 
                'device_id': device.id,
                'device_identifier': device.identifier,
                'fuel_type': device.fuel_type.value,
                'message': f'Device {device.identifier} aggiunto con successo!'
            })
        else:
            # Device creato ma digital twin fallito - tieni comunque il device
            return jsonify({
                'success': True, 
                'device_id': device.id,
                'device_identifier': device.identifier,
                'fuel_type': device.fuel_type.value,
                'message': f'Device {device.identifier} aggiunto (digital twin non creato)'
            })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Errore nella creazione del dispositivo: {str(e)}'}), 500

@bp.route('/user/book_charging', methods=['POST'])
@csrf.exempt
@login_required
def book_charging():
    # Utilizziamo il logger di Flask invece di print per assicurarci che i log vengano registrati
    from flask import current_app
    import logging
    import traceback
    import sys
    
    # Configurazione di un logger dedicato per il debug
    debug_logger = logging.getLogger('booking_debug')
    if not debug_logger.handlers:
        # Configura il file handler solo se non è già stato configurato
        file_handler = logging.FileHandler('booking_debug.log')
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        debug_logger.addHandler(file_handler)
        
        # Aggiungi anche un handler per la console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        debug_logger.addHandler(console_handler)
        
        debug_logger.setLevel(logging.DEBUG)
        debug_logger.propagate = False  # Per evitare duplicati nei log
    
    # Log all'inizio dell'endpoint
    debug_logger.debug("============= INIZIO ENDPOINT BOOK_CHARGING =============")
    debug_logger.debug(f"User: {current_user.id} - {current_user.email}")
    
    # Solo gli utenti normali (non gestori di stazioni) possono effettuare prenotazioni
    if current_user.is_station_manager:
        debug_logger.warning("Accesso negato: utente è un gestore di stazioni")
        return jsonify({'error': 'I gestori di stazioni non possono effettuare prenotazioni'}), 403
    
    # Ottieni i dati della prenotazione dal form
    try:
        data = request.json
        debug_logger.debug(f"Dati ricevuti (JSON): {data}")
    except Exception as e:
        debug_logger.error(f"Errore nel parsing JSON: {str(e)}")
        # Prova a leggere i dati dal form
        data = None
    
    if not data:
        # Se non ci sono dati JSON, prova a leggere i dati dal form
        form_data = request.form
        debug_logger.debug(f"Form data: {form_data}")
        
        # Visualizza anche i raw data per un debug più completo
        raw_data = request.data
        debug_logger.debug(f"Raw request data: {raw_data}")
        
        if form_data:
            # Tentativo di estrazione da form data
            data = {
                'station_id': form_data.get('station_id'),
                'time_slot': form_data.get('time_slot'),
                'duration': form_data.get('duration', '30')
            }
            debug_logger.debug(f"Dati estratti dal form: {data}")
        else:
            debug_logger.error("Nessun dato ricevuto né come JSON né come form")
            return jsonify({'error': 'Dati della prenotazione mancanti'}), 400
    
    # Estrai i campi necessari e logga tutti i passaggi
    station_id = data.get('station_id')
    time_slot = data.get('time_slot')
    duration = data.get('duration', 30)  # Durata predefinita in minuti
    
    # Parametri per specifiche tecniche
    fuel_type = data.get('fuel_type', 'electric')
    connector_type = data.get('connector_type')
    min_power_str = data.get('min_power')
    min_flow_str = data.get('min_flow')
    check_only = data.get('check_only', False)
    
    # Converti min_power e min_flow da stringhe a float
    try:
        min_power = float(min_power_str) if min_power_str else None
    except (ValueError, TypeError):
        min_power = None
        
    try:
        min_flow = float(min_flow_str) if min_flow_str else None
    except (ValueError, TypeError):
        min_flow = None
    
    debug_logger.debug(f"Parametri estratti: station_id={station_id}, time_slot={time_slot}, duration={duration}")
    debug_logger.debug(f"Specifiche tecniche: fuel_type={fuel_type}, connector_type={connector_type}, min_power={min_power}, min_flow={min_flow}")
    
    # Validazione dei dati ricevuti
    if not station_id:
        debug_logger.error("station_id mancante")
        return jsonify({'error': 'ID stazione obbligatorio'}), 400
    
    if not time_slot:
        debug_logger.error("time_slot mancante")
        return jsonify({'error': 'Fascia oraria obbligatoria'}), 400
    
    # Validazione parametri aggiuntivi
    try:
        duration_val = int(duration)
        if duration_val <= 0:
            debug_logger.error("Durata deve essere positiva")
            return jsonify({'error': 'La durata deve essere un numero positivo di minuti'}), 400
    except (ValueError, TypeError):
        debug_logger.error("Durata non valida")
        return jsonify({'error': 'Durata non valida'}), 400
    
    # Validazione tipo carburante
    if fuel_type not in ['electric', 'hydrogen']:
        debug_logger.error(f"Tipo carburante non supportato: {fuel_type}")
        return jsonify({'error': 'Tipo carburante non supportato. Supportati: electric, hydrogen'}), 400
    
    # Validazione parametri cross-type (evita parametri idrogeno per stazioni elettriche)
    if fuel_type == 'electric':
        if connector_type and connector_type in ['h35', 'h70', '350', '700']:
            debug_logger.error("Connettore idrogeno specificato per carburante elettrico")
            return jsonify({'error': 'Connettore non compatibile con il tipo di carburante selezionato'}), 400
        if min_flow:
            debug_logger.error("Parametro flusso specificato per carburante elettrico")
            return jsonify({'error': 'Parametro flusso non applicabile per carburante elettrico'}), 400
    elif fuel_type == 'hydrogen':
        if connector_type and connector_type in ['type2', 'ccs', 'chademo']:
            debug_logger.error("Connettore elettrico specificato per carburante idrogeno")
            return jsonify({'error': 'Connettore non compatibile con il tipo di carburante selezionato'}), 400
        if min_power:
            debug_logger.error("Parametro potenza specificato per carburante idrogeno")
            return jsonify({'error': 'Parametro potenza non applicabile per carburante idrogeno'}), 400
    
    # Converti station_id in intero se è una stringa
    try:
        if isinstance(station_id, str) and station_id.isdigit():
            station_id = int(station_id)
            debug_logger.debug(f"station_id convertito a intero: {station_id}")
    except Exception as e:
        debug_logger.error(f"Errore nella conversione di station_id: {str(e)}")
    
    # Verifica che la stazione esista
    station = Station.query.filter_by(id=station_id).first()
    if not station:
        debug_logger.error(f"Stazione non trovata: {station_id}")
        return jsonify({'error': 'Stazione non trovata'}), 404
    
    debug_logger.debug(f"Stazione trovata: {station.name}")
    
    # Converti time_slot in datetime con gestione errori migliorata
    try:
        from datetime import datetime
        
        # Prova diversi formati di data/ora comuni
        formats_to_try = [
            '%Y-%m-%d %H:%M',  # YYYY-MM-DD HH:MM (formato standard)
            '%Y-%m-%dT%H:%M',  # YYYY-MM-DDThh:mm (ISO 8601 semplificato)
            '%Y-%m-%dT%H:%M:%S',  # YYYY-MM-DDThh:mm:ss (ISO 8601)
            '%Y-%m-%dT%H:%M:%S.%fZ',  # YYYY-MM-DDThh:mm:ss.sssZ (ISO 8601 completo)
            '%d/%m/%Y %H:%M',  # DD/MM/YYYY HH:MM (formato europeo)
            '%m/%d/%Y %H:%M'  # MM/DD/YYYY HH:MM (formato americano)
        ]
        
        booking_time = None
        parse_error = None
        
        debug_logger.debug(f"Tentativo di parse della data/ora: '{time_slot}' usando i formati: {formats_to_try}")
        
        for date_format in formats_to_try:
            try:
                booking_time = datetime.strptime(time_slot, date_format)
                debug_logger.debug(f"Data/ora parsata con successo usando il formato: '{date_format}'")
                break
            except ValueError as e:
                parse_error = e
                continue
        
        if booking_time is None:
            debug_logger.error(f"Impossibile parsare la data/ora: '{time_slot}'. Ultimo errore: {parse_error}")
            return jsonify({
                'error': 'Formato data/ora non valido. Formati supportati: YYYY-MM-DD HH:MM, YYYY-MM-DDThh:mm',
                'received': time_slot,
                'example': '2025-05-15 14:30'
            }), 400
        
        # Verifica che la data non sia nel passato
        if booking_time < datetime.now():
            debug_logger.error(f"Data nel passato: {booking_time}")
            return jsonify({'error': 'Non è possibile prenotare una data nel passato'}), 400
            
    except Exception as e:
        debug_logger.error(f"Errore generico nel parsing della data: {str(e)}")
        debug_logger.error(traceback.format_exc())  # Log dello stack trace completo
        return jsonify({
            'error': 'Errore nella gestione della data/ora',
            'details': str(e),
            'received': time_slot
        }), 400
    
    debug_logger.debug(f"Data/ora prenotazione: {booking_time}")
    
    # Calcola l'orario di fine prenotazione prima di verificare la disponibilità
    end_time = booking_time + timedelta(minutes=int(duration))
    debug_logger.debug(f"Orario fine prenotazione: {end_time}")
    
    # Verifica che ci sia almeno un dispositivo libero per il time slot richiesto
    try:
        # Inizia con tutti i dispositivi della stazione
        devices_query = ChargingPoint.query.filter_by(station_id=station_id)
        
        # Applica filtri per specifiche tecniche
        if fuel_type:
            if fuel_type == 'electric':
                devices_query = devices_query.filter(ChargingPoint.fuel_type == FuelType.ELECTRIC)
            elif fuel_type == 'hydrogen':
                devices_query = devices_query.filter(ChargingPoint.fuel_type == FuelType.HYDROGEN)
        
        if connector_type:
            # Per i connettori elettrici, usa il valore direttamente
            if connector_type in ['type2', 'ccs', 'chademo']:
                devices_query = devices_query.filter(ChargingPoint.connector_type == ConnectorType(connector_type))
            # Per l'idrogeno, il connector_type contiene la pressione (350, 700)
            elif connector_type in ['350', '700']:
                pressure = int(connector_type)
                if pressure == 350:
                    devices_query = devices_query.filter(ChargingPoint.connector_type == ConnectorType.H35)
                elif pressure == 700:
                    devices_query = devices_query.filter(ChargingPoint.connector_type == ConnectorType.H70)
        
        if min_power and fuel_type == 'electric':
            devices_query = devices_query.filter(ChargingPoint.power_level >= min_power)
        
        if min_flow and fuel_type == 'hydrogen':
            devices_query = devices_query.filter(ChargingPoint.flow_rate >= min_flow)
        
        devices = devices_query.all()
        debug_logger.debug(f"Dispositivi corrispondenti ai criteri: {len(devices)}")
        
        # Filtra solo quelli disponibili nel time slot richiesto
        free_devices = [d for d in devices if is_charging_point_available(d.id, booking_time, end_time)]
        debug_logger.debug(f"Dispositivi liberi per slot {booking_time} - {end_time}: {len(free_devices)}")
        
        # In check-only mode, restituiamo solo la disponibilità senza creare prenotazione
        if check_only:
            if free_devices:
                device_info = []
                for d in free_devices:
                    if d.fuel_type == FuelType.ELECTRIC:
                        spec = f"{d.connector_type.value.upper()} - {d.power_level}kW ({d.power_type})"
                    else:
                        spec = f"{d.connector_type.value.upper()} - {d.dispensing_pressure}bar - {d.flow_rate}kg/min"
                    device_info.append({"id": d.id, "identifier": d.identifier, "spec": spec})
                return jsonify({
                    'success': True, 
                    'available_devices': len(free_devices),
                    'devices': device_info
                }), 200
            else:
                return jsonify({'success': False, 'error': 'Nessun dispositivo corrispondente ai criteri per la fascia oraria selezionata'}), 200
        
        # Se non in check-only, blocca se non ci sono dispositivi liberi
        if not free_devices:
            debug_logger.warning("Nessun dispositivo libero nel time slot selezionato")
            return jsonify({'error': 'Nessun dispositivo corrispondente ai criteri per la fascia oraria selezionata'}), 400
        
        # Seleziona il dispositivo migliore (più potente per elettrico, più veloce per idrogeno)
        if fuel_type == 'electric':
            device = max(free_devices, key=lambda d: d.power_level or 0)
        else:
            device = max(free_devices, key=lambda d: d.flow_rate or 0)
        
        debug_logger.debug(f"Dispositivo selezionato: {device.id} - {device.identifier}")
    except Exception as e:
        debug_logger.error(f"Errore nella verifica dei dispositivi liberi: {str(e)}")
        debug_logger.error(traceback.format_exc())
        return jsonify({'error': 'Errore interno durante il controllo di disponibilità'}), 500
    
    # Crea la prenotazione nel DB
    from app.models import ChargingSession
    
    try:
        # Crea la sessione di ricarica con supporto multi-carburante
        session = ChargingSession(
            start_time=booking_time,
            end_time=end_time,
            fuel_type=device.fuel_type,
            energy_consumed=0.0 if device.fuel_type == FuelType.ELECTRIC else None,
            hydrogen_dispensed=0.0 if device.fuel_type == FuelType.HYDROGEN else None,
            user_id=current_user.id,
            charging_point_id=device.id
        )
        
        # Aggiorna lo stato del dispositivo
        device.status = 'booked'
        
        debug_logger.debug("Salvataggio della prenotazione nel database")
        db.session.add(session)
        db.session.commit()
        debug_logger.debug(f"Prenotazione salvata con ID: {session.id}")
        
        # Crea la prenotazione in Orion-LD con supporto multi-carburante
        if device.fuel_type == FuelType.HYDROGEN:
            device_entity_id = f"urn:ngsi-ld:HydrogenDispenser:{device.id}"
            station_entity_id = f"urn:ngsi-ld:HydrogenStation:{station.id}"
            booking_type = "HydrogenBooking"
        else:
            device_entity_id = f"urn:ngsi-ld:ChargingDevice:{device.id}"
            station_entity_id = f"urn:ngsi-ld:ChargingStation:{station.id}"
            booking_type = "ChargingBooking"
        
        booking_entity = {
            "id": f"urn:ngsi-ld:{booking_type}:{session.id}",
            "type": booking_type,
            "fuelType": {
                "type": "Text",
                "value": device.fuel_type.value
            },
            "refUser": {
                "type": "Text",
                "value": f"User:{current_user.id}"
            },
            "refDevice": {
                "type": "Relationship",
                "value": device_entity_id
            },
            "refStation": {
                "type": "Relationship",
                "value": station_entity_id
            },
            "startTime": {
                "type": "DateTime",
                "value": booking_time.strftime('%Y-%m-%dT%H:%M:00Z')
            },
            "endTime": {
                "type": "DateTime",
                "value": end_time.strftime('%Y-%m-%dT%H:%M:00Z')
            },
            "status": {
                "type": "Text",
                "value": "confirmed"
            }
        }

        debug_logger.debug(f"Invio prenotazione a Orion-LD: {booking_entity}")
        
        # Assicurati che gli headers siano corretti
        headers = ORION_HEADERS.copy()
        
        try:
            response = requests.post(
                ORION_ENDPOINT,
                headers=headers,
                json=booking_entity
            )
            
            debug_logger.debug(f"Risposta da Orion-LD: Status={response.status_code}, Body={response.text}")
            
            if response.status_code == 201:
                debug_logger.debug("Prenotazione creata con successo in Orion-LD")
            elif response.status_code == 422 and "Already Exists" in response.text:
                debug_logger.warning(f"Entità già esistente in Orion-LD, continuando comunque: {response.text}")
            else:
                debug_logger.warning(f"Errore Orion-LD (non bloccante): {response.text}")
                # Non blocchiamo la prenotazione per errori Orion-LD
            
            # Aggiorna lo stato del dispositivo in Orion-LD
            device_update = {
                "status": {
                    "type": "Text",
                    "value": "booked"
                }
            }
            
            device_url = f"{ORION_ENDPOINT}/{device_entity_id}/attrs"
            debug_logger.debug(f"Aggiornamento stato dispositivo in Orion-LD: {device_url}")
            
            device_response = requests.patch(
                device_url,
                headers=ORION_HEADERS,
                json=device_update
            )
            
            debug_logger.debug(f"Risposta aggiornamento device: Status={device_response.status_code}, Body={device_response.text}")
            
            if device_response.status_code != 204:
                debug_logger.warning(f"Warning aggiornamento device: {device_response.text}")
        
        except Exception as e:
            debug_logger.error(f"Errore comunicazione con Orion-LD: {str(e)}")
            debug_logger.error(traceback.format_exc())  # Log dello stack trace completo
            # Non facciamo rollback qui per tenere la prenotazione nel DB anche se Orion fallisce
        
        debug_logger.debug("============= PRENOTAZIONE COMPLETATA CON SUCCESSO =============")
        return jsonify({
            'success': True,
            'booking_id': session.id,
            'message': 'Prenotazione effettuata con successo',
            'details': {
                'station': station.name,
                'start_time': booking_time.strftime('%Y-%m-%d %H:%M'),
                'end_time': end_time.strftime('%Y-%m-%d %H:%M'),
                'device_id': device.identifier,
                'fuel_type': device.fuel_type.value
            }
        })
        
    except Exception as e:
        # Rollback in caso di errore
        db.session.rollback()
        debug_logger.error(f"Eccezione critica nella creazione della prenotazione: {str(e)}")
        debug_logger.error(traceback.format_exc())  # Log dello stack trace completo
        return jsonify({'error': f'Errore nella creazione della prenotazione: {str(e)}'}), 500

@bp.route('/api/stations', methods=['GET'])
def get_stations():
    """API per ottenere le stazioni di ricarica filtrate per città e specifiche tecniche"""
    city = request.args.get('city', '')
    time_slot_str = request.args.get('time_slot')
    duration = int(request.args.get('duration', 30))
    
    # Filtri carburante e specifiche tecniche
    fuel_type = request.args.get('fuel_type')
    connector_type = request.args.get('connector_type')
    min_power = request.args.get('min_power', type=float)
    pressure = request.args.get('pressure', type=int)
    min_flow = request.args.get('min_flow', type=float)
    
    # Base query
    query = Station.query
    if city:
        query = query.filter(Station.address.contains(city))
    
    # Filtro per tipo di carburante a livello di stazione
    # Non applico il filtro qui, lo farò a livello Python poiché il campo JSON ha problemi con la query
    all_stations = query.all()
    
    # Filtra le stazioni in base al tipo di carburante
    if fuel_type:
        filtered_stations_list = []
        for station in all_stations:
            if station.fuel_types and fuel_type in station.fuel_types:
                filtered_stations_list.append(station)
        all_stations = filtered_stations_list
    
    # Usa le stazioni filtrate
    stations = all_stations
    
    # Filtri aggiuntivi a livello di dispositivo
    filtered_stations = []
    for station in stations:
        cps = ChargingPoint.query.filter_by(station_id=station.id)
        
        # Applica filtri per le specifiche tecniche
        if fuel_type:
            if fuel_type == 'electric':
                cps = cps.filter(ChargingPoint.fuel_type == FuelType.ELECTRIC)
            elif fuel_type == 'hydrogen':
                cps = cps.filter(ChargingPoint.fuel_type == FuelType.HYDROGEN)
        
        if connector_type:
            cps = cps.filter(ChargingPoint.connector_type == ConnectorType(connector_type))
        
        if min_power and fuel_type == 'electric':
            cps = cps.filter(ChargingPoint.power_level >= min_power)
        
        if pressure and fuel_type == 'hydrogen':
            cps = cps.filter(ChargingPoint.dispensing_pressure >= pressure)
        
        if min_flow and fuel_type == 'hydrogen':
            cps = cps.filter(ChargingPoint.flow_rate >= min_flow)
        
        cps = cps.all()
        
        # Solo includi stazioni che hanno almeno un dispositivo che corrisponde ai criteri
        if cps:
            filtered_stations.append((station, cps))
    
    stations = filtered_stations
    
    # Prepare response data
    result = []
    for station, filtered_cps in stations:
        total_devices = len(filtered_cps)
        # Compute availability based on time slot if provided
        if time_slot_str:
            try:
                start_dt = datetime.fromisoformat(time_slot_str)
            except ValueError:
                start_dt = datetime.strptime(time_slot_str, '%Y-%m-%d %H:%M')
            end_dt = start_dt + timedelta(minutes=duration)
            available_devices = sum(1 for cp in filtered_cps if is_charging_point_available(cp.id, start_dt, end_dt))
        else:
            available_devices = sum(1 for cp in filtered_cps if cp.status == 'available')
        available = available_devices > 0
        
        # Informazioni dettagliate sui dispositivi
        device_specs = []
        for cp in filtered_cps:
            if cp.fuel_type == FuelType.ELECTRIC:
                spec = f"{cp.connector_type.value.upper()} - {cp.power_level}kW ({cp.power_type})"
            else:  # HYDROGEN
                spec = f"{cp.connector_type.value.upper()} - {cp.dispensing_pressure}bar - {cp.flow_rate}kg/min"
            device_specs.append(spec)
        
        result.append({
            'id': station.id,
            'name': station.name,
            'address': station.address,
            'lat': station.latitude,
            'lng': station.longitude,
            'available': available,
            'available_devices': available_devices,
            'total_devices': total_devices,
            'station_type': station.station_type or 'electric',
            'fuel_types': station.fuel_types or ['electric'],
            'device_specs': device_specs
        })
    
    return jsonify({
        'success': True,
        'stations': result,
        'count': len(result)
    })

@bp.route('/api/station/<int:station_id>/specs', methods=['GET'])
def get_station_specs(station_id):
    """API per ottenere le specifiche tecniche disponibili per una stazione"""
    station = Station.query.get_or_404(station_id)
    
    # Ottieni tutti i dispositivi della stazione
    devices = ChargingPoint.query.filter_by(station_id=station_id).all()
    
    # Organizza le specifiche per tipo di carburante
    electric_specs = {
        'connectors': set(),
        'power_levels': set(),
        'power_types': set(),
        'voltages': set()
    }
    
    hydrogen_specs = {
        'connectors': set(),
        'pressures': set(),
        'flow_rates': set(),
        'purity_levels': set()
    }
    
    for device in devices:
        if device.fuel_type == FuelType.ELECTRIC:
            if device.connector_type:
                electric_specs['connectors'].add(device.connector_type.value)
            if device.power_level:
                electric_specs['power_levels'].add(device.power_level)
            if device.power_type:
                electric_specs['power_types'].add(device.power_type)
            if device.voltage:
                electric_specs['voltages'].add(device.voltage)
        elif device.fuel_type == FuelType.HYDROGEN:
            if device.connector_type:
                hydrogen_specs['connectors'].add(device.connector_type.value)
            if device.dispensing_pressure:
                hydrogen_specs['pressures'].add(device.dispensing_pressure)
            if device.flow_rate:
                hydrogen_specs['flow_rates'].add(device.flow_rate)
            if device.purity_level:
                hydrogen_specs['purity_levels'].add(device.purity_level)
    
    # Converti i set in liste ordinate
    electric_specs = {
        'connectors': sorted(list(electric_specs['connectors'])),
        'power_levels': sorted(list(electric_specs['power_levels'])),
        'power_types': sorted(list(electric_specs['power_types'])),
        'voltages': sorted(list(electric_specs['voltages']))
    }
    
    hydrogen_specs = {
        'connectors': sorted(list(hydrogen_specs['connectors'])),
        'pressures': sorted(list(hydrogen_specs['pressures'])),
        'flow_rates': sorted(list(hydrogen_specs['flow_rates'])),
        'purity_levels': sorted(list(hydrogen_specs['purity_levels']))
    }
    
    return jsonify({
        'success': True,
        'station_id': station_id,
        'station_name': station.name,
        'fuel_types': station.fuel_types or ['electric'],
        'electric_specs': electric_specs,
        'hydrogen_specs': hydrogen_specs
    })

@bp.route('/api/specs/available', methods=['GET'])
def get_available_specs():
    """API per ottenere tutte le specifiche tecniche disponibili nel sistema"""
    fuel_type = request.args.get('fuel_type')
    city = request.args.get('city', '')
    
    # Filtra stazioni per città se specificata
    station_query = Station.query
    if city:
        station_query = station_query.filter(Station.address.contains(city))
    
    # Filtra stazioni per tipo di carburante se specificato
    if fuel_type:
        stations = []
        for station in station_query.all():
            if station.fuel_types and fuel_type in station.fuel_types:
                stations.append(station)
    else:
        stations = station_query.all()
    
    # Ottieni tutti i dispositivi delle stazioni filtrate
    station_ids = [s.id for s in stations]
    devices_query = ChargingPoint.query.filter(ChargingPoint.station_id.in_(station_ids))
    
    if fuel_type:
        if fuel_type == 'electric':
            devices_query = devices_query.filter(ChargingPoint.fuel_type == FuelType.ELECTRIC)
        elif fuel_type == 'hydrogen':
            devices_query = devices_query.filter(ChargingPoint.fuel_type == FuelType.HYDROGEN)
    
    devices = devices_query.all()
    
    # Organizza le specifiche aggregate
    electric_specs = {
        'connectors': set(),
        'power_levels': set(),
        'power_types': set()
    }
    
    hydrogen_specs = {
        'connectors': set(),
        'pressures': set(),
        'flow_rates': set()
    }
    
    for device in devices:
        if device.fuel_type == FuelType.ELECTRIC:
            if device.connector_type:
                electric_specs['connectors'].add(device.connector_type.value)
            if device.power_level:
                electric_specs['power_levels'].add(device.power_level)
            if device.power_type:
                electric_specs['power_types'].add(device.power_type)
        elif device.fuel_type == FuelType.HYDROGEN:
            if device.connector_type:
                hydrogen_specs['connectors'].add(device.connector_type.value)
            if device.dispensing_pressure:
                hydrogen_specs['pressures'].add(device.dispensing_pressure)
            if device.flow_rate:
                hydrogen_specs['flow_rates'].add(device.flow_rate)
    
    # Converti i set in liste ordinate con etichette
    electric_connectors = []
    for connector_value in electric_specs['connectors']:
        electric_connectors.append({
            'value': connector_value,
            'label': get_connector_label(connector_value)
        })
    
    hydrogen_connectors = []
    for connector_value in hydrogen_specs['connectors']:
        hydrogen_connectors.append({
            'value': connector_value,
            'label': get_connector_label(connector_value)
        })
    
    electric_specs = {
        'connectors': sorted(electric_connectors, key=lambda x: x['value']),
        'power_levels': sorted(list(electric_specs['power_levels'])),
        'power_types': sorted(list(electric_specs['power_types']))
    }
    
    hydrogen_specs = {
        'connectors': sorted(hydrogen_connectors, key=lambda x: x['value']),
        'pressures': sorted(list(hydrogen_specs['pressures'])),
        'flow_rates': sorted(list(hydrogen_specs['flow_rates']))
    }
    
    return jsonify({
        'success': True,
        'fuel_type': fuel_type,
        'city': city,
        'electric_specs': electric_specs,
        'hydrogen_specs': hydrogen_specs
    })

def get_connector_label(connector_value):
    """Ottieni etichetta user-friendly per i connettori"""
    labels = {
        'type2': 'Type 2 (AC - Standard Europeo)',
        'ccs': 'CCS (DC - Combined Charging)',
        'chademo': 'CHAdeMO (DC - Standard Giapponese)',
        'h35': 'H35 (350 bar)',
        'h70': 'H70 (700 bar)'
    }
    return labels.get(connector_value, connector_value.upper())

@bp.route('/api/station/<int:station_id>/devices', methods=['GET'])
@login_required
def get_station_devices(station_id):
    """API per ottenere i dispositivi di una stazione"""
    # Verifica che la stazione esista
    station = Station.query.get_or_404(station_id)
    
    # Ottieni i dispositivi
    devices = ChargingPoint.query.filter_by(station_id=station_id).all()
    
    # Prepara i dati per la risposta
    result = []
    for device in devices:
        device_info = {
            'id': device.id,
            'identifier': device.identifier,
            'fuel_type': device.fuel_type.value,
            'status': device.status
        }
        
        # Aggiungi campi specifici per tipo carburante
        if device.fuel_type == FuelType.ELECTRIC:
            device_info.update({
                'power_type': device.power_type,
                'power_level': device.power_level,
                'voltage': device.voltage,
                'current': device.current
            })
        elif device.fuel_type == FuelType.HYDROGEN:
            device_info.update({
                'dispensing_pressure': device.dispensing_pressure,
                'flow_rate': device.flow_rate,
                'purity_level': device.purity_level
            })
        
        result.append(device_info)
    
    return jsonify({
        'success': True,
        'station_name': station.name,
        'devices': result,
        'count': len(result)
    })

@bp.route('/api/user/bookings', methods=['GET'])
@login_required
def get_user_bookings():
    """API per ottenere le prenotazioni dell'utente corrente"""
    if current_user.is_station_manager:
        return jsonify({'error': 'Accesso non autorizzato'}), 403
    
    from app.models import ChargingSession
    
    # Ottieni le prenotazioni dell'utente
    bookings = ChargingSession.query.filter_by(user_id=current_user.id).all()
    
    # Prepara i dati per la risposta
    result = []
    for booking in bookings:
        # Ottieni informazioni sulla stazione
        device = ChargingPoint.query.get(booking.charging_point_id)
        station = Station.query.get(device.station_id) if device else None
        
        result.append({
            'id': booking.id,
            'start_time': booking.start_time.strftime('%Y-%m-%d %H:%M'),
            'end_time': booking.end_time.strftime('%Y-%m-%d %H:%M') if booking.end_time else None,
            'energy_consumed': booking.energy_consumed,
            'device_id': device.identifier if device else None,
            'station_name': station.name if station else None,
            'station_address': station.address if station else None,
            'status': 'completed' if booking.end_time and booking.end_time < datetime.utcnow() else 'active'
        })
    
    return jsonify({
        'success': True,
        'bookings': result,
        'count': len(result)
    })

@bp.route('/api/station/bookings', methods=['GET'])
@login_required
def get_station_bookings():
    """API per ottenere le prenotazioni della stazione dell'utente corrente"""
    if not current_user.is_station_manager or not current_user.station_id:
        return jsonify({'error': 'Accesso non autorizzato'}), 403
    
    from app.models import ChargingSession
    from datetime import datetime
    
    # Ottieni i dispositivi della stazione
    devices = ChargingPoint.query.filter_by(station_id=current_user.station_id).all()
    device_ids = [device.id for device in devices]
    
    # Ottieni le prenotazioni per questi dispositivi
    bookings = ChargingSession.query.filter(ChargingSession.charging_point_id.in_(device_ids)).all()
    
    # Prepara i dati per la risposta
    result = []
    for booking in bookings:
        # Ottieni informazioni sull'utente
        user = User.query.get(booking.user_id)
        device = ChargingPoint.query.get(booking.charging_point_id)
        
        result.append({
            'id': booking.id,
            'user_id': booking.user_id,
            'user_name': f"{user.name} {user.surname}" if user else "Utente sconosciuto",
            'trust_score': user.trust_score if user else 0,
            'user_email': user.email if user else None,
            'start_time': booking.start_time.strftime('%Y-%m-%d %H:%M'),
            'end_time': booking.end_time.strftime('%Y-%m-%d %H:%M') if booking.end_time else None,
            'duration': int((booking.end_time - booking.start_time).total_seconds() / 60) if booking.end_time else None,
            'device_id': device.identifier if device else None,
            'energy_consumed': booking.energy_consumed,
            'status': 'completed' if booking.end_time and booking.end_time < datetime.utcnow() else 'active'
        })
    
    return jsonify({
        'success': True,
        'bookings': result,
        'count': len(result)
    })

@bp.route('/booking/create', methods=['POST'])
@login_required
def create_new_booking():
    """Crea una nuova prenotazione per una stazione di ricarica"""
    data = request.json
    if not data:
        return jsonify({'error': 'Dati della prenotazione mancanti'}), 400
    
    # Estrai i dati dalla richiesta
    station_id = data.get('station_id')
    charging_point_id = data.get('charging_point_id')
    start_time_str = data.get('scheduled_start')
    end_time_str = data.get('scheduled_end')
    
    if not station_id or not charging_point_id or not start_time_str or not end_time_str:
        return jsonify({'error': 'Parametri mancanti'}), 400
    
    # Converti stringhe in datetime
    try:
        scheduled_start = datetime.fromisoformat(start_time_str)
        scheduled_end = datetime.fromisoformat(end_time_str)
    except ValueError:
        return jsonify({'error': 'Formato data non valido. Usa il formato ISO 8601 (YYYY-MM-DDTHH:MM:SS)'}), 400
    
    # Verifica che l'orario di inizio sia nel futuro
    if scheduled_start <= datetime.utcnow():
        return jsonify({'error': 'L\'orario di inizio deve essere nel futuro'}), 400
    
    # Verifica che l'orario di fine sia successivo all'inizio
    if scheduled_end <= scheduled_start:
        return jsonify({'error': 'L\'orario di fine deve essere successivo all\'orario di inizio'}), 400
    
    # Crea la prenotazione
    booking = create_booking(
        user_id=current_user.id,
        station_id=station_id,
        charging_point_id=charging_point_id,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end
    )
    
    if booking:
        return jsonify({
            'success': True,
            'booking_id': booking.id,
            'message': 'Prenotazione creata con successo'
        }), 201
    else:
        return jsonify({'error': 'Impossibile creare la prenotazione'}), 400

@bp.route('/bookings/user', methods=['GET'])
@login_required
def list_user_bookings():
    """Elenca tutte le prenotazioni dell'utente corrente"""
    bookings = get_user_bookings(current_user.id)
    
    # Formatta le prenotazioni per la risposta JSON
    bookings_data = []
    for booking in bookings:
        bookings_data.append({
            'id': booking.id,
            'station_name': booking.station.name,
            'station_address': booking.station.address,
            'charging_point': booking.charging_point.identifier,
            'scheduled_start': booking.scheduled_start.isoformat(),
            'scheduled_end': booking.scheduled_end.isoformat(),
            'booking_time': booking.booking_time.isoformat(),
            'status': booking.status
        })
    
    return jsonify({'bookings': bookings_data})

@bp.route('/booking/cancel/<int:booking_id>', methods=['POST'])
@csrf.exempt
@login_required
def cancel_user_booking(booking_id):
    """Annulla una prenotazione esistente"""
    # Usa ChargingSession: cancella la sessione dal DB e libera il punto
    session = ChargingSession.query.get(booking_id)
    if not session:
        return jsonify({'error': 'Prenotazione non trovata'}), 404
    if session.user_id != current_user.id:
        return jsonify({'error': 'Non sei autorizzato ad annullare questa prenotazione'}), 403
    # Impedisci cancellazione se già iniziata
    if session.start_time <= datetime.utcnow():
        return jsonify({'error': 'Impossibile annullare una prenotazione già iniziata'}), 400
    # Rimuovi sessione e libera il punto di ricarica
    cp = ChargingPoint.query.get(session.charging_point_id)
    db.session.delete(session)
    if cp:
        cp.status = 'available'
    db.session.commit()
    # Patch su Orion-LD ChargingBooking entity
    try:
        entity_id = f"urn:ngsi-ld:ChargingBooking:{booking_id}"
        patch_url = f"{ORION_ENDPOINT}/{entity_id}/attrs"
        payload = {'status': {'type': 'Text', 'value': 'cancelled'}}
        requests.patch(patch_url,
            headers={
                'Content-Type': 'application/json',
                'Fiware-Service': FIWARE_SERVICE,
                'Fiware-ServicePath': FIWARE_SERVICEPATH
            }, json=payload)
    except Exception:
        pass
    return jsonify({'success': True, 'message': 'Prenotazione annullata con successo'})

@bp.route('/bookings/station', methods=['GET'])
@login_required
def list_station_bookings():
    """Elenca tutte le prenotazioni per la stazione gestita dall'utente corrente"""
    # Verifica che l'utente sia un gestore stazione
    if not current_user.is_station_manager or not current_user.station_id:
        return jsonify({'error': 'Accesso non autorizzato'}), 403
    
    bookings = get_station_bookings(current_user.station_id)
    
    # Formatta le prenotazioni per la risposta JSON
    bookings_data = []
    for booking in bookings:
        bookings_data.append({
            'id': booking.id,
            'user_email': booking.user.email,
            'charging_point': booking.charging_point.identifier,
            'scheduled_start': booking.scheduled_start.isoformat(),
            'scheduled_end': booking.scheduled_end.isoformat(),
            'booking_time': booking.booking_time.isoformat(),
            'status': booking.status
        })
    
    return jsonify({'bookings': bookings_data})

@bp.route('/auth/user/bookings', methods=['GET'])
@login_required
def auth_user_bookings():
    """API per ottenere le prenotazioni dell'utente corrente - endpoint compatibile con il frontend"""
    return get_user_bookings()

@bp.route('/user/booking/<int:booking_id>', methods=['GET'])
@login_required
def get_booking_details(booking_id):
    """API per ottenere i dettagli di una specifica prenotazione"""
    if current_user.is_station_manager:
        return jsonify({'error': 'Accesso non autorizzato'}), 403
    
    from app.models import ChargingSession
    
    # Ottieni la prenotazione
    booking = ChargingSession.query.filter_by(id=booking_id, user_id=current_user.id).first()
    
    if not booking:
        return jsonify({'error': 'Prenotazione non trovata o non autorizzata'}), 404
    
    # Ottieni informazioni sulla stazione
    device = ChargingPoint.query.get(booking.charging_point_id)
    station = Station.query.get(device.station_id) if device else None
    
    # Prepara i dati per la risposta
    booking_data = {
        'id': booking.id,
        'start_time': booking.start_time.strftime('%Y-%m-%d %H:%M'),
        'end_time': booking.end_time.strftime('%Y-%m-%d %H:%M') if booking.end_time else None,
        'energy_consumed': booking.energy_consumed,
        'device_id': device.identifier if device else None,
        'charging_point_id': booking.charging_point_id,
        'charging_point_name': device.identifier if device else "Sconosciuto",
        'station_id': station.id if station else None,
        'station_name': station.name if station else "Sconosciuta",
        'station_address': station.address if station else None,
        'status': 'completed' if booking.end_time and booking.end_time < datetime.utcnow() else 'active',
        'booking_time': booking.start_time.strftime('%Y-%m-%d %H:%M')
    }
    
    return jsonify({
        'success': True,
        'booking': booking_data
    })

@bp.route('/user/bookings', methods=['GET'])
@login_required
def user_bookings():
    """API per ottenere le prenotazioni dell'utente corrente"""
    from app.models import ChargingSession
    from datetime import datetime
    
    # Ottieni le prenotazioni dell'utente
    bookings = ChargingSession.query.filter_by(user_id=current_user.id).all()
    
    # Prepara i dati per la risposta
    result = []
    for booking in bookings:
        # Ottieni informazioni sulla stazione
        device = ChargingPoint.query.get(booking.charging_point_id)
        station = Station.query.get(device.station_id) if device else None
        
        result.append({
            'id': booking.id,
            'start_time': booking.start_time.strftime('%Y-%m-%d %H:%M'),
            'end_time': booking.end_time.strftime('%Y-%m-%d %H:%M') if booking.end_time else None,
            'energy_consumed': booking.energy_consumed,
            'device_id': device.identifier if device else None,
            'charging_point_id': booking.charging_point_id,
            'charging_point_name': device.identifier if device else "Sconosciuto",
            'station_id': station.id if station else None,
            'station_name': station.name if station else "Sconosciuta",
            'station_address': station.address if station else None,
            'status': 'completed' if booking.end_time and booking.end_time < datetime.utcnow() else 'active',
            'scheduled_start': booking.start_time.strftime('%Y-%m-%d %H:%M'),
            'scheduled_end': booking.end_time.strftime('%Y-%m-%d %H:%M') if booking.end_time else None
        })
    
    return jsonify({
        'success': True,
        'bookings': result,
        'count': len(result)
    })

# Mark a station booking as success or no-show and update user trust
# @bp.route('/api/station/bookings/<int:booking_id>/mark', methods=['POST'])
# @bp.route('/api/station/bookings/<int:booking_id>/mark/', methods=['POST']) # Explicitly add route with trailing slash
# @csrf.exempt
# @login_required
# def mark_booking(booking_id):
#    logging.getLogger('auth').debug(f"[DEBUG] mark_booking called for booking_id={booking_id}, json={request.get_json()}")
#    # authorization checks...
#    data = request.get_json() or {}
#    result = data.get('result')
#    if result not in ['success', 'no_show']:
#        return jsonify({'error': 'Risultato non valido'}), 400
#    booking = Booking.query.get_or_404(booking_id)
#    if booking.station_id != current_user.station_id:
#        return jsonify({'error': 'Accesso non autorizzato'}), 403
#    user = User.query.get(booking.user_id)
#    # Update booking status and user trust score
#    if result == 'success':
#        booking.status = 'completed'
#        score_delta = 1
#    else:
#        booking.status = 'no_show'
#        score_delta = -1
#    user.trust_score = user.trust_score + score_delta
#    # Create a TrustRecord
#    trust_rec = TrustRecord(booking_id=booking.id, user_id=user.id, station_id=current_user.station_id, score_change=score_delta)
#    db.session.add(trust_rec)
#    db.session.commit()
#    # Patch or create trust_score in Orion-LD user entity
#    try:
#        user_entity_id = f"urn:ngsi-ld:User:{user.id}"
#        patch_url = f"{ORION_ENDPOINT}/{user_entity_id}/attrs"
#        payload = {'trust_score': {'type': 'Number', 'value': user.trust_score}}
#        resp = requests.patch(patch_url, headers=ORION_HEADERS, json=payload)
#        if resp.status_code == 404:
#            # entity not found: create user entity
#            user_entity = {
#                'id': user_entity_id,
#                'type': 'User',
#                'name': {'type': 'Text', 'value': user.name + ' ' + user.surname},
#                'email': {'type': 'Text', 'value': user.email},
#                'trust_score': {'type': 'Number', 'value': user.trust_score}
#            }
#            requests.post(ORION_ENDPOINT, headers=ORION_HEADERS, json=user_entity)
#    except Exception:
#        pass
#    return jsonify({'success': True, 'status': booking.status, 'trust_score': user.trust_score})


@bp.route('/api/station/bookings/<int:charging_session_id>/mark', methods=['POST'])
@csrf.exempt
@login_required
def mark_booking(charging_session_id):
    if not current_user.is_station_manager or not current_user.station_id:
        return jsonify({'error': 'Accesso non autorizzato: solo gestori stazione'}), 403

    data = request.get_json()
    if not data or 'result' not in data:
        current_app.logger.warning(f"mark_booking: Dati mancanti o formato non valido. Payload: {data}")
        return jsonify({'error': 'Dati mancanti o formato non valido'}), 400

    result_status = data.get('result')  # 'success' or 'no_show'
    if result_status not in ['success', 'no_show']:
        return jsonify({'error': "Valore 'result' non valido"}), 400

    # 1. Fetch the ChargingSession
    session = ChargingSession.query.get(charging_session_id)
    if not session:
        return jsonify({'error': f'Sessione di ricarica con ID {charging_session_id} non trovata'}), 404

    # 2. Get related User and ChargingPoint
    user = User.query.get(session.user_id)
    if not user:
        current_app.logger.error(f"mark_booking: Utente con ID {session.user_id} non trovato per sessione {session.id}")
        return jsonify({'error': f'Utente con ID {session.user_id} non trovato'}), 404

    charging_point = ChargingPoint.query.get(session.charging_point_id)
    if not charging_point:
        current_app.logger.error(f"mark_booking: Punto di ricarica {session.charging_point_id} non trovato per sessione {session.id}")
        return jsonify({'error': f'Punto di ricarica con ID {session.charging_point_id} non trovato'}), 404
    
    if charging_point.station_id != current_user.station_id:
        return jsonify({'error': 'Accesso non autorizzato: sessione non appartiene a questa stazione'}), 403

    # 3. Find or create temporary Booking record (needed for TrustRecord)
    booking = Booking.query.filter_by(
        user_id=session.user_id,
        charging_point_id=session.charging_point_id,
        scheduled_start=session.start_time
    ).order_by(Booking.booking_time.desc()).first()

    if not booking:
        current_app.logger.info(f"Nessuna prenotazione (Booking) esistente trovata per sessione {session.id}. Creazione di una temporanea per TrustRecord.")
        if not session.end_time:
            session.end_time = session.start_time + timedelta(minutes=30)  # Default duration if not set

        booking = Booking(
            user_id=session.user_id,
            charging_point_id=session.charging_point_id,
            station_id=charging_point.station_id,
            scheduled_start=session.start_time,
            scheduled_end=session.end_time,
            booking_time=session.start_time,
            status='processing_for_trust_record'
        )
        db.session.add(booking)
        try:
            db.session.flush()  # Get an ID for the booking
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Errore DB durante il flush per nuova Prenotazione (Booking): {str(e)}")
            return jsonify({'error': 'Errore database creando record prenotazione temporaneo'}), 500

    # Store booking ID for TrustRecord
    booking_id_for_trust = booking.id

    # 4. Update User trust_score
    if result_status == 'success':
        if user.trust_score is None:
            user.trust_score = 0
        user.trust_score += 1
        score_delta = 1
    else:  # no_show
        if user.trust_score is None:
            user.trust_score = 0
        user.trust_score -= 1
        score_delta = -1

    # 5. Create TrustRecord
    trust_record = TrustRecord(
        booking_id=booking_id_for_trust,
        user_id=user.id,
        station_id=current_user.station_id,
        score_change=score_delta,
        user_trust_score_after_change=user.trust_score,
        timestamp=datetime.utcnow()
    )
    db.session.add(trust_record)
    db.session.add(user)

    # 6. Delete ChargingSession and Booking from database
    db.session.delete(session)
    db.session.delete(booking)

    # 7. Mark ChargingPoint as available again
    charging_point.status = 'available'
    db.session.add(charging_point)

    try:
        db.session.commit()
        current_app.logger.info(f"Sessione {charging_session_id} e Booking {booking_id_for_trust} eliminati dal DB. Trust score utente aggiornato.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore DB durante il commit in mark_booking: {str(e)}")
        return jsonify({'error': 'Errore durante il salvataggio nel database'}), 500

    # 8. Delete the ChargingBooking entity from Orion-LD
    try:
        entity_id = f"urn:ngsi-ld:ChargingBooking:{charging_session_id}"
        delete_url = f"{ORION_ENDPOINT}/{entity_id}"
        
        # Create specific headers for delete operation - no Content-Type needed for DELETE
        delete_headers = {
            'Fiware-Service': FIWARE_SERVICE,
            'Fiware-ServicePath': FIWARE_SERVICEPATH
        }
        
        delete_response = requests.delete(delete_url, headers=delete_headers)
        
        if delete_response.status_code == 204:
            current_app.logger.info(f"Entità ChargingBooking {entity_id} eliminata da Orion-LD.")
        elif delete_response.status_code == 404:
            current_app.logger.info(f"Entità ChargingBooking {entity_id} non trovata in Orion-LD (già eliminata).")
        else:
            current_app.logger.error(f"Errore eliminazione entità ChargingBooking {entity_id} da Orion-LD: {delete_response.status_code} - {delete_response.text}")
            # Don't fail the operation if Orion-LD delete fails, just log the error
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Errore richiesta Orion-LD (delete) in mark_booking: {str(e)}")
        # Don't fail the operation if Orion-LD request fails, just log the error

    # 9. Update User trust_score in Orion-LD
    try:
        user_entity_id = f"urn:ngsi-ld:User:{user.id}"
        patch_url = f"{ORION_ENDPOINT}/{user_entity_id}/attrs"
        patch_payload = {'trust_score': {'type': 'Number', 'value': user.trust_score}}
        patch_response = requests.patch(patch_url, headers=ORION_HEADERS, json=patch_payload)

        if patch_response.status_code == 404:
            # Create user entity if it doesn't exist
            user_entity = {
                "id": user_entity_id,
                "type": "User",
                "name": {"type": "Text", "value": f"{user.name} {user.surname}" if user.name and user.surname else user.username},
                "email": {"type": "Text", "value": user.email},
                "trust_score": {"type": "Number", "value": user.trust_score}
            }
            create_response = requests.post(ORION_ENDPOINT, headers=ORION_HEADERS, json=user_entity)
            if create_response.status_code != 201:
                current_app.logger.error(f"Errore creazione entità utente in Orion: {create_response.status_code}")
        elif patch_response.status_code != 204:
            current_app.logger.error(f"Errore aggiornamento trust score utente in Orion: {patch_response.status_code}")
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Errore richiesta Orion-LD (update user) in mark_booking: {str(e)}")

    return jsonify({
        'success': True,
        'message': f'Sessione {charging_session_id} processata con successo. Trust score utente aggiornato a {user.trust_score}.',
        'user_trust_score': user.trust_score
    })

# API per ottenere i trust record della stazione
@bp.route('/api/station/trust-records', methods=['GET'])
@login_required
def get_trust_records():
    if not current_user.is_station_manager or not current_user.station_id:
        return jsonify({'error': 'Accesso non autorizzato'}), 403

    user_name_filter = request.args.get('user_name_filter', None)
    
    query = db.session.query(TrustRecord).join(User, TrustRecord.user_id == User.id)\
                      .filter(TrustRecord.station_id == current_user.station_id)

    if user_name_filter and user_name_filter.strip():
        # Use "starts with" search logic (e.g., 'ad%')
        search_term_starts_with = f"{user_name_filter.strip()}%"
        query = query.filter(
            or_(
                User.name.ilike(search_term_starts_with),
                User.surname.ilike(search_term_starts_with),
                func.concat(User.name, ' ', User.surname).ilike(search_term_starts_with)
            )
        )
    
    records = query.order_by(TrustRecord.timestamp.desc()).limit(5).all()
    
    result = []
    for r in records:
        usr = r.user # Access the related User object via the relationship
        booking_record = Booking.query.get(r.booking_id) 
        
        result.append({
            'id': r.id,
            'booking_id': r.booking_id,
            'user_name': f"{usr.name} {usr.surname}" if usr and usr.name and usr.surname else (usr.username if usr else 'Sconosciuto'),
            'punteggio_utente_dopo_evento': r.user_trust_score_after_change, 
            'variazione_punteggio': r.score_change, 
            'timestamp': r.timestamp.strftime('%Y-%m-%d %H:%M'),
            'booking_start_time': booking_record.scheduled_start.strftime('%Y-%m-%d %H:%M') if booking_record else 'N/A'
        })
    
    return jsonify({'success': True, 'records': result, 'count': len(result)}) # count will be max 5