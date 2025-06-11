// JavaScript per la gestione dinamica del form di registrazione stazione

document.addEventListener('DOMContentLoaded', function() {
    const stationTypeSelect = document.getElementById('station_type');
    const fuelTypesContainer = document.querySelector('.fuel-types-container');
    const hydrogenFields = document.getElementById('hydrogen-fields');
    const electricFields = document.getElementById('electric-fields');
    // Prova diversi selettori per le checkbox dei carburanti
    let fuelTypeCheckboxes = document.querySelectorAll('input[type="checkbox"][id^="fuel_types-"]');
    if (fuelTypeCheckboxes.length === 0) {
        fuelTypeCheckboxes = document.querySelectorAll('input[name="fuel_types"]');
    }
    if (fuelTypeCheckboxes.length === 0) {
        fuelTypeCheckboxes = document.querySelectorAll('.fuel-types-container input[type="checkbox"]');
    }
    
    // Funzione per aggiornare la visibilità dei campi in base al tipo di stazione
    function updateFieldsVisibility() {
        const stationType = stationTypeSelect.value;
        // console.log('Station type selected:', stationType);
        // console.log('Found fuel type checkboxes:', fuelTypeCheckboxes.length);
        
        // Aggiorna le checkbox dei carburanti in base al tipo di stazione
        if (stationType === 'electric') {
            // Solo elettrico
            fuelTypeCheckboxes.forEach(cb => {
                // Controlla sia il valore che il testo del label
                const label = cb.nextElementSibling;
                const labelText = label ? label.textContent.trim() : '';
                if (cb.value === 'electric' || labelText === 'Elettrico') {
                    cb.checked = true;
                    cb.disabled = false;
                } else {
                    cb.checked = false;
                    cb.disabled = true;
                }
            });
        } else if (stationType === 'hydrogen') {
            // Solo idrogeno
            fuelTypeCheckboxes.forEach(cb => {
                // Controlla sia il valore che il testo del label
                const label = cb.nextElementSibling;
                const labelText = label ? label.textContent.trim() : '';
                if (cb.value === 'hydrogen' || labelText === 'Idrogeno') {
                    cb.checked = true;
                    cb.disabled = false;
                } else {
                    cb.checked = false;
                    cb.disabled = true;
                }
            });
        } else if (stationType === 'hybrid') {
            // Entrambi
            fuelTypeCheckboxes.forEach(cb => {
                cb.disabled = false;
                cb.checked = true; // Seleziona entrambi per default
            });
        } else {
            // Nessun tipo selezionato - abilita tutto ma non selezionare nulla
            fuelTypeCheckboxes.forEach(cb => {
                cb.disabled = false;
                cb.checked = false;
            });
        }
        
        // Aggiorna selectedFuelTypes dopo aver modificato le checkbox
        const selectedFuelTypes = Array.from(fuelTypeCheckboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);
        
        // Mostra/nascondi campi elettrici
        const showElectricFields = selectedFuelTypes.includes('electric') || stationType === 'electric' || stationType === 'hybrid';
        if (electricFields) {
            electricFields.style.display = showElectricFields ? 'block' : 'none';
        }
        
        // Mostra/nascondi campi idrogeno
        const showHydrogenFields = selectedFuelTypes.includes('hydrogen') || stationType === 'hydrogen' || stationType === 'hybrid';
        if (hydrogenFields) {
            hydrogenFields.style.display = showHydrogenFields ? 'block' : 'none';
        }
        
        // Rendi i campi idrogeno obbligatori/opzionali
        const hydrogenInputs = hydrogenFields ? hydrogenFields.querySelectorAll('input, select') : [];
        hydrogenInputs.forEach(input => {
            if (showHydrogenFields) {
                if (input.name === 'hydrogen_storage_capacity') {
                    input.required = true;
                }
            } else {
                input.required = false;
            }
        });
        
        // Rendi i campi elettrici obbligatori/opzionali
        const electricInputs = electricFields ? electricFields.querySelectorAll('input, select') : [];
        electricInputs.forEach(input => {
            if (showElectricFields) {
                if (input.name === 'electric_power') {
                    input.required = true;
                }
            } else {
                input.required = false;
            }
        });
    }
    
    // Gestisci cambio tipo stazione
    stationTypeSelect.addEventListener('change', updateFieldsVisibility);
    
    // Gestisci cambio tipi carburante
    fuelTypeCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            // Assicurati che almeno un tipo sia selezionato
            const checkedBoxes = Array.from(fuelTypeCheckboxes).filter(cb => cb.checked);
            if (checkedBoxes.length === 0) {
                this.checked = true; // Mantieni almeno una selezione
            }
            updateFieldsVisibility();
        });
    });
    
    // Validazione aggiuntiva al submit
    document.querySelector('.auth-form').addEventListener('submit', function(e) {
        const selectedFuelTypes = Array.from(fuelTypeCheckboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);
        
        if (selectedFuelTypes.length === 0) {
            e.preventDefault();
            alert('Seleziona almeno un tipo di carburante');
            return false;
        }
        
        // Validazione campi elettrici
        if (selectedFuelTypes.includes('electric')) {
            const electricPower = document.querySelector('input[name="electric_power"]');
            if (electricPower && !electricPower.value) {
                e.preventDefault();
                alert('La potenza massima è obbligatoria per stazioni elettriche');
                electricPower.focus();
                return false;
            }
            
            // Verifica che almeno un connettore sia selezionato
            const connectorCheckboxes = document.querySelectorAll('input[id^="connector_types-"]:checked');
            if (connectorCheckboxes.length === 0) {
                e.preventDefault();
                alert('Seleziona almeno un tipo di connettore per stazioni elettriche');
                return false;
            }
        }
        
        // Validazione campi idrogeno
        if (selectedFuelTypes.includes('hydrogen')) {
            const storageCapacity = document.querySelector('input[name="hydrogen_storage_capacity"]');
            if (!storageCapacity.value) {
                e.preventDefault();
                alert('La capacità di stoccaggio idrogeno è obbligatoria per stazioni idrogeno');
                storageCapacity.focus();
                return false;
            }
        }
    });
    
    // Inizializza lo stato dei campi
    updateFieldsVisibility();
    
    // Geolocalizzazione automatica (opzionale)
    const getLocationBtn = document.createElement('button');
    getLocationBtn.type = 'button';
    getLocationBtn.className = 'btn btn-secondary btn-sm';
    getLocationBtn.innerHTML = '<i class="fas fa-map-marker-alt"></i> Usa la mia posizione';
    getLocationBtn.style.marginTop = '10px';
    
    // Aggiungi il bottone dopo il campo longitudine
    const longitudeField = document.querySelector('input[name="longitude"]');
    if (longitudeField && navigator.geolocation) {
        longitudeField.parentNode.appendChild(getLocationBtn);
        
        getLocationBtn.addEventListener('click', function() {
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Rilevamento...';
            
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    document.querySelector('input[name="latitude"]').value = position.coords.latitude.toFixed(6);
                    document.querySelector('input[name="longitude"]').value = position.coords.longitude.toFixed(6);
                    getLocationBtn.disabled = false;
                    getLocationBtn.innerHTML = '<i class="fas fa-check"></i> Posizione rilevata';
                },
                function(error) {
                    console.error('Errore geolocalizzazione:', error);
                    getLocationBtn.disabled = false;
                    getLocationBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Errore rilevamento';
                    alert('Impossibile rilevare la posizione. Inserisci manualmente le coordinate.');
                }
            );
        });
    }
});