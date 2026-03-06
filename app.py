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
def login():
    u = request.args.get('user')
    p = request.args.get('pwd')
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT nombre_completo FROM Usuarios WHERE usuario = %s AND password = %s", (u, p))
        user = cur.fetchone()
        if user:
            return jsonify({"status": "success", "usuario": {"nombre": user[0]}})
        return jsonify({"status": "error", "message": "No encontrado"})
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
