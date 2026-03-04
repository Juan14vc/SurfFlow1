const URL_API = "http://localhost:5000/Servlet";

async function cargarTablas() {
    try {
        const res = await fetch(`${URL_API}?accion=listar`);
        const datos = await res.json();
        const tbody = document.getElementById("tabla-gestion");
        tbody.innerHTML = "";

        datos.forEach(tabla => {
            const claseEstado = tabla.estado.toLowerCase().replace(/\s+/g, "-");
            
            tbody.innerHTML += `
                <tr>
                    <td>${tabla.id}</td>
                    <td><strong>${tabla.nombre}</strong></td>
                    <td><span class="status-badge ${claseEstado}">${tabla.estado}</span></td>
                    <td>
                        <select class="select-gestion" onchange="manejarCambio(${tabla.id}, this.value)">
                            <option value="" disabled selected>Cambiar estado...</option>
                            <option value="Disponible">Disponible 🟢</option>
                            <option value="En Uso">En Uso 🟡 (Alquilar)</option>
                            <option value="Mantenimiento">Mantenimiento 🔴</option>
                        </select>
                    </td>
                </tr>`;
        });
    } catch (e) { console.error("Error al cargar", e); }
}

async function manejarCambio(id, nuevoEstado) {
    if (nuevoEstado === "En Uso") {
        // AQUÍ ESTABA EL ERROR: Ahora mandamos a reserva.html directamente
        window.location.href = `reserva.html?id=${id}`;
    } else {
        if (confirm(`¿Mover tabla #${id} a ${nuevoEstado}?`)) {
            const res = await fetch(`${URL_API}?accion=actualizar_estado&id=${id}&estado=${nuevoEstado}`);
            const data = await res.json();
            if (data.status === "ok") {
                alert("✅ Estado actualizado");
                cargarTablas();
            }
        }
    }
}

document.addEventListener("DOMContentLoaded", cargarTablas);