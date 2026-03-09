from flask import Flask, jsonify, request
from flask_cors import CORS
from database import get_connection
import os

app = Flask(__name__)
# Permitimos CORS para que tu GitHub Pages pueda conectarse sin bloqueos
CORS(app, resources={r"/*": {"origins": "*"}})

def inicializar_sistema():
    """Función para crear tablas y usuario inicial automáticamente"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Crear tabla de Usuarios si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Usuarios (
                id SERIAL PRIMARY KEY,
                nombre_completo VARCHAR(100),
                usuario VARCHAR(50) UNIQUE,
                password VARCHAR(50),
                rol VARCHAR(20)
            );
        """)

        # 2. Crear tabla de Tablas (Inventario) si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Tablas (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100),
                medida VARCHAR(20),
                tipo VARCHAR(50),
                estado VARCHAR(20) DEFAULT 'Disponible'
            );
        """)

        # 3. Crear tabla de Reservas si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Reservas (
                id SERIAL PRIMARY KEY,
                cliente_nombre VARCHAR(100),
                monto_pago DECIMAL(10,2),
                comprobante_img TEXT,
                confirmado BOOLEAN,
                fecha_reserva TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tabla_id INTEGER REFERENCES Tablas(id)
            );
        """)

        # 4. Insertar a Natali (Admin) si no existe
        cursor.execute("""
            INSERT INTO Usuarios (nombre_completo, usuario, password, rol)
            VALUES ('Natali', 'natali_surf', 'surf2026', 'admin')
            ON CONFLICT (usuario) DO NOTHING;
        """)

        # 5. Insertar tablas de prueba solo si está vacío
        cursor.execute("SELECT COUNT(*) FROM Tablas")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO Tablas (nombre, medida, tipo, estado) VALUES 
                ('Blue Wave', '7.0', 'Funboard', 'Disponible'),
                ('Red Shark', '6.0', 'Shortboard', 'Disponible'),
                ('Yellow Sun', '8.2', 'Longboard', 'Disponible');
            """)

        conn.commit()
        print("✅ Base de datos sincronizada correctamente.")
    except Exception as e:
        print(f"❌ Error al inicializar: {e}")
    finally:
        cursor.close()
        conn.close()

# Ejecutar la inicialización al arrancar el servidor
inicializar_sistema()

@app.route('/Servlet', methods=['GET'])
def gateway():
    accion = request.args.get('accion')
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # --- LOGIN ---
        if accion == 'login':
            user = request.args.get('user')
            pwd = request.args.get('pwd')
            cursor.execute("SELECT id, nombre_completo FROM Usuarios WHERE usuario = %s AND password = %s", (user, pwd))
            row = cursor.fetchone()
            if row:
                return jsonify({"status": "success", "usuario": {"id": row[0], "nombre": row[1]}})
            return jsonify({"status": "error", "message": "Credenciales inválidas"})

        # --- LISTAR INVENTARIO ---
        elif accion == 'listar':
            cursor.execute("SELECT id, nombre, medida, tipo, estado FROM Tablas ORDER BY id ASC")
            tablas = [{"id": r[0], "nombre": r[1], "medida": r[2], "tipo": r[3], "estado": r[4]} for r in cursor.fetchall()]
            return jsonify(tablas)

        # --- ACTUALIZAR ESTADO (LIBERAR, MANTENIMIENTO O PREPARAR ALQUILER) ---
        elif accion == 'actualizar_estado':
            id_tabla = request.args.get('id')
            nuevo_estado = request.args.get('estado')
            cursor.execute("UPDATE Tablas SET estado = %s WHERE id = %s", (nuevo_estado, id_tabla))
            conn.commit()
            return jsonify({"status": "ok", "message": "Estado actualizado"})

        # --- REGISTRAR RESERVA (ALQUILER FINALIZADO) ---
        elif accion == 'insertar_reserva':
            tabla_id = request.args.get('tabla_id')
            cliente = request.args.get('cliente')
            monto = request.args.get('monto')
            referencia = request.args.get('comprobante')

            # Insertamos el movimiento
            sql = """INSERT INTO Reservas (cliente_nombre, monto_pago, comprobante_img, confirmado, tabla_id) 
                     VALUES (%s, %s, %s, %s, %s)"""
            cursor.execute(sql, (cliente, monto, referencia, True, tabla_id))
            
            # Aseguramos que el estado cambie a 'En Uso'
            cursor.execute("UPDATE Tablas SET estado = 'En Uso' WHERE id = %s", (tabla_id,))
            
            conn.commit()
            return jsonify({"status": "ok"})

        # --- LISTAR MOVIMIENTOS (REPORTE DE VENTAS) ---
        elif accion == 'listar_movimientos':
            sql = """SELECT R.fecha_reserva, T.nombre, R.cliente_nombre, R.comprobante_img, R.monto_pago
                     FROM Reservas R 
                     INNER JOIN Tablas T ON R.tabla_id = T.id 
                     ORDER BY R.fecha_reserva DESC"""
            cursor.execute(sql)
            movs = [{
                "fecha": r[0].strftime("%d/%m %H:%M"),
                "tabla": r[1],
                "cliente": r[2],
                "ref": r[3], 
                "monto": float(r[4])
            } for r in cursor.fetchall()]
            return jsonify(movs)

        # --- AGREGAR NUEVA TABLA AL STOCK ---
        elif accion == 'agregar_tabla':
            nombre = request.args.get('nombre')
            medida = request.args.get('medida')
            tipo = request.args.get('tipo')
            cursor.execute("INSERT INTO Tablas (nombre, medida, tipo, estado) VALUES (%s, %s, %s, 'Disponible')", 
                           (nombre, medida, tipo))
            conn.commit()
            return jsonify({"status": "success"})

        else:
            return jsonify({"status": "error", "message": "Acción no reconocida"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
