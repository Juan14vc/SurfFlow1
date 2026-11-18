from flask import Flask, jsonify, request
from flask_cors import CORS
from database import get_connection
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


def inicializar_sistema():
    """Sincroniza la estructura de la DB al arrancar"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

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
        # 3. Tabla Reservas
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
        print("Base de datos inicializada correctamente")
    except Exception as e:
        print(f"Error inicialización: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


inicializar_sistema()


@app.route('/')
def inicio():
    return jsonify({"status": "ok", "app": "SurfFlow API"})


@app.route('/Servlet', methods=['GET'])
def gateway():
    accion = request.args.get('accion')

    try:
        conn = get_connection()
    except Exception as e:
        return jsonify({"status": "error", "message": f"No hay conexión a la BD: {e}"}), 500

    cursor = conn.cursor()

    try:
        # --- LOGIN ---
        if accion == 'login':
            user = request.args.get('user')
            pwd = request.args.get('pwd')
            cursor.execute(
                "SELECT id, nombre_completo FROM Usuarios WHERE usuario = %s AND password = %s",
                (user, pwd)
            )
            row = cursor.fetchone()
            if row:
                return jsonify({"status": "success", "usuario": {"id": row[0], "nombre": row[1]}})
            return jsonify({"status": "error"})

        # --- LISTAR TABLAS ---
        elif accion == 'listar':
            cursor.execute("SELECT id, nombre, medida, tipo, estado FROM Tablas ORDER BY id ASC")
            tablas = [
                {"id": r[0], "nombre": r[1], "medida": r[2], "tipo": r[3], "estado": r[4]}
                for r in cursor.fetchall()
            ]
            return jsonify(tablas)

        # --- AGREGAR TABLA ---
        elif accion == 'agregar_tabla':
            nombre = request.args.get('nombre')
            medida = request.args.get('medida')
            tipo = request.args.get('tipo')
            cursor.execute(
                "INSERT INTO Tablas (nombre, medida, tipo) VALUES (%s, %s, %s)",
                (nombre, medida, tipo)
            )
            conn.commit()
            return jsonify({"status": "success"})

        # --- ACTUALIZAR ESTADO ---
        elif accion == 'actualizar_estado':
            id_t = request.args.get('id')
            est = request.args.get('estado')
            cursor.execute("UPDATE Tablas SET estado = %s WHERE id = %s", (est, id_t))
            conn.commit()
            return jsonify({"status": "ok"})

        # --- INSERTAR RESERVA ---
        elif accion == 'insertar_reserva':
            t_id = request.args.get('tabla_id')
            cli = request.args.get('cliente')
            mon = request.args.get('monto')
            ref = request.args.get('comprobante')

            cursor.execute("SELECT id FROM Usuarios WHERE usuario = 'natali_surf' LIMIT 1")
            u_id = cursor.fetchone()[0]

            cursor.execute(
                """INSERT INTO Reservas (cliente_nombre, monto_pago, comprobante_img, confirmado, tabla_id, usuario_id)
                   VALUES (%s, %s, %s, True, %s, %s)""",
                (cli, mon, ref, t_id, u_id)
            )
            cursor.execute("UPDATE Tablas SET estado = 'En Uso' WHERE id = %s", (t_id,))
            conn.commit()
            return jsonify({"status": "ok"})

        # --- REPORTE DE VENTAS ---
        elif accion == 'listar_movimientos':
            cursor.execute(
                """SELECT R.fecha_reserva, T.nombre, R.cliente_nombre, R.comprobante_img, R.monto_pago
                   FROM Reservas R
                   INNER JOIN Tablas T ON R.tabla_id = T.id
                   ORDER BY R.fecha_reserva DESC"""
            )
            movs = [
                {
                    "fecha": r[0].strftime("%d/%m %H:%M"),
                    "tabla": r[1],
                    "cliente": r[2],
                    "ref": r[3],
                    "monto": float(r[4])
                }
                for r in cursor.fetchall()
            ]
            return jsonify(movs)

        # --- ACCIÓN DESCONOCIDA ---
        else:
            return jsonify({"status": "error", "message": "acción no válida"})

    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)})
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)