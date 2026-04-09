// Variables globales
let searchIndex = null;
const INDEX_URL = 'api/index/search_index.json';

// Cargar el índice al iniciar (o podemos hacerlo lazy-load al primer search)
async function loadIndex() {
    try {
        const response = await fetch(INDEX_URL);
        if (!response.ok) throw new Error("No se pudo cargar el índice de búsqueda.");
        searchIndex = await response.json();
        console.log("Índice cargado correctamente.");
    } catch (error) {
        console.error("Error cargando índice:", error);
        document.getElementById('statusMsg').innerText = "Error: No se pudo cargar la base de datos de búsqueda.";
    }
}

// Iniciar carga del índice
loadIndex();

function handleEnter(e) {
    if (e.key === 'Enter') performSearch();
}

async function performSearch() {
    const input = document.getElementById('searchInput');
    const statusMsg = document.getElementById('statusMsg');
    const bankAlert = document.getElementById('bankAlert');
    const resultContainer = document.getElementById('resultContainer');

    // Limpiar estado
    statusMsg.innerText = "Buscando...";
    statusMsg.className = "status-msg";
    resultContainer.style.display = 'none';
    resultContainer.innerHTML = ''; // Limpiar resultados previos
    bankAlert.style.display = 'none';

    const query = input.value.trim().toUpperCase();
    if (!query) {
        statusMsg.innerText = "Por favor ingrese un término de búsqueda.";
        return;
    }

    if (!searchIndex) {
        statusMsg.innerText = "Cargando base de datos, intente en unos segundos...";
        await loadIndex();
        if (!searchIndex) return;
    }

    const searchResult = searchIndex[query];

    if (!searchResult) {
        statusMsg.innerText = "No se encontraron resultados para: " + query;
        return;
    }

    // Convertir a array si es un ID único
    const trafoIds = Array.isArray(searchResult) ? searchResult : [searchResult];
    
    // Mostrar alerta de banco si hay más de uno
    if (trafoIds.length > 1) {
        bankAlert.style.display = 'block';
    }

    // Buscar detalles para todos los IDs
    fetchMultipleTrafoDetails(trafoIds, query);
}

async function fetchMultipleTrafoDetails(trafoIds, query) {
    const statusMsg = document.getElementById('statusMsg');
    const resultContainer = document.getElementById('resultContainer');

    try {
        const promises = trafoIds.map(id => fetch(`api/details/${id}.json`).then(r => {
            if (!r.ok) throw new Error(`No se encontró el detalle ${id}`);
            return r.json();
        }));

        const results = await Promise.all(promises);
        
        results.forEach(data => {
            renderTrafoResult(data, query);
        });

        statusMsg.innerText = "";
        resultContainer.style.display = 'block';

    } catch (error) {
        console.error(error);
        statusMsg.innerText = "Error al cargar detalles de los Transformadores.";
    }
}

function renderTrafoResult(data, query) {
    const resultContainer = document.getElementById('resultContainer');

    // Crear bloque de resultado
    const resultBlock = document.createElement('div');
    resultBlock.className = 'result-block';

    // 1. Info Trafo
    const mapsLat = data.LATITUD && String(data.LATITUD).trim() !== '' ? String(data.LATITUD).trim().replace(',', '.') : null;
    const mapsLon = data.LONGITUD && String(data.LONGITUD).trim() !== '' ? String(data.LONGITUD).trim().replace(',', '.') : null;
    const mapsUrl = (mapsLat && mapsLon) ? `https://www.google.com/maps/place/${mapsLat},${mapsLon}/@${mapsLat},${mapsLon},16z?entry=ttu` : '#';
    const mapsDisplay = (mapsLat && mapsLon) ? 'block' : 'none';

    const status = data.LEVANTAR_STATUS || 'DESCONOCIDO';
    const badgeClass = status === 'LEVANTAR' ? 'badge-danger' : 'badge-success';

    // Cliente Encontrado logic
    let foundClientHtml = '';
    if (query && data.CLIENTES && data.CLIENTES.length > 0) {
        const foundClient = data.CLIENTES.find(c => {
            const medidorFull = c.MEDIDOR ? String(c.MEDIDOR).trim().toUpperCase() : '';
            const medidorBase = medidorFull.includes('-') ? medidorFull.split('-')[0] : medidorFull;
            const nicStr = c.NIC ? String(c.NIC).trim().toUpperCase() : '';
            return medidorFull === query || medidorBase === query || nicStr === query;
        });

        if (foundClient) {
            foundClientHtml = `
                <div class="card client-found-card" style="border: 2px solid #28a745; background-color: #f4fff4;">
                    <div class="card-header" style="background-color: #28a745; color: white;">
                        <h2>Cliente Encontrado</h2>
                    </div>
                    <div class="card-body">
                        <div class="info-row"><strong>Nombre:</strong> <span>${foundClient['NOMBRE_CLIENTE'] || '-'}</span></div>
                        <div class="info-row"><strong>Medidor:</strong> <span>${foundClient['MEDIDOR'] || '-'}</span></div>
                        <div class="info-row"><strong>NIU:</strong> <span>${foundClient['NIU'] || '-'}</span></div>
                        <div class="info-row"><strong>Dirección:</strong> <span>${foundClient['DIRECCION_CLIENTE'] || '-'}</span></div>
                        <div class="info-row"><strong>Matrícula CT:</strong> <span>${foundClient['MATRÍCULA CT'] || '-'}</span></div>
                        <div class="info-row"><strong>NIS_RAD_1:</strong> <span>${foundClient['NIS_RAD_1'] || '-'}</span></div>
                        <div class="info-row"><strong>NIC:</strong> <span>${foundClient['NIC'] || '-'}</span></div>
                    </div>
                </div>
            `;
        }
    }

    // Clientes Table rows
    let clientRowsHtml = '';
    if (data.CLIENTES && data.CLIENTES.length > 0) {
        clientRowsHtml = data.CLIENTES.map(cliente => `
            <tr>
                <td>${cliente['NOMBRE_CLIENTE'] || ''}</td>
                <td>${cliente['MEDIDOR'] || ''}</td>
                <td>${cliente['NIU'] || ''}</td>
                <td>${cliente['DIRECCION_CLIENTE'] || ''}</td>
                <td>${cliente['MATRÍCULA CT'] || ''}</td>
                <td>${cliente['NIS_RAD_1'] || ''}</td>
                <td>${cliente['NIC'] || ''}</td>
            </tr>
        `).join('');
    } else {
        clientRowsHtml = `<tr><td colspan="7" style="text-align:center;">No hay clientes registrados en este transformador.</td></tr>`;
    }

    resultBlock.innerHTML = `
        <div class="card trafo-card">
            <div class="card-header">
                <h2>Información del Transformador</h2>
                <span class="badge ${badgeClass}">${status}</span>
            </div>
            <div class="card-body">
                <div class="info-row"><strong>Código:</strong> <span>${data.CODIGO_TRANSFORMADOR || '-'}</span></div>
                <div class="info-row"><strong>Matrícula CT:</strong> <span>${data['MATRÍCULA CT'] || '-'}</span></div>
                <div class="info-row"><strong>Matrícula Trafo:</strong> <span>${data['MATRÍCULA_TRANSFORMADOR'] || '-'}</span></div>
                <div class="info-row"><strong>QR:</strong> <span>${data['MATRÍCULA_CENSO'] || '-'}</span></div>
                <div class="info-row"><strong>Dirección:</strong> <span>${data['DIRECCIÓN TRAFO'] || '-'}</span></div>
                <div class="info-row"><strong>Potencia:</strong> <span>${data['POTENCIA_NOMINAL'] || '-'}</span></div>
                <div class="info-row"><strong>Marca:</strong> <span>${data['MODELO'] || '-'}</span></div>
                <div class="info-row"><strong>TIPO CT:</strong> <span>${data['TIPO CT'] || '-'}</span></div>
                <div class="info-row"><strong>Tipo conexión:</strong> <span>${data['TIPO CONEXION'] || '-'}</span></div>
                <div class="info-row"><strong>Total Clientes:</strong> <span>${data['TOTAL_CLIENTES'] || '0'}</span></div>
                <div style="display: ${mapsDisplay}; text-align: center; margin-top: 15px; margin-bottom: 5px;">
                    <a href="${mapsUrl}" target="_blank" rel="noopener noreferrer" class="maps-btn">
                        📍 Ver en Google Maps
                    </a>
                    <button onclick="showMap(${mapsLat}, ${mapsLon}, '${data.CODIGO_TRANSFORMADOR}', '${data['MATRÍCULA CT']}')" class="maps-btn map-view-btn">
                        🗺️ Ver Mapa
                    </button>
                </div>
            </div>
        </div>

        ${foundClientHtml}

        <div class="card clients-card">
            <div class="card-header">
                <h2>Clientes Asociados</h2>
            </div>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Nombre</th>
                            <th>Medidor</th>
                            <th>NIU</th>
                            <th>Dirección</th>
                            <th>Matrícula CT</th>
                            <th>NIS_RAD_1</th>
                            <th>NIC</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${clientRowsHtml}
                    </tbody>
                </table>
            </div>
        </div>
    `;

    resultContainer.appendChild(resultBlock);
}

// ==========================================
// Lógica de Mapa Interactivo (Leaflet)
// ==========================================
let map = null;
let markers = [];

function showMap(lat, lon, originalId, matriculaCt) {
    const modal = document.getElementById('mapModal');
    modal.style.display = 'block';

    if (!map) {
        initMap(lat, lon);
    } else {
        map.setView([lat, lon], 17);
    }

    loadNearbyTrafos(lat, lon, originalId, matriculaCt);
    
    // Forzar redibujado de Leaflet (necesario si el contenedor estaba oculto)
    setTimeout(() => {
        map.invalidateSize();
    }, 200);
}

function closeMap() {
    document.getElementById('mapModal').style.display = 'none';
}

function initMap(lat, lon) {
    map = L.map('map').setView([lat, lon], 17);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
}

async function loadNearbyTrafos(targetLat, targetLon, targetId, targetCt) {
    // Limpiar marcadores previos
    markers.forEach(m => map.removeLayer(m));
    markers = [];

    // Definir radio de búsqueda en grados aprox para las celdas (0.01)
    const gridLat = Math.round(targetLat * 100) / 100;
    const gridLon = Math.round(targetLon * 100) / 100;

    // Cargar celda actual y 8 vecinas para no perder puntos en los bordes
    const cellCoords = [];
    for (let i = -1; i <= 1; i++) {
        for (let j = -1; j <= 1; j++) {
            cellCoords.push({
                lat: (parseFloat(gridLat) + i * 0.01).toFixed(2),
                lon: (parseFloat(gridLon) + j * 0.01).toFixed(2)
            });
        }
    }

    const promises = cellCoords.map(c => 
        fetch(`api/map/tile_${c.lat}_${c.lon}.json`)
        .then(r => r.ok ? r.json() : [])
        .catch(() => [])
    );

    try {
        const results = await Promise.all(promises);
        const allTrafos = results.flat();

        allTrafos.forEach(trafo => {
            const dist = calculateDistance(targetLat, targetLon, trafo.lat, trafo.lon);
            
            // Solo mostrar si está a menos de 400m (margen extra sobre los 300m pedidos)
            if (dist <= 400) {
                renderMarker(trafo, targetId, targetCt);
            }
        });
    } catch (e) {
        console.error("Error cargando índice espacial:", e);
    }
}

function renderMarker(trafo, targetId, targetCt) {
    const isTarget = (trafo.id === targetId);
    const isBank = (trafo.ct && trafo.ct === targetCt && !isTarget);
    
    // Determinar color
    let color = '#6c757d'; // Gris por defecto
    let weight = 1;
    let radius = 6;
    let zIndex = 100;

    if (isTarget) {
        color = '#007bff'; // Azul para el objetivo
        weight = 3;
        radius = 10;
        zIndex = 1000;
    } else if (isBank) {
        color = '#ffc107'; // Amarillo para banco
        weight = 2;
        radius = 8;
        zIndex = 500;
    }

    const marker = L.circleMarker([trafo.lat, trafo.lon], {
        radius: radius,
        fillColor: color,
        color: isTarget ? '#fff' : color,
        weight: weight,
        opacity: 1,
        fillOpacity: 0.8
    }).addTo(map);

    marker.bindPopup(`
        <strong>Trafo: ${trafo.id}</strong><br>
        CT: ${trafo.ct}<br>
        Status: ${trafo.status}<br>
        <button onclick="closeMap(); document.getElementById('searchInput').value='${trafo.id}'; performSearch();" 
                style="margin-top:5px; padding:3px 8px; font-size:11px; cursor:pointer;">
            Ver Detalles
        </button>
    `);
    
    if (isTarget) marker.openPopup();

    markers.push(marker);
}

// Distancia en metros (Haversine)
function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371e3; // Radio de la tierra 
    const φ1 = lat1 * Math.PI/180;
    const φ2 = lat2 * Math.PI/180;
    const Δφ = (lat2-lat1) * Math.PI/180;
    const Δλ = (lon2-lon1) * Math.PI/180;

    const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ/2) * Math.sin(Δλ/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

    return R * c; 
}
