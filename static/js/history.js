// Alternar visualización de los eventos del bloque de historial
function toggleHistory(id) {
    document.getElementById(id).classList.toggle('hidden');
}

// Filtro dinámico en tiempo real del historial de maniobras
function filterHistory() {
    const input = document.getElementById('historySearch').value.toUpperCase();
    const items = document.getElementsByClassName('history-item');

    for (let i = 0; i < items.length; i++) {
        const name = items[i].getAttribute('data-name');
        const nomen = items[i].getAttribute('data-nomen');

        if (name || nomen) {
            if (name.toUpperCase().includes(input) || nomen.toUpperCase().includes(input)) {
                items[i].style.display = '';
            } else {
                items[i].style.display = 'none';
            }
        }
    }
}