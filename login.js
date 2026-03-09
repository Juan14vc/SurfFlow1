async function intentarLogin() {
    const user = document.getElementById('txt-usuario').value;
    const pass = document.getElementById('txt-password').value;

    if (!user || !pass) {
        alert("¡Ingresa tus datos! 🏄‍♂️");
        return;
    }

    try {
        // CORRECCIÓN: La URL va entre comillas invertidas, pero SIN ${} al principio
        const url = `https://surfflow1.onrender.com/Servlet?accion=login&user=${encodeURIComponent(user)}&pwd=${encodeURIComponent(pass)}`;
        
        console.log("Intentando conectar a:", url);

        const response = await fetch(url);
        const data = await response.json();

        if (data.status === "success") {
            localStorage.setItem('nombre_admin', data.usuario.nombre);
            localStorage.setItem('usuario_logeado', 'true'); 
            window.location.href = "SurfFlow.html"; 
        } else {
            alert("Credenciales incorrectas ❌");
        }
    } catch (error) {
        console.error("Error detallado:", error);
        alert("El servidor está despertando. Espera 20 segundos y vuelve a intentar.");
    }
}
