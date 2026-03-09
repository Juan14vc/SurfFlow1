// Configuración de la URL de tu servidor en Render
const URL_API = "https://surfflow1.onrender.com/Servlet";

/**
 * Función principal para obtener las tablas desde Python (Flask)
 */
async function obtenerDatos() {
    const tbody = document.getElementById("lista-tablas");
    if (!tbody) return;

    try {
        // Mostramos un mensaje de carga mientras el servidor "despierta"
        tbody.innerHTML = '<tr><td colspan="6">Cargando datos desde la playa... 🌊</td></tr>';

        const respuesta = await fetch(`${URL_API}?accion=listar`);
        
        if (!respuesta.ok) throw new Error("Error en la respuesta del servidor");

        const datos = await respuesta.json();
        tbody.innerHTML = ""; // Limpiamos el mensaje de carga

        if (datos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">No hay tablas registradas en el inventario.</td></tr>';
            return;
        }

        datos.forEach(tabla => {
            // Determinamos la clase CSS según el estado para el diseño de las etiquetas
            const estadoClase = tabla.estado.toLowerCase().includes("uso") ? "en-uso" : "disponible";

            const fila = `
                <tr>
                    <td>${tabla.id}</td>
                    <td><strong>${tabla.nombre}</strong></td>
                    <td>${tabla.medida || 'N/A'}</td>
                    <td>${tabla.tipo || 'N/A'}</td>
                    <td>
                        <span class="status-badge ${estadoClase}">
                            ${tabla.estado}
                        </span>
                    </td>
                    <td>
                        <button class="btn-uso" onclick="gestionar(${tabla.id}, '${tabla.estado}')">
                            Gestionar ⚙️
                        </button>
                    </td>
                </tr>
            `;
            tbody.innerHTML += fila;
        });
    } catch (error) {
        console.error("Error al obtener datos:", error);
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="color: #e63946; padding: 20px;">
                    ❌ Error: El servidor no responde. <br>
                    <small>Es posible que el servidor de Render esté despertando. Reintenta en 20 segundos.</small>
                </td>
            </tr>`;
    }
}

/**
 * Función para gestionar una tabla individual (Alquiler)
 * @param {number} id - ID de la tabla
 * @param {string} estadoActual - Estado actual de la tabla
 */
async function gestionar(id, estadoActual) {
    // Si la tabla ya está en uso, podríamos avisar, pero aquí lanzamos el proceso de alquiler
    if (estadoActual.toLowerCase().includes("uso")) {
        alert("Esta tabla ya se encuentra alquilada actualmente.");
        return;
    }

    const cliente = prompt("Nombre del cliente para el alquiler:");
    if (!cliente) return; // Si cancela el prompt

    const monto = prompt("Monto pagado (Ej: 50):");
    if (!monto) return;

    try {
        // Limpiamos el monto por si ponen símbolos de moneda
        const montoLimpio = monto.replace(/[^0-9.]/g, '');
        
        const url = `${URL_API}?accion=insertar_reserva&cliente=${encodeURIComponent(cliente)}&monto=${montoLimpio}&tabla_id=${id}&comprobante=WebManual`;

        const res = await fetch(url);
        const data = await res.json();

        if (data.status === 'ok' || data.status === 'success') {
            alert("¡Registro exitoso! La tabla ahora está EN USO. 🏄‍♂️");
            obtenerDatos(); // Recargamos la tabla para ver el cambio de estado
        } else {
            alert("Hubo un problema: " + (data.message || "Error desconocido"));
        }
    } catch (error) {
        console.error("Error al gestionar:", error);
        alert("El servidor tardó mucho en responder. Intenta presionar Gestionar de nuevo.");
    }
}

// Ejecutar la carga de datos apenas la página esté lista
document.addEventListener("DOMContentLoaded", obtenerDatos);
