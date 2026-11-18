async function intentarLogin() {
    const user = document.getElementById('txt-usuario').value;
    const pass = document.getElementById('txt-password').value;

    if (!user || !pass) {
        alert("¡Ingresa tus datos! 🏄‍♂️");
        return;
    }

    try {
        // Ponemos la URL directamente aquí para que no haya errores de "variable no definida"
        const url = `https://surfflow1.onrender.com/Servlet?accion=login&user=${encodeURIComponent(user)}&pwd=${encodeURIComponent(pass)}`;
        
        console.log("Intentando conectar a:", url); // Esto aparecerá en tu consola F12

        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error("El servidor no respondió correctamente");
        }

        const data = await response.json();

        if (data.status === "success") {
            // Guardamos los datos de Natali
            localStorage.setItem('nombre_admin', data.usuario.nombre);
            localStorage.setItem('usuario_logeado', 'true'); 
            
            // Redireccionamos
            window.location.href = "SurfFlow.html"; 
        } else {
            alert("Credenciales incorrectas. Verifica tu usuario y clave.");
        }
    } catch (error) {
        console.error("Error detallado:", error);
        alert("El servidor de Render está despertando (Cold Start). Dale 20 segundos y vuelve a intentar.");
    }
}