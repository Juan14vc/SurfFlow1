import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from database import get_connection

app = Flask(__name__)
CORS(app)

def setup_db():
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Crea tablas
        cur.execute("CREATE TABLE IF NOT EXISTS Usuarios (id SERIAL PRIMARY KEY, nombre_completo TEXT, usuario TEXT UNIQUE, password TEXT, rol TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS Tablas (id SERIAL PRIMARY KEY, nombre TEXT, medida TEXT, tipo TEXT, estado TEXT DEFAULT 'Disponible')")
        
        # Inserta a Natali (Admin)
        cur.execute("INSERT INTO Usuarios (nombre_completo, usuario, password, rol) VALUES ('Natali', 'natali_surf', 'surf2026', 'admin') ON CONFLICT (usuario) DO NOTHING")
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

setup_db()

@app.route('/Servlet', methods=['GET'])
def gateway():
    accion = request.args.get('accion') # Aquí leemos qué quiere hacer el JS
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # --- CASO 1: LOGIN ---
        if accion == 'login':
            u = request.args.get('user')
            p = request.args.get('pwd')
            cur.execute("SELECT nombre_completo FROM Usuarios WHERE usuario = %s AND password = %s", (u, p))
            user = cur.fetchone()
            if user:
                return jsonify({"status": "success", "usuario": {"nombre": user[0]}})
            return jsonify({"status": "error", "message": "Credenciales incorrectas"})

        # --- CASO 2: LISTAR TABLAS ---
        elif accion == 'listar':
            cur.execute("SELECT id, nombre, medida, tipo, estado FROM Tablas ORDER BY id ASC")
            tablas = [{"id": r[0], "nombre": r[1], "medida": r[2], "tipo": r[3], "estado": r[4]} for r in cur.fetchall()]
            return jsonify(tablas)

        # --- CASO 3: AGREGAR TABLA ---
        elif accion == 'agregar_tabla':
            n = request.args.get('nombre')
            m = request.args.get('medida')
            t = request.args.get('tipo')
            cur.execute("INSERT INTO Tablas (nombre, medida, tipo) VALUES (%s, %s, %s)", (n, m, t))
            conn.commit()
            return jsonify({"status": "success"})

        return jsonify({"status": "error", "message": "Acción no reconocida"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

