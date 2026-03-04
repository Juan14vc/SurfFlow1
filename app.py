from flask import Flask, jsonify, request
from flask_cors import CORS
from database import get_connection
import datetime

app = Flask(__name__)
CORS(app) 

# --- FUNCIONES DE BASE DE DATOS (DAO) ---

def db_listar_tablas():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, medida, tipo, estado FROM Tablas")
    tablas = []
    for row in cursor.fetchall():
        tablas.append({
            "id": row[0], "nombre": row[1], "medida": row[2], "tipo": row[3], "estado": row[4]
        })
    conn.close()
    return tablas

def db_registrar_alquiler(datos):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sql_ins = """INSERT INTO Reservas 
                     (cliente_nombre, monto_pago, comprobante_img, confirmado, fecha_reserva, tabla_id) 
                     VALUES (?, ?, CONVERT(VARBINARY(MAX), ?), ?, GETDATE(), ?)"""
        
        cursor.execute(sql_ins, (
            datos.get('cliente'), datos.get('monto'), 
            datos.get('comprobante'), 1, datos.get('tabla_id')
        ))
        
        cursor.execute("UPDATE Tablas SET estado = 'En Uso' WHERE id = ?", (datos.get('tabla_id'),))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error SQL: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def db_modificar_estado(id_tabla, nuevo_estado):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Tablas SET estado = ? WHERE id = ?", (nuevo_estado, id_tabla))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def db_listar_movimientos():
    conn = get_connection()
    cursor = conn.cursor()
    sql = """
        SELECT R.id, T.nombre, R.cliente_nombre, R.monto_pago, R.fecha_reserva, 
               CAST(R.comprobante_img AS VARCHAR(MAX)) as ref 
        FROM Reservas R
        INNER JOIN Tablas T ON R.tabla_id = T.id
        ORDER BY R.fecha_reserva DESC
    """
    cursor.execute(sql)
    movimientos = []
    for row in cursor.fetchall():
        movimientos.append({
            "id": row[0], "tabla": row[1], "cliente": row[2],
            "monto": float(row[3]),
            "fecha": row[4].strftime("%d/%m/%Y %H:%M"),
            "ref": row[5] if row[5] else "S/N"
        })
    conn.close()
    return movimientos

def db_agregar_tabla(nombre, medida, tipo):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Insertamos la tabla con estado 'Disponible' por defecto
        sql = "INSERT INTO Tablas (nombre, medida, tipo, estado) VALUES (?, ?, ?, 'Disponible')"
        cursor.execute(sql, (nombre, medida, tipo))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error al agregar tabla: {e}")
        return False

# --- EL PUENTE (RUTAS API) ---

@app.route('/Servlet', methods=['GET'])
def gateway():
    accion = request.args.get('accion')
    
    if accion == 'listar':
        return jsonify(db_listar_tablas())
    
    if accion == 'insertar_reserva':
        exito = db_registrar_alquiler(request.args)
        return jsonify({"status": "ok" if exito else "error"})

    if accion == 'actualizar_estado':
        exito = db_modificar_estado(request.args.get('id'), request.args.get('estado'))
        return jsonify({"status": "ok" if exito else "error"})
    
    if accion == 'listar_movimientos':
        return jsonify(db_listar_movimientos())
    
    if accion == 'login':
        user = request.args.get('user')
        pwd = request.args.get('pwd')
        
        # Consultamos a la base de datos
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre_completo FROM Usuarios WHERE usuario = ? AND password = ?", (user, pwd))
        row = cursor.fetchone()
        conn.close()

        if row:
            # Si existe, devolvemos éxito y sus datos
            return jsonify({
                "status": "success",
                "usuario": {"id": row[0], "nombre": row[1]}
            })
        else:
            # Si no coincide, devolvemos error
            return jsonify({"status": "error", "message": "Credenciales inválidas"})
        
    if accion == 'agregar_tabla':
        nombre = request.args.get('nombre')
        medida = request.args.get('medida')
        tipo = request.args.get('tipo')
        
        exito = db_agregar_tabla(nombre, medida, tipo)
        
        if exito:
            return jsonify({"status": "success", "message": "Tabla guardada"})
        else:
            return jsonify({"status": "error", "message": "No se pudo guardar"})

    return jsonify({"error": "Acción no reconocida"}), 404

    if accion == 'eliminar_tabla':
        id_tabla = request.args.get('id')
        
        conn = get_connection()
        cursor = conn.cursor()
        # OJO: Solo eliminamos si no tiene reservas activas (o podrías solo 'desactivarla')
        cursor.execute("DELETE FROM Tablas WHERE id = ?", (id_tabla,))
        conn.commit()
        conn.close()
    
    return jsonify({"status": "success"})

import os

if __name__ == '__main__':
    # Render y Railway te asignan un puerto automáticamente
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)