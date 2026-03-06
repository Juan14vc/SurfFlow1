const URL_API = "https://surfflow1.onrender.com/Servlet";

async function intentarLogin() {
    const user = document.getElementById('txt-usuario').value;
    const pass = document.getElementById('txt-password').value;

    try {
        // Importante: No borres el ?accion= si tu código lo usa, pero aquí lo simplifiqué
        const response = await fetch(`${URL_API}?user=${user}&pwd=${pass}`);
        const data = await response.json();

        if (data.status === "success") {
            localStorage.setItem('admin_name', data.usuario.nombre);
            window.location.href = "SurfFlow.html"; 
        } else {
            alert("Usuario o clave incorrectos");
        }
    } catch (error) {
        alert("El servidor está cargando... espera 30 segundos y reintenta.");
    }
}
