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
    const resultContainer = document.getElementById('resultContainer');

    // Limpiar estado
    statusMsg.innerText = "Buscando...";
    statusMsg.className = "status-msg";
    resultContainer.style.display = 'none';

    const query = input.value.trim().toUpperCase();
    if (!query) {
        statusMsg.innerText = "Por favor ingrese un término de búsqueda.";
        return;
    }

    if (!searchIndex) {
        statusMsg.innerText = "Cargando base de datos, intente en unos segundos...";
        await loadIndex();
        if (!searchIndex) return; // Si sigue fallando
    }

    const trafoId = searchIndex[query];

    if (!trafoId) {
        statusMsg.innerText = "No se encontraron resultados para: " + query;
        return;
    }

    // Si encontramos ID, buscamos el detalle
    fetchTrafoDetails(trafoId, query);
}

async function fetchTrafoDetails(trafoId, query) {
    const statusMsg = document.getElementById('statusMsg');

    try {
        const url = `api/details/${trafoId}.json`;
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error("No se encontró e archivo de detalle.");
        }

        const data = await response.json();
        renderResults(data, query);
        statusMsg.innerText = "";

    } catch (error) {
        console.error(error);
        statusMsg.innerText = "Error al cargar detalles del Transformador.";
    }
}

function renderResults(data, query) {
    const resultContainer = document.getElementById('resultContainer');

    // 1. Renderizar Info Trafo
    document.getElementById('t_codigo').innerText = data.CODIGO_TRANSFORMADOR || '-';
    document.getElementById('t_matricula_ct').innerText = data['MATRÍCULA CT'] || '-';
    document.getElementById('t_matricula_trafo').innerText = data['MATRÍCULA_TRANSFORMADOR'] || '-';
    document.getElementById('t_censo').innerText = data['MATRÍCULA_CENSO'] || '-';
    document.getElementById('t_direccion').innerText = data['DIRECCIÓN TRAFO'] || '-';
    document.getElementById('t_potencia').innerText = data['POTENCIA_NOMINAL'] || '-';
    document.getElementById('t_modelo').innerText = data['MODELO'] || '-';
    document.getElementById('t_tipo_ct').innerText = data['TIPO CT'] || '-';
    document.getElementById('t_tipo_conexion').innerText = data['TIPO CONEXION'] || '-';
    document.getElementById('t_total_clientes').innerText = data['TOTAL_CLIENTES'] || '0';

    // Link para Google Maps
    const mapsContainer = document.getElementById('mapsContainer');
    const mapsLink = document.getElementById('t_maps_link');

    // Validar si las coordenadas existen y no están vacías
    if (data.LATITUD && data.LONGITUD && String(data.LATITUD).trim() !== '' && String(data.LONGITUD).trim() !== '') {
        const lat = String(data.LATITUD).trim().replace(',', '.');
        const lon = String(data.LONGITUD).trim().replace(',', '.');
        // Usamos el formato /maps/place/ con el pin exacto y forzamos target _blank en el HTML
        mapsLink.href = `https://www.google.com/maps/place/${lat},${lon}/@${lat},${lon},16z?entry=ttu`;
        mapsContainer.style.display = 'block';
    } else {
        mapsContainer.style.display = 'none';
        mapsLink.href = '#';
    }

    // Mostrar Cliente Encontrado si aplica
    const foundClientContainer = document.getElementById('foundClientContainer');
    let foundClient = null;
    if (query && data.CLIENTES && data.CLIENTES.length > 0) {
        foundClient = data.CLIENTES.find(c =>
            (c.MEDIDOR && String(c.MEDIDOR).trim().toUpperCase() === query) ||
            (c.NIC && String(c.NIC).trim().toUpperCase() === query)
        );
    }

    if (foundClient) {
        document.getElementById('fc_nombre').innerText = foundClient['NOMBRE_CLIENTE'] || '-';
        document.getElementById('fc_medidor').innerText = foundClient['MEDIDOR'] || '-';
        document.getElementById('fc_niu').innerText = foundClient['NIU'] || '-';
        document.getElementById('fc_direccion').innerText = foundClient['DIRECCION_CLIENTE'] || '-';
        document.getElementById('fc_matricula_ct').innerText = foundClient['MATRÍCULA CT'] || '-';
        document.getElementById('fc_nis').innerText = foundClient['NIS_RAD_1'] || '-';
        document.getElementById('fc_nic').innerText = foundClient['NIC'] || '-';
        foundClientContainer.style.display = 'block';
    } else {
        foundClientContainer.style.display = 'none';
    }

    // Badge Levantar
    const badge = document.getElementById('levantarBadge');
    const status = data.LEVANTAR_STATUS;
    badge.innerText = status;
    badge.className = 'badge ' + (status === 'LEVANTAR' ? 'badge-success' : 'badge-danger');
    // Note: User logic says 'LEVANTAR' should probably be alert/danger or success? 
    // Usually 'LEVANTAR' implies work needed -> Danger/Warning? Or Success (found)?
    // Let's stick to Red for LEVANTAR (Attention needed) and Green for NO LEVANTAR.

    // 2. Renderizar Tabla Clientes
    const tbody = document.querySelector('#clientsTable tbody');
    tbody.innerHTML = ''; // Limpiar

    if (data.CLIENTES && data.CLIENTES.length > 0) {
        data.CLIENTES.forEach(cliente => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${cliente['NOMBRE_CLIENTE'] || ''}</td>
                <td>${cliente['MEDIDOR'] || ''}</td>
                <td>${cliente['NIU'] || ''}</td>
                <td>${cliente['DIRECCION_CLIENTE'] || ''}</td>
                <td>${cliente['MATRÍCULA CT'] || ''}</td>
                <td>${cliente['NIS_RAD_1'] || ''}</td>
                <td>${cliente['NIC'] || ''}</td>
            `;
            tbody.appendChild(tr);
        });
    } else {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td colspan="7" style="text-align:center;">No hay clientes registrados en este transformador.</td>`;
        tbody.appendChild(tr);
    }

    resultContainer.style.display = 'block';
}
