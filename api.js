// api.js - funciones compartidas por todas las páginas de SurfFlow
const URL_API = "https://surfflow1.onrender.com/Servlet";

function exigirLogin() {
    if (localStorage.getItem("usuario_logeado") !== "true") {
        window.location.href = "index.html";
    }
}

// Llama al backend. Los arreglos se envían como parámetros repetidos.
// Si el servidor responde con error, lanza una excepción con el mensaje.
async function llamar(params) {
    const qs = new URLSearchParams();
    for (const [clave, valor] of Object.entries(params)) {
        if (Array.isArray(valor)) valor.forEach(v => qs.append(clave, v));
        else if (valor !== undefined && valor !== null) qs.append(clave, valor);
    }
    const res = await fetch(`${URL_API}?${qs}`);
    const data = await res.json();
    if (data && !Array.isArray(data) && data.status === "error") {
        throw new Error(data.message || "Error del servidor");
    }
    return data;
}

function esc(texto) {
    return String(texto ?? "").replace(/[&<>"']/g, c => (
        { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
    ));
}

// 90 -> "1 h 30 min"
function fmtMin(minutos) {
    const m = Number(minutos) || 0;
    const h = Math.floor(m / 60);
    const r = m % 60;
    if (h && r) return `${h} h ${r} min`;
    if (h) return `${h} h`;
    return `${r} min`;
}

// milisegundos -> "05:32" o "1:05:32"
function reloj(ms) {
    const s = Math.max(0, Math.floor(ms / 1000));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const seg = s % 60;
    const dos = n => String(n).padStart(2, "0");
    return h > 0 ? `${h}:${dos(m)}:${dos(seg)}` : `${dos(m)}:${dos(seg)}`;
}

// segundos (epoch) -> fecha y hora local
function fmtFecha(segundos) {
    return new Date(segundos * 1000).toLocaleString("es-PE", {
        day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit"
    });
}

function soles(n) {
    return "S/ " + Number(n || 0).toFixed(2);
}
