async function intentarLogin() {
    const user = document.getElementById('txt-usuario').value;
    const pass = document.getElementById('txt-password').value;

    if (!user || !pass) {
        alert("¡Ingresa tus datos! 🏄‍♂️");
        return;
    }

    try {
        // AGREGAMOS: ?accion=login para que Python sepa que es un inicio de sesión
        const response = await fetch(`${https://surfflow1.onrender.com/Servlet}?accion=login&user=${user}&pwd=${pass}`);
        const data = await response.json();

        if (data.status === "success") {
            // Guardamos el nombre para mostrarlo en el Dashboard
            localStorage.setItem('nombre_admin', data.usuario.nombre);
            // IMPORTANTE: Esta es la "llave" para que SurfFlow.html te deje entrar
            localStorage.setItem('usuario_logeado', 'true'); 
            
            window.location.href = "SurfFlow.html"; 
        } else {
            alert("Credenciales incorrectas.");
        }
    } catch (error) {
        alert("El servidor está despertando... espera 30 segundos y reintenta.");
    }
}

