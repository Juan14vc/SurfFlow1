const URL_API = "https://surfflow1.onrender.com/Servlet";
const urlParams = new URLSearchParams(window.location.search);
const idActual = urlParams.get('id');

// Mostrar el ID en la interfaz
if(document.getElementById('id-txt')) {
    document.getElementById('id-txt').innerText = idActual || "Error";
}

document.getElementById('reservaForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btn');
    btn.disabled = true;
    btn.innerText = "⏳ Guardando...";

    const params = new URLSearchParams({
        accion: "insertar_reserva",
        tabla_id: idActual,
        cliente: document.getElementById('cliente').value,
        monto: document.getElementById('monto').value,
        comprobante: document.getElementById('ref').value // Referencia Yape/Plin
    });

    try {
        const res = await fetch(`${URL_API}?${params}`);
        const data = await res.json();
        
        if (data.status === "ok") {
            alert("✅ ¡Alquiler registrado con éxito!");
            window.location.href = "SurfFlow.html";
        } else {
            alert("❌ Error al guardar.");
            btn.disabled = false;
        }
    } catch (err) {
        alert("❌ Error de conexión con el servidor.");
        btn.disabled = false;
    }
});
