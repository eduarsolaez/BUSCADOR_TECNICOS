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
    fetchTrafoDetails(trafoId);
}

async function fetchTrafoDetails(trafoId) {
    const statusMsg = document.getElementById('statusMsg');

    try {
        const url = `api/details/${trafoId}.json`;
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error("No se encontró e archivo de detalle.");
        }

        const data = await response.json();
        renderResults(data);
        statusMsg.innerText = "";

    } catch (error) {
        console.error(error);
        statusMsg.innerText = "Error al cargar detalles del Transformador.";
    }
}

function renderResults(data) {
    const resultContainer = document.getElementById('resultContainer');

    // 1. Renderizar Info Trafo
    document.getElementById('t_codigo').innerText = data.CODIGO_TRANSFORMADOR || '-';
    document.getElementById('t_matricula_ct').innerText = data['MATRÍCULA CT'] || '-';
    document.getElementById('t_matricula_trafo').innerText = data['MATRÍCULA_TRANSFORMADOR'] || '-';
    document.getElementById('t_censo').innerText = data['MATRÍCULA_CENSO'] || '-';
    document.getElementById('t_direccion').innerText = data['DIRECCIÓN TRAFO'] || '-';
    document.getElementById('t_potencia').innerText = data['POTENCIA_NOMINAL'] || '-';
    document.getElementById('t_total_clientes').innerText = data['TOTAL_CLIENTES'] || '0';

    // Badge Levantar
    const badge = document.getElementById('levantarBadge');
    const status = data.LEVANTAR_STATUS;
    badge.innerText = status;
    badge.className = 'badge ' + (status === 'LEVANTAR' ? 'badge-danger' : 'badge-success');
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
