// app.js - dashboard de tablas (requiere api.js cargado antes)
const alertados = new Set();

function celdaTiempo(t) {
    if (t.estado === "En Uso" && t.hora_fin) {
        return `<div class="tiempo-pagado">Pagó: ${fmtMin(t.minutos)}</div>
                <div class="timer" data-fin="${t.hora_fin}" data-nombre="${esc(t.nombre)}" data-cliente="${esc(t.cliente)}">...</div>`;
    }
    if (t.en_clase) return "👥 En clase";
    return "—";
}

function filaTabla(t) {
    const claseEstado = t.estado.toLowerCase().replace(/\s+/g, "-");
    const claseUso = t.uso === "Clases" ? "uso-clases" : "uso-alquiler";
    return `
        <tr>
            <td>${t.id}</td>
            <td>${esc(t.nombre)}</td>
            <td>${esc(t.medida || "N/A")}</td>
            <td>${esc(t.tipo || "N/A")}</td>
            <td><span class="uso-badge ${claseUso}">${esc(t.uso)}</span></td>
            <td><span class="status-badge ${claseEstado}">${esc(t.estado)}</span></td>
            <td>${celdaTiempo(t)}</td>
            <td><button class="btn-uso" onclick="gestionar(${t.id})">Gestionar</button></td>
        </tr>`;
}

async function obtenerDatos() {
    const tbody = document.getElementById("lista-tablas");
    if (!tbody) return;
    try {
        const datos = await llamar({ accion: "listar" });
        if (!Array.isArray(datos)) throw new Error("Respuesta inesperada del servidor");
        if (datos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8">Aún no hay tablas. Agrega la primera arriba 🏄‍♂️</td></tr>';
            return;
        }
        tbody.innerHTML = datos.map(filaTabla).join("");
        actualizarTemporizadores();
    } catch (error) {
        console.error("Error:", error);
        tbody.innerHTML = '<tr><td colspan="8">❌ No se pudo conectar con el servidor. Si recién abriste la página, espera unos segundos y recarga.</td></tr>';
    }
}

function pitar() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        osc.frequency.value = 880;
        osc.connect(ctx.destination);
        osc.start();
        setTimeout(() => { osc.stop(); ctx.close(); }, 400);
    } catch (e) { /* el navegador puede bloquear el sonido hasta que se toque la página */ }
}

function actualizarTemporizadores() {
    const excedidos = [];
    document.querySelectorAll(".timer").forEach(el => {
        const restante = Number(el.dataset.fin) * 1000 - Date.now();
        if (restante >= 0) {
            el.textContent = `⏱️ Restan ${reloj(restante)}`;
            el.className = "timer " + (restante <= 5 * 60 * 1000 ? "por-vencer" : "en-tiempo");
        } else {
            el.textContent = `⚠️ Excedido +${reloj(-restante)}`;
            el.className = "timer excedido";
            const detalle = el.dataset.nombre + (el.dataset.cliente ? ` (${el.dataset.cliente})` : "");
            excedidos.push(detalle);
            const clave = el.dataset.fin + el.dataset.nombre;
            if (!alertados.has(clave)) {
                alertados.add(clave);
                pitar();
            }
        }
    });
    const banner = document.getElementById("alerta-tiempo");
    if (banner) {
        if (excedidos.length) {
            banner.style.display = "block";
            banner.innerHTML = "⚠️ <strong>Tiempo excedido:</strong> " + excedidos.map(esc).join(" · ");
        } else {
            banner.style.display = "none";
        }
    }
}

function gestionar(id) {
    window.location.href = `gestion_individual.html?id=${id}`;
}

function cerrarSesion() {
    localStorage.clear();
    window.location.href = "index.html";
}

document.addEventListener("DOMContentLoaded", obtenerDatos);
setInterval(actualizarTemporizadores, 1000);
setInterval(obtenerDatos, 30000);
