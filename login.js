// URL de tu API (Asegúrate de que coincida con tu puerto o ngrok)
const URL_API = "https://surfflow1.onrender.com/Servlet";
async function intentarLogin() {
    const user = document.getElementById('txt-usuario').value;
    const pass = document.getElementById('txt-password').value;
    const divError = document.getElementById('mensaje-error');

    if (user === "" || pass === "") {
        alert("¡No olvides poner tu usuario y clave, surfista! 🏄‍♂️");
        return;
    }

    try {
        const URL_API = "https://surfflow1.onrender.com/Servlet";
        const response = await fetch(url);
        const data = await response.json();

        if (data.status === "success") {
            // 1. Guardamos una "marca" en el navegador para saber que ya entró
            localStorage.setItem('usuario_logeado', 'true');
            localStorage.setItem('nombre_admin', data.usuario.nombre);

            // 2. ¡LA REDIRECCIÓN! La mandamos a la página principal
            window.location.href = "SurfFlow.html"; 
        } else {
            // Si los datos están mal, mostramos el error rojo
            divError.style.display = "block";
            divError.innerText = "⚠️ Usuario o clave incorrectos";
        }
    } catch (error) {
        console.error("Error:", error);
        alert("Parece que el servidor está apagado. ¡Prende el Python!");
    }

}

