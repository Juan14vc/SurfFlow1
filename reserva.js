// reserva.js corregido
const URL_API = "https://surfflow1.onrender.com/Servlet";
const idActual = urlParams.get('id');
document.getElementById('id-txt').innerText = idActual || "Error";

document.getElementById('reservaForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const btn = document.getElementById('btn');
    btn.disabled = true;
    btn.innerText = "⏳ Guardando...";

    // Preparamos los parámetros para Flask
    const params = new URLSearchParams({
    accion: "insertar_reserva",
    tabla_id: idActual,
    cliente: document.getElementById('cliente').value,
    monto: document.getElementById('monto').value,
    comprobante: document.getElementById('ref').value // Esto envía "Yape"
    });

    try {
        // IMPORTANTE: Puerto 5000 para Python
        const res = await fetch(`http://localhost:5000/Servlet?${params}`);
        const data = await res.json();
        
        if (data.status === "ok") {
            alert("✅ ¡Alquiler guardado con éxito!");
            window.location.href = "SurfFlow.html";
        } else {
            alert("❌ Error: No se pudo guardar en la base de datos.");
            btn.disabled = false;
            btn.innerText = "Reintentar Guardar";
        }
    } catch (err) {
        alert("❌ Error: El servidor Python no está respondiendo.");
        btn.disabled = false;
    }

});
