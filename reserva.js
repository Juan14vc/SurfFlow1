// reserva.js - registrar alquiler (requiere api.js cargado antes)
exigirLogin();

const idActual = new URLSearchParams(window.location.search).get("id");
const form = document.getElementById("reservaForm");
const btn = document.getElementById("btn");
const aviso = document.getElementById("aviso");

function bloquear(mensaje) {
    aviso.textContent = mensaje;
    aviso.style.display = "block";
    form.querySelectorAll("input, button").forEach(el => el.disabled = true);
}

// Botones de tiempo rápido
document.querySelectorAll(".rapidos button").forEach(b => {
    b.addEventListener("click", () => {
        document.getElementById("minutos").value = b.dataset.min;
    });
});

async function cargarTabla() {
    if (!idActual) return bloquear("No se indicó la tabla.");
    try {
        const t = await llamar({ accion: "obtener_tabla", id: idActual });
        document.getElementById("nombre-tabla").textContent = `${t.nombre} (#${t.id})`;
        if (t.uso !== "Alquiler") bloquear("Esta tabla es de uso para clases, no se alquila.");
        else if (t.estado === "Mantenimiento") bloquear("Esta tabla está en mantenimiento.");
        else if (t.estado === "En Uso" && t.reserva_id) bloquear("Esta tabla ya está alquilada.");
    } catch (e) {
        bloquear("❌ " + e.message);
    }
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    btn.disabled = true;
    btn.textContent = "⏳ Guardando...";

    try {
        await llamar({
            accion: "insertar_reserva",
            tabla_id: idActual,
            cliente: document.getElementById("cliente").value,
            minutos: document.getElementById("minutos").value,
            monto: document.getElementById("monto").value,
            comprobante: document.getElementById("ref").value
        });
        alert("✅ ¡Alquiler registrado con éxito!");
        window.location.href = "SurfFlow.html";
    } catch (err) {
        alert("❌ " + err.message);
        btn.disabled = false;
        btn.textContent = "GUARDAR Y FINALIZAR";
    }
});

cargarTabla();
