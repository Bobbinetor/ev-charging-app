// auth.js - JavaScript per le pagine di autenticazione

document.addEventListener('DOMContentLoaded', function() {
    // Validazione form
    const forms = document.querySelectorAll('.auth-form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            let valid = true;
            
            // Validazione email
            const emailField = form.querySelector('input[type="email"]');
            if (emailField) {
                // Aggiornata regex per accettare email con underscore e numeri
                const emailRegex = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
                if (!emailRegex.test(emailField.value)) {
                    showError(emailField, 'Inserisci un indirizzo email valido');
                    valid = false;
                } else {
                    clearError(emailField);
                }
            }
            
            // Validazione password
            const passwordField = form.querySelector('input[name="password"]');
            if (passwordField && passwordField.value.length < 8) {
                showError(passwordField, 'La password deve contenere almeno 8 caratteri');
                valid = false;
            } else if (passwordField) {
                clearError(passwordField);
            }
            
            // Validazione conferma password
            const password2Field = form.querySelector('input[name="password2"]');
            if (password2Field && passwordField) {
                if (password2Field.value !== passwordField.value) {
                    showError(password2Field, 'Le password non coincidono');
                    valid = false;
                } else {
                    clearError(password2Field);
                }
            }
            
            // Validazione termini e condizioni
            const termsCheckbox = form.querySelector('input[name="accept_terms"]');
            if (termsCheckbox && !termsCheckbox.checked) {
                showError(termsCheckbox.parentNode, 'Devi accettare i termini e le condizioni');
                valid = false;
            } else if (termsCheckbox) {
                clearError(termsCheckbox.parentNode);
            }
            
            // Per il form stazione, validazione campi specifici
            if (form.getAttribute('action').includes('register_station')) {
                // Validazione coordinate
                const latField = form.querySelector('input[name="latitude"]');
                const lonField = form.querySelector('input[name="longitude"]');
                
                if (latField && lonField) {
                    const latRegex = /^(\+|-)?(?:90(?:(?:\.0{1,6})?)|(?:[0-9]|[1-8][0-9])(?:(?:\.[0-9]{1,6})?))$/;
                    const lonRegex = /^(\+|-)?(?:180(?:(?:\.0{1,6})?)|(?:[0-9]|[1-9][0-9]|1[0-7][0-9])(?:(?:\.[0-9]{1,6})?))$/;
                    
                    if (!latRegex.test(latField.value)) {
                        showError(latField, 'Inserisci una latitudine valida');
                        valid = false;
                    } else {
                        clearError(latField);
                    }
                    
                    if (!lonRegex.test(lonField.value)) {
                        showError(lonField, 'Inserisci una longitudine valida');
                        valid = false;
                    } else {
                        clearError(lonField);
                    }
                }
                
                // Validazione partita IVA
                const vatField = form.querySelector('input[name="vat_number"]');
                if (vatField) {
                    const vatRegex = /^[0-9]{11}$/;
                    if (!vatRegex.test(vatField.value)) {
                        showError(vatField, 'Inserisci una partita IVA valida (11 cifre)');
                        valid = false;
                    } else {
                        clearError(vatField);
                    }
                }
            }
            
            if (!valid) {
                e.preventDefault();
            }
        });
    });
    
    // Funzioni helper per mostrare e nascondere errori
    function showError(field, message) {
        // Trova o crea il contenitore degli errori
        let errorContainer = field.parentNode.querySelector('.error-message');
        if (!errorContainer) {
            errorContainer = document.createElement('div');
            errorContainer.className = 'error-message';
            field.parentNode.appendChild(errorContainer);
        }
        
        // Imposta il messaggio di errore
        errorContainer.innerHTML = `<span>${message}</span>`;
        field.classList.add('is-invalid');
    }
    
    function clearError(field) {
        const errorContainer = field.parentNode.querySelector('.error-message');
        if (errorContainer) {
            errorContainer.innerHTML = '';
        }
        field.classList.remove('is-invalid');
    }
    
    // Geolocalizzazione per la pagina di registrazione stazione
    if (document.querySelector('form[action*="register_station"]')) {
        const getLocationBtn = document.createElement('button');
        getLocationBtn.type = 'button';
        getLocationBtn.className = 'btn btn-secondary location-btn';
        getLocationBtn.innerHTML = '<i class="fas fa-map-marker-alt"></i> Usa posizione attuale';
        
        const latField = document.querySelector('input[name="latitude"]');
        const lonField = document.querySelector('input[name="longitude"]');
        
        if (latField && lonField) {
            const coordinatesContainer = lonField.closest('.form-row');
            coordinatesContainer.insertAdjacentElement('afterend', getLocationBtn);
            
            getLocationBtn.addEventListener('click', function() {
                if (navigator.geolocation) {
                    getLocationBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Rilevamento...';
                    getLocationBtn.disabled = true;
                    
                    navigator.geolocation.getCurrentPosition(
                        function(position) {
                            latField.value = position.coords.latitude.toFixed(6);
                            lonField.value = position.coords.longitude.toFixed(6);
                            
                            getLocationBtn.innerHTML = '<i class="fas fa-check"></i> Posizione rilevata';
                            getLocationBtn.classList.remove('btn-secondary');
                            getLocationBtn.classList.add('btn-success');
                            
                            // Ripristina il pulsante dopo 3 secondi
                            setTimeout(() => {
                                getLocationBtn.innerHTML = '<i class="fas fa-map-marker-alt"></i> Usa posizione attuale';
                                getLocationBtn.classList.remove('btn-success');
                                getLocationBtn.classList.add('btn-secondary');
                                getLocationBtn.disabled = false;
                            }, 3000);
                        },
                        function(error) {
                            getLocationBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Errore nel rilevamento';
                            getLocationBtn.classList.remove('btn-secondary');
                            getLocationBtn.classList.add('btn-danger');
                            
                            // Ripristina il pulsante dopo 3 secondi
                            setTimeout(() => {
                                getLocationBtn.innerHTML = '<i class="fas fa-map-marker-alt"></i> Usa posizione attuale';
                                getLocationBtn.classList.remove('btn-danger');
                                getLocationBtn.classList.add('btn-secondary');
                                getLocationBtn.disabled = false;
                            }, 3000);
                            
                            console.error('Errore di geolocalizzazione:', error);
                        }
                    );
                } else {
                    alert('La geolocalizzazione non è supportata dal tuo browser.');
                }
            });
        }
    }
});