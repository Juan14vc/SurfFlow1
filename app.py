from flask import Flask, jsonify, request
from flask_cors import CORS
from database import get_connection
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def inicializar_sistema():
    """Sincroniza la estructura de la DB al arrancar"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Tabla Usuarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Usuarios (
                id SERIAL PRIMARY KEY,
                nombre_completo VARCHAR(100),
                usuario VARCHAR(50) UNIQUE,
                password VARCHAR(50),
                rol VARCHAR(20)
            );
        """)
        # 2. Tabla Tablas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Tablas (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100),
                medida VARCHAR(20),
                tipo VARCHAR(50),
                estado VARCHAR(20) DEFAULT 'Disponible'
            );
        """)
        # 3. Tabla Reservas (Fiel a tu diagrama de SQL Server)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Reservas (
                id SERIAL PRIMARY KEY,
                cliente_nombre VARCHAR(100),
                monto_pago DECIMAL(10,2),
                comprobante_img TEXT,
                confirmado BOOLEAN DEFAULT True,
                fecha_reserva TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tabla_id INTEGER REFERENCES Tablas(id),
                usuario_id INTEGER REFERENCES Usuarios(id)
            );
        """)
        # 4. Usuario Admin por defecto
        cursor.execute("""
            INSERT INTO Usuarios (nombre_completo, usuario, password, rol)
            VALUES ('Natali', 'natali_surf', 'surf2026', 'admin')
            ON CONFLICT (usuario) DO NOTHING;
        """)
        conn.commit()
    except Exception as e:
        print(f"Error inicialización: {e}")
    finally:
        cursor.close()
        conn.close()

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
            return jsonify({"status": "error"})

        # --- LISTAR TABLAS ---
        elif accion == 'listar':
            cursor.execute("SELECT id, nombre, medida, tipo, estado FROM Tablas ORDER BY id ASC")
            tablas = [{"id": r[0], "nombre": r[1], "medida": r[2], "tipo": r[3], "estado": r[4]} for r in cursor.fetchall()]
            return jsonify(tablas)

        # --- ACTUALIZAR ESTADO (PARA GESTIÓN INDIVIDUAL) ---
        elif accion == 'actualizar_estado':
            id_t = request.args.get('id')
            est = request.args.get('estado')
            cursor.execute("UPDATE Tablas SET estado = %s WHERE id = %s", (est, id_t))
            conn.commit()
            return jsonify({"status": "ok"})

        # --- INSERTAR RESERVA (EL CORAZÓN DEL NEGOCIO) ---
        elif accion == 'insertar_reserva':
            t_id = request.args.get('tabla_id')
            cli = request.args.get('cliente')
            mon = request.args.get('monto')
            ref = request.args.get('comprobante')
            
            # Buscamos el ID del usuario logueado (Natali)
            cursor.execute("SELECT id FROM Usuarios WHERE usuario = 'natali_surf' LIMIT 1")
            u_id = cursor.fetchone()[0]

            # Inserción en la DB_SurfFlow
            sql = """INSERT INTO Reservas (cliente_nombre, monto_pago, comprobante_img, confirmado, tabla_id, usuario_id) 
                     VALUES (%s, %s, %s, True, %s, %s)"""
            cursor.execute(sql, (cli, mon, ref, t_id, u_id))
            
            # Actualizamos la tabla a 'En Uso'
            cursor.execute("UPDATE Tablas SET estado = 'En Uso' WHERE id = %s", (t_id,))
            
            conn.commit()
            return jsonify({"status": "ok"})

        # --- REPORTE DE VENTAS ---
        elif accion == 'listar_movimientos':
            sql = """SELECT R.fecha_reserva, T.nombre, R.cliente_nombre, R.comprobante_img, R.monto_pago
                     FROM Reservas R 
                     INNER JOIN Tablas T ON R.tabla_id = T.id 
                     ORDER BY R.fecha_reserva DESC"""
            cursor.execute(sql)
            movs = [{"fecha": r[0].strftime("%d/%m %H:%M"), "tabla": r[1], "cliente": r[2], "ref": r[3], "monto": float(r[4])} for r in cursor.fetchall()]
            return jsonify(movs)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
