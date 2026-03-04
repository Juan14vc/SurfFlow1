// app.js corregido para conectar con Flask (Python) en VS Code
const URL_API = "http://localhost:5000/Servlet"; // Cambiamos 8080 por 5000

async function obtenerDatos() {
    try {
        // Añadimos el parámetro accion=listar para que Python sepa qué hacer
        const respuesta = await fetch(`${URL_API}?accion=listar`);
        const datos = await respuesta.json();
        const tbody = document.getElementById("lista-tablas");
        
        if (!tbody) return; // Seguridad por si no existe el elemento
        tbody.innerHTML = ""; 

        datos.forEach(tabla => {
            const fila = `
                <tr>
                    <td>${tabla.id}</td>
                    <td>${tabla.nombre}</td>
                    <td>${tabla.medida || 'N/A'}</td>
                    <td>${tabla.tipo || 'N/A'}</td>
                    <td>
                        <span class="status-badge ${tabla.estado.toLowerCase().replace(/\s+/g, "-")}">
                            ${tabla.estado}
                        </span>
                    </td>
                    <td>
                        <button class="btn-uso" onclick="gestionar(${tabla.id})">Gestionar</button>
                    </td>
                </tr>
            `;
            tbody.innerHTML += fila;
        });
    } catch (error) {
        console.error("Error:", error);
        const errorMsg = '<tr><td colspan="6">❌ Error al conectar con el servidor Python.</td></tr>';
        document.getElementById("lista-tablas").innerHTML = errorMsg;
    }
}

function gestionar(id) {
    // Redirige a la nueva ventana de gestión pasando el ID
    window.location.href = `gestion_individual.html?id=${id}`;
}
document.addEventListener("DOMContentLoaded", obtenerDatos);
