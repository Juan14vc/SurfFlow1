from flask import Flask, jsonify, request
from flask_cors import CORS
from database import get_connection
import os

app = Flask(__name__)
# Permitimos CORS para que tu página en GitHub Pages pueda hablar con este servidor
CORS(app)

def inicializar_sistema():
    """Crea las tablas y el usuario administrador si no existen al arrancar"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Crear tabla de Usuarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Usuarios (
                id SERIAL PRIMARY KEY,
                nombre_completo VARCHAR(100),
                usuario VARCHAR(50) UNIQUE,
                password VARCHAR(50),
                rol VARCHAR(20)
            );
        """)

        # 2. Crear tabla de Tablas (Inventario)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Tablas (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100),
                medida VARCHAR(20),
                tipo VARCHAR(50),
                estado VARCHAR(20) DEFAULT 'Disponible'
            );
        """)

        # 3. Crear tabla de Reservas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Reservas (
                id SERIAL PRIMARY KEY,
                cliente_nombre VARCHAR(100),
                monto_pago DECIMAL(10,2),
                comprobante_img TEXT,
                confirmado BOOLEAN DEFAULT TRUE,
                fecha_reserva TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tabla_id INTEGER REFERENCES Tablas(id)
            );
        """)

        # 4. Insertar a Natali como administradora (si no existe)
        cursor.execute("""
            INSERT INTO Usuarios (nombre_completo, usuario, password, rol)
            VALUES ('Natali', 'natali_surf', 'surf2026', 'admin')
            ON CONFLICT (usuario) DO NOTHING;
        """)

        # 5. Insertar inventario inicial si la tabla está vacía
        cursor.execute("SELECT COUNT(*) FROM Tablas")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO Tablas (nombre, medida, tipo, estado) VALUES 
                ('Blue Wave', '7.0', 'Funboard', 'Disponible'),
                ('Red Shark', '6.0', 'Shortboard', 'Disponible'),
                ('Yellow Sun', '8.2', 'Longboard', 'Disponible');
            """)

        conn.commit()
        print("✅ Sistema inicializado: Tablas y usuario administrador listos.")
    except Exception as e:
        print(f"❌ Error en la inicialización: {e}")
    finally:
        cursor.close()
        conn.close()

# Ejecutamos la configuración automática
inicializar_sistema()

@app.route('/Servlet', methods=['GET'])
def gateway():
    accion = request.args.get('accion')
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Lógica de LOGIN
        if accion == 'login':
            user = request.args.get('user')
            pwd = request.args.get('pwd')
            cursor.execute("SELECT id, nombre_completo FROM Usuarios WHERE usuario = %s AND password = %s", (user, pwd))
            row = cursor.fetchone()
            if row:
                return jsonify({"status": "success", "usuario": {"id": row[0], "nombre": row[1]}})
            return jsonify({"status": "error", "message": "Credenciales inválidas"})

        # Listar inventario para el sistema de gestión
        if accion == 'listar':
            cursor.execute("SELECT id, nombre, medida, tipo, estado FROM Tablas ORDER BY id ASC")
            tablas = [{"id": r[0], "nombre": r[1], "medida": r[2], "tipo": r[3], "estado": r[4]} for r in cursor.fetchall()]
            return jsonify(tablas)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    # Render asigna un puerto dinámicamente mediante la variable de entorno PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
