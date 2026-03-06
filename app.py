from flask import Flask, jsonify, request
from flask_cors import CORS
from database import get_connection
import os

app = Flask(__name__)
CORS(app) # Crucial para que GitHub Pages pueda comunicarse con Render

@app.route('/Servlet', methods=['GET'])
def gateway():
    accion = request.args.get('accion')
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # VALIDACIÓN DE USUARIO
        if accion == 'login':
            user, pwd = request.args.get('user'), request.args.get('pwd')
            cursor.execute("SELECT id, nombre_completo FROM Usuarios WHERE usuario = %s AND password = %s", (user, pwd))
            row = cursor.fetchone()
            if row:
                return jsonify({"status": "success", "usuario": {"id": row[0], "nombre": row[1]}})
            return jsonify({"status": "error", "message": "No se encontró al surfista"})

        # LISTAR TABLAS DE BARRANCO
        if accion == 'listar':
            cursor.execute("SELECT id, nombre, medida, tipo, estado FROM Tablas ORDER BY id ASC")
            tablas = [{"id": r[0], "nombre": r[1], "medida": r[2], "tipo": r[3], "estado": r[4]} for r in cursor.fetchall()]
            return jsonify(tablas)

        # REGISTRAR NUEVO ALQUILER
        if accion == 'insertar_reserva':
            sql = """INSERT INTO Reservas (cliente_nombre, monto_pago, comprobante_img, confirmado, fecha_reserva, tabla_id) 
                     VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)"""
            cursor.execute(sql, (request.args.get('cliente'), request.args.get('monto'), request.args.get('comprobante'), True, request.args.get('tabla_id')))
            # Cambiamos estado de la tabla automáticamente
            cursor.execute("UPDATE Tablas SET estado = 'En Uso' WHERE id = %s", (request.args.get('tabla_id'),))
            conn.commit()
            return jsonify({"status": "ok"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        conn.close()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)