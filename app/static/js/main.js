// main.js - JavaScript principale dell'applicazione

document.addEventListener('DOMContentLoaded', function() {
    // Gestione chiusura degli alert
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => {
                alert.style.display = 'none';
            }, 300);
        }, 5000);
    });

    // Inizializzazione header responsive
    const mobileBreakpoint = 768;
    function checkScreenSize() {
        if(window.innerWidth <= mobileBreakpoint) {
            document.body.classList.add('mobile');
        } else {
            document.body.classList.remove('mobile');
        }
    }

    // Esecuzione iniziale e al ridimensionamento
    checkScreenSize();
    window.addEventListener('resize', checkScreenSize);
});