async function intentarLogin() {
    const user = document.getElementById('txt-usuario').value;
    const pass = document.getElementById('txt-password').value;

    if (!user || !pass) {
        alert("¡Ingresa tus datos! 🏄‍♂️");
        return;
    }

    try {
        // URL limpia con backticks y solo variables donde corresponde
        const url = `https://surfflow1.onrender.com/Servlet?accion=login&user=${encodeURIComponent(user)}&pwd=${encodeURIComponent(pass)}`;
        
        const response = await fetch(url);
        const data = await response.json();

        if (data.status === "success") {
            localStorage.setItem('nombre_admin', data.usuario.nombre);
            localStorage.setItem('usuario_logeado', 'true'); 
            window.location.href = "SurfFlow.html"; 
        } else {
            alert("Credenciales incorrectas.");
        }
    } catch (error) {
        console.error("Error real:", error); // Esto te ayuda a ver fallos en F12
        alert("El servidor está despertando... espera 30 segundos y reintenta.");
    }
}
