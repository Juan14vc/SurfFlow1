const URL_API = "https://surfflow1.onrender.com/Servlet";

async function intentarLogin() {
    const user = document.getElementById('txt-usuario').value;
    const pass = document.getElementById('txt-password').value;

    if (!user || !pass) {
        alert("¡Ingresa tus datos! 🏄‍♂️");
        return;
    }

    try {
        const response = await fetch(`${URL_API}?accion=login&user=${user}&pwd=${pass}`);
        const data = await response.json();

        if (data.status === "success") {
            localStorage.setItem('admin_name', data.usuario.nombre);
            window.location.href = "SurfFlow.html"; 
        } else {
            alert("Credenciales incorrectas.");
        }
    } catch (error) {
        alert("El servidor está despertando... espera 50 segundos y reintenta.");
    }
}