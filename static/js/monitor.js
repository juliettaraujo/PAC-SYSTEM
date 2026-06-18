// BUSCADOR EN TIEMPO REAL DEL MONITOR PRINCIPAL
let currentStatusFilter = 'todos';
let currentSearchTerm = '';

// Función ejecutada al hacer click en cualquier pestaña
function filterByStatus(status, buttonElement) {
    currentStatusFilter = status.toLowerCase();
    
    // Resetear estilos visuales de todos los botones de pestañas
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('bg-blue-600', 'text-white', 'shadow-sm');
        btn.classList.add('text-slate-600', 'hover:bg-slate-100');
    });
    
    // Activar visualmente el botón seleccionado
    buttonElement.classList.add('bg-blue-600', 'text-white', 'shadow-sm');
    buttonElement.classList.remove('text-slate-600', 'hover:bg-slate-100');

    // Aplicar la lógica combinada
    applyCombinedFilters();
}

// Escuchador de eventos para la barra de búsqueda existente
document.getElementById("searchCircuit").addEventListener("keyup", function() {
    currentSearchTerm = this.value.toLowerCase();
    applyCombinedFilters();
});

// Función auxiliar para calcular el tiempo transcurrido en ms (Para ordenamiento)
function getOutageDurationMs(card) {
    const startTimeStr = card.getAttribute('data-start-time');
    if (!startTimeStr || startTimeStr === '--:--' || startTimeStr === 'None' || startTimeStr === '') {
        return 0;
    }
    const parts = startTimeStr.split(':');
    if (parts.length !== 2) return 0;

    const now = new Date();
    const startTime = new Date();
    startTime.setHours(parseInt(parts[0], 10), parseInt(parts[1], 10), 0, 0);

    if (now < startTime) {
        startTime.setDate(startTime.getDate() - 1); // Corrección para turnos nocturnos
    }
    return now - startTime;
}

// MOTOR DE FILTRADO COMBINADO INTEGRADO
function applyCombinedFilters() {
    let cards = document.querySelectorAll(".circuit-card");
    const blocksGrid = document.getElementById("blocks-grid");
    const unifiedView = document.getElementById("unified-view-container");
    const unifiedHolder = document.getElementById("unified-circuits-holder");
    const unifiedTitle = document.getElementById("unified-title");
    const unifiedIndicator = document.getElementById("unified-indicator");
    const unifiedHeader = document.getElementById("unified-header");

    // Contenedores para la lista de circuitos recuperados
    const fsContainer = document.getElementById("fs-chronological-container");
    const fsListHolder = document.getElementById("fs-list-holder");

    // Registro dinámico para saber qué bloques conservan circuitos visibles
    const activeBlocks = {};

    // ==========================================
    // CASO 1: MODO VISTA GENERAL (TODOS)
    // ==========================================
    if (currentStatusFilter === 'todos') {
        if (blocksGrid) blocksGrid.classList.remove('hidden');
        if (unifiedView) unifiedView.classList.add('hidden');
        if (fsContainer) fsContainer.classList.add('hidden'); 

        cards.forEach(card => {
            let searchMatch = card.innerText.toLowerCase().includes(currentSearchTerm);
            const badge = card.querySelector('.block-badge');
            if (badge) badge.classList.add('hidden');

            // Retornar físicamente el circuito a su bloque correspondiente
            const originalBlock = card.getAttribute('data-block');
            const originalContainer = document.getElementById(`original-block-${originalBlock}`);
            if (originalContainer && card.parentNode !== originalContainer) {
                originalContainer.appendChild(card);
            }

            // Evaluar coincidencia con la barra de búsqueda de texto
            if (searchMatch) {
                card.style.display = "";
                if (originalBlock) {
                    activeBlocks[originalBlock] = true;
                }
            } else {
                card.style.display = "none";
            }
        });

        // Ocultar bloques vacíos por completo
        const blockContainers = document.querySelectorAll("[id^='original-block-']");
        blockContainers.forEach(container => {
            const blockName = container.id.replace('original-block-', '');
            const parentCard = container.closest('.corp-card');
            
            if (parentCard) {
                if (activeBlocks[blockName]) {
                    parentCard.classList.remove('hidden');
                } else {
                    parentCard.classList.add('hidden');
                }
            }
        });

    // ==========================================
    // CASO 2: PESTAÑA ACTIVOS (CIRCUITOS EN LINEA)
    // ==========================================
    } else if (currentStatusFilter === 'activo') {
        if (blocksGrid) blocksGrid.classList.add('hidden');
        if (fsContainer) fsContainer.classList.add('hidden'); 
        if (unifiedView) unifiedView.classList.remove('hidden');

        if (unifiedTitle && unifiedIndicator && unifiedHeader) {
            unifiedTitle.textContent = `Circuitos en ACTIVOS`;
            unifiedIndicator.className = "w-2 h-8 rounded-full bg-green-500";
            unifiedHeader.className = "table-header px-4 py-3 flex items-center justify-between flex-shrink-0 bg-slate-900 text-white rounded-t-xl border-b-2 border-green-500";
        }

        const matchingCards = Array.from(cards).filter(card => {
            let text = card.innerText.toLowerCase();
            let cardStatus = (card.getAttribute("data-status") || "").toLowerCase();
            return cardStatus === 'activo' && text.includes(currentSearchTerm);
        });

        cards.forEach(card => card.style.display = "none");

        if (unifiedHolder) {
            unifiedHolder.innerHTML = '';
            matchingCards.forEach(card => {
                const badge = card.querySelector('.block-badge');
                if (badge) badge.classList.remove('hidden');

                card.style.display = "";
                unifiedHolder.appendChild(card);
            });
        }
        
        if (matchingCards.length === 0) {
            unifiedView.classList.add('hidden');
        } else {
            unifiedView.classList.remove('hidden');
        }

    // ==========================================
    // CASO 3: PESTAÑA CRONOLÓGICA (CIRCUITOS RECUPERADOS ANTERIORMENTE)
    // ==========================================
    } else if (currentStatusFilter === 'fuera_servicio') {
        if (blocksGrid) blocksGrid.classList.add('hidden');
        if (unifiedView) unifiedView.classList.add('hidden');
        if (fsContainer) fsContainer.classList.remove('hidden'); 

        // FILTRADO ESTRICTO: Estatus ACTIVO y que posea una hora de cierre válida (formato HH:MM)
        const matchingCards = Array.from(cards).filter(card => {
            let text = card.innerText.toLowerCase();
            let cardStatus = (card.getAttribute("data-status") || "").toLowerCase();
            let endTime = (card.getAttribute("data-end-time") || "").trim();
            
            const hasValidTimeFormat = /^\d{2}:\d{2}$/.test(endTime);
            const isRecovered = (cardStatus === 'activo' && hasValidTimeFormat);
            
            return isRecovered && text.includes(currentSearchTerm);
        });

        // ORDENAMIENTO: El recuperado más reciente arriba (Descendente)
        matchingCards.sort((a, b) => {
            let timeA = a.getAttribute("data-end-time") || "";
            let timeB = b.getAttribute("data-end-time") || "";
            return timeB.localeCompare(timeA);
        });

        // Ocultar del flujo principal
        cards.forEach(card => card.style.display = "none");

        if (fsListHolder) {
            fsListHolder.innerHTML = ''; 

            if (matchingCards.length === 0) {
                fsListHolder.innerHTML = `
                    <div class="text-center py-10 text-slate-400 font-bold text-sm bg-white rounded-xl border border-dashed border-slate-200">
                        📋 No se han registrado circuitos recuperados en este periodo.
                    </div>`;
            } else {
                matchingCards.forEach(card => {
                    const badge = card.querySelector('.block-badge');
                    if (badge) badge.classList.remove('hidden'); 

                    card.style.display = "";
                    fsListHolder.appendChild(card);
                });
            }
        }

    // ==========================================
    // CASO 4: PESTAÑAS FILTRADAS (PAC, FALLA, MANTENIMIENTO)
    // ==========================================
    } else {
        if (blocksGrid) blocksGrid.classList.add('hidden');
        if (fsContainer) fsContainer.classList.add('hidden'); 
        if (unifiedView) unifiedView.classList.remove('hidden');

        if (unifiedTitle && unifiedIndicator && unifiedHeader) {
            unifiedTitle.textContent = `Circuitos en ${currentStatusFilter.toUpperCase()}`;
            
            if (currentStatusFilter === 'pac') {
                unifiedIndicator.className = "w-2 h-8 rounded-full bg-blue-400";
                unifiedHeader.className = "table-header px-4 py-3 flex items-center justify-between flex-shrink-0 bg-slate-900 text-white rounded-t-xl border-b-2 border-blue-500";
            } else if (currentStatusFilter === 'falla') {
                unifiedIndicator.className = "w-2 h-8 rounded-full bg-red-500";
                unifiedHeader.className = "table-header px-4 py-3 flex items-center justify-between flex-shrink-0 bg-slate-900 text-white rounded-t-xl border-b-2 border-red-600";
            } else if (currentStatusFilter === 'mantenimiento') {
                unifiedIndicator.className = "w-2 h-8 rounded-full bg-amber-500";
                unifiedHeader.className = "table-header px-4 py-3 flex items-center justify-between flex-shrink-0 bg-slate-900 text-white rounded-t-xl border-b-2 border-amber-500";
            }
        }

        const matchingCards = Array.from(cards).filter(card => {
            let text = card.innerText.toLowerCase();
            let cardStatus = (card.getAttribute("data-status") || "").toLowerCase();
            return cardStatus === currentStatusFilter && text.includes(currentSearchTerm);
        });

        matchingCards.sort((a, b) => {
            return getOutageDurationMs(b) - getOutageDurationMs(a);
        });

        cards.forEach(card => card.style.display = "none");

        if (unifiedHolder) {
            unifiedHolder.innerHTML = '';
            matchingCards.forEach(card => {
                const badge = card.querySelector('.block-badge');
                if (badge) badge.classList.remove('hidden');

                card.style.display = "";
                unifiedHolder.appendChild(card);
            });
        }
        
        if (matchingCards.length === 0) {
            unifiedView.classList.add('hidden');
        } else {
            unifiedView.classList.remove('hidden');
        }
    }
}

// RESTRICCIÓN: No permitir hora de cierre mayor a la hora actual del sistema
function validateFutureTime(input) {
    if (!input.value) return;

    const now = new Date();
    const currentHH = String(now.getHours()).padStart(2, '0');
    const currentMM = String(now.getMinutes()).padStart(2, '0');
    const currentTime = `${currentHH}:${currentMM}`;

    if (input.value > currentTime) {
        alert("Error: La hora de cierre (" + input.value + ") no puede ser superior a la hora actual (" + currentTime + ").");
        input.value = ""; 
    }
}

// CONTROLADOR DEL MODAL DE CAMBIO DE ESTADO
document.addEventListener('DOMContentLoaded', function() {
    const monitorForms = document.querySelectorAll('.monitor-form');
    const modal = document.getElementById('confirmModal');
    const modalMessage = document.getElementById('modalMessage');
    const confirmBtn = document.getElementById('confirmBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    
    let formToSubmit = null; 

    monitorForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const originalStatus = form.getAttribute('data-original-status');
            const newStatus = form.querySelector('select[name="status"]').value;
            const estadosCriticos = ['PAC', 'MANTENIMIENTO', 'FALLA'];

            if (estadosCriticos.includes(originalStatus) && originalStatus !== newStatus) {
                e.preventDefault(); 
                formToSubmit = form; 

                modalMessage.innerHTML = `El circuito se encuentra actualmente bajo el estatus 
                    <span class="px-1.5 py-0.5 rounded-md bg-red-100 text-red-700 font-black font-mono">${originalStatus}</span>. 
                    ¿Estás seguro de que deseas cambiarlo a 
                    <span class="px-1.5 py-0.5 rounded-md bg-green-100 text-green-700 font-black font-mono">${newStatus}</span>? 
                    Verifica que las maniobras operativas en campo hayan concluido de forma segura.`;

                modal.classList.remove('hidden');
                modal.classList.add('flex');
                setTimeout(() => {
                    modal.classList.remove('opacity-0');
                    modal.querySelector('div').classList.remove('scale-95');
                }, 10);
            }
        });
    });

    function closeModal() {
        modal.classList.add('opacity-0');
        modal.querySelector('div').classList.add('scale-95');
        setTimeout(() => {
            modal.classList.remove('flex');
            modal.classList.add('hidden');
            formToSubmit = null; 
        }, 300);
    }

    cancelBtn.addEventListener('click', closeModal);
    confirmBtn.addEventListener('click', function() {
        if (formToSubmit) {
            formToSubmit.submit(); 
        }
    });

    modal.addEventListener('click', function(e) {
        if (e.target === modal) closeModal();
    });
});

// MOTOR DEL CRONÓMETRO EN TIEMPO REAL
function updateLiveChronometers() {
    const chronometers = document.querySelectorAll('.realtime-chrono');
    const now = new Date();

    chronometers.forEach(chrono => {
        const startTimeStr = chrono.getAttribute('data-start-time'); 
        
        if (!startTimeStr || startTimeStr === 'None' || startTimeStr === '' || startTimeStr === '--:--') {
            chrono.textContent = '--:--:--';
            return;
        }

        const timeParts = startTimeStr.split(':');
        const startTime = new Date();
        startTime.setHours(parseInt(timeParts[0], 10));
        startTime.setMinutes(parseInt(timeParts[1], 10));
        startTime.setSeconds(0);
        startTime.setMilliseconds(0);

        if (now < startTime) {
            startTime.setDate(startTime.getDate() - 1);
        }

        const diffMs = now - startTime;
        const diffSecs = Math.floor(diffMs / 1000);
        const hours = Math.floor(diffSecs / 3600);
        const minutes = Math.floor((diffSecs % 3600) / 60);
        const seconds = diffSecs % 60;

        const formattedTime = 
            String(hours).padStart(2, '0') + ':' + 
            String(minutes).padStart(2, '0') + ':' + 
            String(seconds).padStart(2, '0');

        chrono.textContent = formattedTime;
    });
}

// Inicializadores automáticos
setInterval(updateLiveChronometers, 1000);
document.addEventListener('DOMContentLoaded', updateLiveChronometers);