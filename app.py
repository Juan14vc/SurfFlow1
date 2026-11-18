from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS
from database import get_connection
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

TIPOS_CLASE = ("Individual", "Pareja", "Grupal")
USOS_TABLA = ("Alquiler", "Clases")
ESTADOS_TABLA = ("Disponible", "En Uso", "Mantenimiento")
ESTADOS_CLASE = ("En curso", "Completada", "Cancelada")


class ErrorNegocio(Exception):
    """Errores esperados (datos inválidos, reglas del negocio)."""


# ---------------------------------------------------------------------------
# ESQUEMA DE LA BASE DE DATOS (se crea / actualiza solo al arrancar)
# ---------------------------------------------------------------------------
ESQUEMA = [
    """CREATE TABLE IF NOT EXISTS Usuarios (
        id SERIAL PRIMARY KEY,
        nombre_completo VARCHAR(100),
        usuario VARCHAR(50) UNIQUE,
        password VARCHAR(50),
        rol VARCHAR(20)
    )""",
    """CREATE TABLE IF NOT EXISTS Tablas (
        id SERIAL PRIMARY KEY,
        nombre VARCHAR(100),
        medida VARCHAR(20),
        tipo VARCHAR(50),
        estado VARCHAR(20) DEFAULT 'Disponible'
    )""",
    """CREATE TABLE IF NOT EXISTS Reservas (
        id SERIAL PRIMARY KEY,
        cliente_nombre VARCHAR(100),
        monto_pago DECIMAL(10,2),
        comprobante_img TEXT,
        confirmado BOOLEAN DEFAULT True,
        fecha_reserva TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        tabla_id INTEGER REFERENCES Tablas(id),
        usuario_id INTEGER REFERENCES Usuarios(id)
    )""",
    # --- Novedades sobre tablas y alquileres ---
    "ALTER TABLE Tablas ADD COLUMN IF NOT EXISTS uso VARCHAR(20) DEFAULT 'Alquiler'",
    "ALTER TABLE Reservas ADD COLUMN IF NOT EXISTS minutos_pagados INTEGER DEFAULT 60",
    "ALTER TABLE Reservas ADD COLUMN IF NOT EXISTS hora_inicio TIMESTAMPTZ DEFAULT NOW()",
    "ALTER TABLE Reservas ADD COLUMN IF NOT EXISTS hora_fin TIMESTAMPTZ",
    "ALTER TABLE Reservas ADD COLUMN IF NOT EXISTS finalizada BOOLEAN DEFAULT FALSE",
    # --- Alumnos, instructores y paquetes ---
    """CREATE TABLE IF NOT EXISTS Alumnos (
        id SERIAL PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL,
        telefono VARCHAR(30)
    )""",
    """CREATE TABLE IF NOT EXISTS Instructores (
        id SERIAL PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL,
        activo BOOLEAN DEFAULT TRUE
    )""",
    """CREATE TABLE IF NOT EXISTS Paquetes (
        id SERIAL PRIMARY KEY,
        alumno_id INTEGER REFERENCES Alumnos(id),
        clases_total INTEGER NOT NULL,
        precio_total DECIMAL(10,2) DEFAULT 0,
        fecha_compra TIMESTAMPTZ DEFAULT NOW(),
        estado VARCHAR(20) DEFAULT 'Activo',
        notas TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS PagosPaquete (
        id SERIAL PRIMARY KEY,
        paquete_id INTEGER REFERENCES Paquetes(id),
        monto DECIMAL(10,2) NOT NULL,
        referencia TEXT,
        fecha TIMESTAMPTZ DEFAULT NOW()
    )""",
    # --- Clases ---
    """CREATE TABLE IF NOT EXISTS Clases (
        id SERIAL PRIMARY KEY,
        fecha_hora TIMESTAMPTZ NOT NULL,
        duracion_min INTEGER DEFAULT 60,
        tipo VARCHAR(20) DEFAULT 'Individual',
        estado VARCHAR(20) DEFAULT 'Programada',
        paquete_id INTEGER REFERENCES Paquetes(id),
        monto DECIMAL(10,2) DEFAULT 0,
        notas TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS Clase_Participantes (
        clase_id INTEGER REFERENCES Clases(id) ON DELETE CASCADE,
        alumno_id INTEGER REFERENCES Alumnos(id),
        PRIMARY KEY (clase_id, alumno_id)
    )""",
    """CREATE TABLE IF NOT EXISTS Clase_Instructores (
        clase_id INTEGER REFERENCES Clases(id) ON DELETE CASCADE,
        instructor_id INTEGER REFERENCES Instructores(id),
        PRIMARY KEY (clase_id, instructor_id)
    )""",
    """CREATE TABLE IF NOT EXISTS Clase_Tablas (
        clase_id INTEGER REFERENCES Clases(id) ON DELETE CASCADE,
        tabla_id INTEGER REFERENCES Tablas(id),
        PRIMARY KEY (clase_id, tabla_id)
    )""",
]


def inicializar_sistema():
    """Sincroniza la estructura de la DB al arrancar"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        for sql in ESQUEMA:
            cursor.execute(sql)
        cursor.execute("""
            INSERT INTO Usuarios (nombre_completo, usuario, password, rol)
            VALUES ('Natali', 'natali_surf', 'surf2026', 'admin')
            ON CONFLICT (usuario) DO NOTHING;
        """)
        conn.commit()
        print("Base de datos inicializada correctamente")
    except Exception as e:
        print(f"Error inicialización: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


inicializar_sistema()


# ---------------------------------------------------------------------------
# UTILIDADES
# ---------------------------------------------------------------------------
def a_int(valor, defecto=None):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return defecto


def a_dec(valor, defecto=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return defecto


def lista_ids(texto):
    ids = []
    for parte in (texto or "").split(","):
        n = a_int(parte.strip())
        if n is not None:
            ids.append(n)
    return ids


def obtener_o_crear_alumno(cur, nombre, telefono=None):
    nombre = nombre.strip()
    cur.execute("SELECT id FROM Alumnos WHERE LOWER(nombre) = LOWER(%s) LIMIT 1", (nombre,))
    fila = cur.fetchone()
    if fila:
        if telefono:
            cur.execute("UPDATE Alumnos SET telefono = %s WHERE id = %s", (telefono, fila[0]))
        return fila[0]
    cur.execute("INSERT INTO Alumnos (nombre, telefono) VALUES (%s, %s) RETURNING id", (nombre, telefono))
    return cur.fetchone()[0]


# Tablas con su alquiler activo (si lo hay) y si están en una clase en curso
SQL_TABLAS = """
    SELECT T.id, T.nombre, T.medida, T.tipo, T.estado, COALESCE(T.uso, 'Alquiler'),
           R.id, R.cliente_nombre, R.minutos_pagados, EXTRACT(EPOCH FROM R.hora_fin),
           EXISTS (SELECT 1 FROM Clase_Tablas CT JOIN Clases C ON C.id = CT.clase_id
                   WHERE CT.tabla_id = T.id AND C.estado = 'En curso')
    FROM Tablas T
    LEFT JOIN LATERAL (
        SELECT id, cliente_nombre, minutos_pagados, hora_fin FROM Reservas
        WHERE tabla_id = T.id AND finalizada = FALSE AND hora_fin IS NOT NULL
        ORDER BY id DESC LIMIT 1
    ) R ON TRUE
"""


def fila_tabla(r):
    en_uso = r[4] == "En Uso"
    return {
        "id": r[0], "nombre": r[1], "medida": r[2], "tipo": r[3], "estado": r[4], "uso": r[5],
        "reserva_id": r[6] if en_uso else None,
        "cliente": r[7] if en_uso else None,
        "minutos": r[8] if en_uso else None,
        "hora_fin": float(r[9]) if (en_uso and r[9] is not None) else None,
        "en_clase": bool(r[10]),
    }


# ---------------------------------------------------------------------------
# ACCIONES: LOGIN Y TABLAS
# ---------------------------------------------------------------------------
def accion_login(cur, a):
    cur.execute("SELECT id, nombre_completo FROM Usuarios WHERE usuario = %s AND password = %s",
                (a.get("user"), a.get("pwd")))
    fila = cur.fetchone()
    if fila:
        return {"status": "success", "usuario": {"id": fila[0], "nombre": fila[1]}}
    return {"status": "error"}


def accion_listar(cur, a):
    cur.execute(SQL_TABLAS + " ORDER BY T.id ASC")
    return [fila_tabla(r) for r in cur.fetchall()]


def accion_obtener_tabla(cur, a):
    cur.execute(SQL_TABLAS + " WHERE T.id = %s", (a_int(a.get("id"), 0),))
    fila = cur.fetchone()
    if not fila:
        raise ErrorNegocio("Tabla no encontrada")
    return fila_tabla(fila)


def accion_agregar_tabla(cur, a):
    """Agrega 1 tabla, o varias iguales de golpe si cantidad > 1 (se numeran)."""
    nombre = (a.get("nombre") or "").strip()
    medida = (a.get("medida") or "").strip()
    tipo = (a.get("tipo") or "Softboard").strip()
    uso = a.get("uso") or "Alquiler"
    cantidad = a_int(a.get("cantidad"), 1)

    if not nombre or not medida:
        raise ErrorNegocio("Completa el nombre y la medida")
    if uso not in USOS_TABLA:
        raise ErrorNegocio("Uso de tabla no válido")
    if cantidad < 1 or cantidad > 100:
        raise ErrorNegocio("La cantidad debe estar entre 1 y 100")

    if cantidad == 1:
        nombres = [nombre]
    else:
        prefijo = f"{nombre} #"
        cur.execute("SELECT COUNT(*) FROM Tablas WHERE LEFT(nombre, %s) = %s", (len(prefijo), prefijo))
        inicio = cur.fetchone()[0] + 1
        nombres = [f"{prefijo}{inicio + i}" for i in range(cantidad)]

    cur.executemany(
        "INSERT INTO Tablas (nombre, medida, tipo, uso) VALUES (%s, %s, %s, %s)",
        [(n, medida, tipo, uso) for n in nombres],
    )
    return {"status": "success", "creadas": len(nombres)}


def accion_actualizar_estado(cur, a):
    id_t = a_int(a.get("id"))
    estado = a.get("estado")
    if id_t is None or estado not in ESTADOS_TABLA:
        raise ErrorNegocio("Datos no válidos")
    cur.execute("UPDATE Tablas SET estado = %s WHERE id = %s", (estado, id_t))
    if estado != "En Uso":
        # Al liberar la tabla se cierra su alquiler activo
        cur.execute("UPDATE Reservas SET finalizada = TRUE WHERE tabla_id = %s AND finalizada = FALSE", (id_t,))
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# ACCIONES: ALQUILERES
# ---------------------------------------------------------------------------
def accion_insertar_reserva(cur, a):
    t_id = a_int(a.get("tabla_id"))
    cliente = (a.get("cliente") or "").strip()
    monto = a_dec(a.get("monto"), None)
    ref = (a.get("comprobante") or "").strip()
    minutos = a_int(a.get("minutos"), 60)

    if t_id is None or not cliente or monto is None or monto < 0:
        raise ErrorNegocio("Completa cliente y monto")
    if minutos < 5 or minutos > 1440:
        raise ErrorNegocio("El tiempo debe estar entre 5 minutos y 24 horas")

    cur.execute("SELECT estado, COALESCE(uso, 'Alquiler') FROM Tablas WHERE id = %s FOR UPDATE", (t_id,))
    tabla = cur.fetchone()
    if not tabla:
        raise ErrorNegocio("Tabla no encontrada")
    if tabla[1] != "Alquiler":
        raise ErrorNegocio("Esta tabla es de uso para clases, no se alquila")
    if tabla[0] == "Mantenimiento":
        raise ErrorNegocio("La tabla está en mantenimiento")
    cur.execute("SELECT 1 FROM Reservas WHERE tabla_id = %s AND finalizada = FALSE AND hora_fin IS NOT NULL", (t_id,))
    if cur.fetchone():
        raise ErrorNegocio("La tabla ya tiene un alquiler activo")

    cur.execute("SELECT id FROM Usuarios WHERE usuario = 'natali_surf' LIMIT 1")
    fila_u = cur.fetchone()
    u_id = fila_u[0] if fila_u else None

    cur.execute(
        """INSERT INTO Reservas (cliente_nombre, monto_pago, comprobante_img, confirmado, tabla_id, usuario_id,
                                 minutos_pagados, hora_inicio, hora_fin, finalizada)
           VALUES (%s, %s, %s, TRUE, %s, %s, %s, NOW(), NOW() + make_interval(mins => %s), FALSE)""",
        (cliente, monto, ref, t_id, u_id, minutos, minutos),
    )
    cur.execute("UPDATE Tablas SET estado = 'En Uso' WHERE id = %s", (t_id,))
    return {"status": "ok"}


def accion_extender_reserva(cur, a):
    reserva_id = a_int(a.get("reserva_id"))
    minutos = a_int(a.get("minutos"))
    monto = a_dec(a.get("monto"), 0.0)
    if reserva_id is None or not minutos or minutos < 5 or minutos > 1440 or monto < 0:
        raise ErrorNegocio("Indica los minutos a agregar (y el monto, si cobras extra)")
    cur.execute(
        """UPDATE Reservas
           SET hora_fin = hora_fin + make_interval(mins => %s),
               minutos_pagados = minutos_pagados + %s,
               monto_pago = COALESCE(monto_pago, 0) + %s
           WHERE id = %s AND finalizada = FALSE""",
        (minutos, minutos, monto, reserva_id),
    )
    if cur.rowcount == 0:
        raise ErrorNegocio("No hay un alquiler activo para extender")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# ACCIONES: INSTRUCTORES
# ---------------------------------------------------------------------------
def accion_listar_instructores(cur, a):
    cur.execute("SELECT id, nombre FROM Instructores WHERE activo ORDER BY nombre")
    return [{"id": r[0], "nombre": r[1]} for r in cur.fetchall()]


def accion_agregar_instructor(cur, a):
    nombre = (a.get("nombre") or "").strip()
    if not nombre:
        raise ErrorNegocio("Escribe el nombre del instructor")
    cur.execute("SELECT 1 FROM Instructores WHERE LOWER(nombre) = LOWER(%s) AND activo", (nombre,))
    if cur.fetchone():
        raise ErrorNegocio("Ese instructor ya existe")
    cur.execute("INSERT INTO Instructores (nombre) VALUES (%s) RETURNING id", (nombre,))
    return {"status": "ok", "id": cur.fetchone()[0]}


# ---------------------------------------------------------------------------
# ACCIONES: PAQUETES
# ---------------------------------------------------------------------------
def accion_crear_paquete(cur, a):
    nombre = (a.get("alumno") or "").strip()
    telefono = (a.get("telefono") or "").strip() or None
    total = a_int(a.get("clases_total"))
    precio = a_dec(a.get("precio_total"), 0.0)
    pago = a_dec(a.get("monto"), 0.0)
    ref = (a.get("referencia") or "").strip()
    notas = (a.get("notas") or "").strip() or None

    if not nombre:
        raise ErrorNegocio("Escribe el nombre del alumno")
    if not total or total < 1 or total > 100:
        raise ErrorNegocio("El número de clases debe estar entre 1 y 100")
    if precio < 0 or pago < 0:
        raise ErrorNegocio("Los montos no pueden ser negativos")

    alumno_id = obtener_o_crear_alumno(cur, nombre, telefono)
    cur.execute(
        "INSERT INTO Paquetes (alumno_id, clases_total, precio_total, notas) VALUES (%s, %s, %s, %s) RETURNING id",
        (alumno_id, total, precio, notas),
    )
    paquete_id = cur.fetchone()[0]
    if pago > 0:
        cur.execute("INSERT INTO PagosPaquete (paquete_id, monto, referencia) VALUES (%s, %s, %s)",
                    (paquete_id, pago, ref))
    return {"status": "ok", "id": paquete_id}


def accion_listar_paquetes(cur, a):
    cur.execute("""
        SELECT P.id, A.nombre, A.telefono, P.clases_total, P.precio_total, P.fecha_compra, P.estado, P.notas,
               (SELECT COUNT(*) FROM Clases C WHERE C.paquete_id = P.id AND C.estado = 'Completada'),
               (SELECT COUNT(*) FROM Clases C WHERE C.paquete_id = P.id AND C.estado IN ('Programada', 'En curso')),
               COALESCE((SELECT SUM(G.monto) FROM PagosPaquete G WHERE G.paquete_id = P.id), 0)
        FROM Paquetes P JOIN Alumnos A ON A.id = P.alumno_id
        ORDER BY (P.estado = 'Activo') DESC, P.id DESC
    """)
    paquetes = []
    for r in cur.fetchall():
        total, completadas, programadas = r[3], r[8], r[9]
        precio, pagado = float(r[4] or 0), float(r[10] or 0)
        paquetes.append({
            "id": r[0], "alumno": r[1], "telefono": r[2], "clases_total": total,
            "precio_total": precio, "fecha_compra": r[5].strftime("%d/%m/%Y"),
            "estado": r[6], "notas": r[7],
            "completadas": completadas, "programadas": programadas,
            "restantes": max(total - completadas, 0),
            "por_agendar": max(total - completadas - programadas, 0),
            "pagado": pagado, "saldo": round(precio - pagado, 2),
        })
    return paquetes


def accion_detalle_paquete(cur, a):
    pid = a_int(a.get("id"), 0)
    cur.execute("""SELECT id, EXTRACT(EPOCH FROM fecha_hora), estado, tipo, duracion_min
                   FROM Clases WHERE paquete_id = %s ORDER BY fecha_hora""", (pid,))
    clases = [{"id": r[0], "fecha": float(r[1]), "estado": r[2], "tipo": r[3], "duracion": r[4]}
              for r in cur.fetchall()]
    cur.execute("SELECT EXTRACT(EPOCH FROM fecha), monto, referencia FROM PagosPaquete WHERE paquete_id = %s ORDER BY fecha",
                (pid,))
    pagos = [{"fecha": float(r[0]), "monto": float(r[1]), "ref": r[2] or ""} for r in cur.fetchall()]
    return {"clases": clases, "pagos": pagos}


def accion_agregar_pago(cur, a):
    pid = a_int(a.get("paquete_id"))
    monto = a_dec(a.get("monto"), 0.0)
    ref = (a.get("referencia") or "").strip()
    if pid is None or monto <= 0:
        raise ErrorNegocio("Indica un monto mayor a 0")
    cur.execute("SELECT 1 FROM Paquetes WHERE id = %s", (pid,))
    if not cur.fetchone():
        raise ErrorNegocio("Paquete no encontrado")
    cur.execute("INSERT INTO PagosPaquete (paquete_id, monto, referencia) VALUES (%s, %s, %s)", (pid, monto, ref))
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# ACCIONES: CLASES
# ---------------------------------------------------------------------------
def accion_crear_clase(cur, a):
    try:
        fecha = datetime.fromisoformat((a.get("fecha_hora") or "").replace("Z", "+00:00"))
    except ValueError:
        raise ErrorNegocio("Fecha y hora no válidas")
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)

    duracion = a_int(a.get("duracion"), 60)
    tipo = a.get("tipo")
    tablas_ids = sorted(set(lista_ids(a.get("tablas"))))
    instructores_ids = sorted(set(lista_ids(a.get("instructores"))))
    paquete_id = a_int(a.get("paquete_id"))
    monto = a_dec(a.get("monto"), 0.0)

    if duracion < 15 or duracion > 480:
        raise ErrorNegocio("La duración debe estar entre 15 minutos y 8 horas")
    if tipo not in TIPOS_CLASE:
        raise ErrorNegocio("Tipo de clase no válido")
    if monto < 0:
        raise ErrorNegocio("El monto no puede ser negativo")

    # Participantes sin repetir
    participantes, vistos = [], set()
    for p in a.getlist("participante"):
        p = p.strip()
        if p and p.lower() not in vistos:
            vistos.add(p.lower())
            participantes.append(p)

    # Paquete: el alumno del paquete participa siempre y la clase no se cobra aparte
    if paquete_id:
        cur.execute("""SELECT A.nombre, P.clases_total, P.estado,
                              (SELECT COUNT(*) FROM Clases C WHERE C.paquete_id = P.id AND C.estado <> 'Cancelada')
                       FROM Paquetes P JOIN Alumnos A ON A.id = P.alumno_id WHERE P.id = %s""", (paquete_id,))
        paq = cur.fetchone()
        if not paq:
            raise ErrorNegocio("Paquete no encontrado")
        if paq[2] != "Activo":
            raise ErrorNegocio("Ese paquete ya no está activo")
        if paq[3] >= paq[1]:
            raise ErrorNegocio("Ese paquete ya tiene todas sus clases agendadas")
        if paq[0].lower() not in vistos:
            participantes.insert(0, paq[0])
        monto = 0.0

    n = len(participantes)
    if tipo == "Individual" and n != 1:
        raise ErrorNegocio("Una clase individual lleva exactamente 1 participante")
    if tipo == "Pareja" and n != 2:
        raise ErrorNegocio("Una clase en pareja lleva exactamente 2 participantes")
    if tipo == "Grupal" and n < 3:
        raise ErrorNegocio("Una clase grupal necesita 3 o más participantes")

    # Tablas e instructores
    if not tablas_ids:
        raise ErrorNegocio("Elige al menos una tabla")
    cur.execute("SELECT COUNT(*) FROM Tablas WHERE id = ANY(%s) AND uso = 'Clases'", (tablas_ids,))
    if cur.fetchone()[0] != len(tablas_ids):
        raise ErrorNegocio("Solo puedes usar tablas marcadas para clases")
    if not instructores_ids:
        raise ErrorNegocio("Elige al menos un instructor")
    cur.execute("SELECT COUNT(*) FROM Instructores WHERE id = ANY(%s) AND activo", (instructores_ids,))
    if cur.fetchone()[0] != len(instructores_ids):
        raise ErrorNegocio("Instructor no válido")

    # Choques de horario
    cur.execute("""SELECT 1 FROM Clases C JOIN Clase_Tablas CT ON CT.clase_id = C.id
                   WHERE CT.tabla_id = ANY(%s) AND C.estado IN ('Programada', 'En curso')
                     AND C.fecha_hora < %s + make_interval(mins => %s)
                     AND C.fecha_hora + make_interval(mins => C.duracion_min) > %s
                   LIMIT 1""", (tablas_ids, fecha, duracion, fecha))
    if cur.fetchone():
        raise ErrorNegocio("Alguna de las tablas ya está en otra clase en ese horario")
    cur.execute("""SELECT 1 FROM Clases C JOIN Clase_Instructores CI ON CI.clase_id = C.id
                   WHERE CI.instructor_id = ANY(%s) AND C.estado IN ('Programada', 'En curso')
                     AND C.fecha_hora < %s + make_interval(mins => %s)
                     AND C.fecha_hora + make_interval(mins => C.duracion_min) > %s
                   LIMIT 1""", (instructores_ids, fecha, duracion, fecha))
    if cur.fetchone():
        raise ErrorNegocio("Algún instructor ya tiene otra clase en ese horario")

    cur.execute(
        """INSERT INTO Clases (fecha_hora, duracion_min, tipo, paquete_id, monto)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (fecha, duracion, tipo, paquete_id, monto),
    )
    clase_id = cur.fetchone()[0]
    for nombre in participantes:
        alumno_id = obtener_o_crear_alumno(cur, nombre)
        cur.execute("INSERT INTO Clase_Participantes (clase_id, alumno_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (clase_id, alumno_id))
    for tid in tablas_ids:
        cur.execute("INSERT INTO Clase_Tablas (clase_id, tabla_id) VALUES (%s, %s)", (clase_id, tid))
    for iid in instructores_ids:
        cur.execute("INSERT INTO Clase_Instructores (clase_id, instructor_id) VALUES (%s, %s)", (clase_id, iid))
    return {"status": "ok", "id": clase_id}


def accion_listar_clases(cur, a):
    filtro = a.get("filtro") or "proximas"
    condiciones, params = [], []
    if filtro == "proximas":
        condiciones.append("C.estado IN ('Programada', 'En curso')")
        orden = "ASC"
    elif filtro == "historial":
        condiciones.append("C.estado IN ('Completada', 'Cancelada')")
        orden = "DESC"
    else:
        orden = "DESC"
    paquete_id = a_int(a.get("paquete_id"))
    if paquete_id:
        condiciones.append("C.paquete_id = %s")
        params.append(paquete_id)
    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""

    cur.execute(f"""
        SELECT C.id, EXTRACT(EPOCH FROM C.fecha_hora), C.duracion_min, C.tipo, C.estado, C.paquete_id, C.monto,
               ARRAY(SELECT A.nombre FROM Clase_Participantes CP JOIN Alumnos A ON A.id = CP.alumno_id
                     WHERE CP.clase_id = C.id ORDER BY A.nombre),
               ARRAY(SELECT I.nombre FROM Clase_Instructores CI JOIN Instructores I ON I.id = CI.instructor_id
                     WHERE CI.clase_id = C.id ORDER BY I.nombre),
               ARRAY(SELECT T.nombre FROM Clase_Tablas CT JOIN Tablas T ON T.id = CT.tabla_id
                     WHERE CT.clase_id = C.id ORDER BY T.id)
        FROM Clases C {where}
        ORDER BY C.fecha_hora {orden}
        LIMIT 100
    """, params)
    return [{
        "id": r[0], "fecha": float(r[1]), "duracion": r[2], "tipo": r[3], "estado": r[4],
        "paquete_id": r[5], "monto": float(r[6] or 0),
        "participantes": r[7], "instructores": r[8], "tablas": r[9],
    } for r in cur.fetchall()]


def accion_cambiar_estado_clase(cur, a):
    clase_id = a_int(a.get("clase_id"))
    nuevo = a.get("estado")
    if clase_id is None or nuevo not in ESTADOS_CLASE:
        raise ErrorNegocio("Datos no válidos")

    cur.execute("SELECT estado, paquete_id FROM Clases WHERE id = %s FOR UPDATE", (clase_id,))
    fila = cur.fetchone()
    if not fila:
        raise ErrorNegocio("Clase no encontrada")
    actual, paquete_id = fila
    if actual in ("Completada", "Cancelada"):
        raise ErrorNegocio(f"La clase ya está {actual.lower()}")
    if nuevo == actual:
        raise ErrorNegocio(f"La clase ya está {actual.lower()}")

    cur.execute("SELECT tabla_id FROM Clase_Tablas WHERE clase_id = %s", (clase_id,))
    tablas_ids = [r[0] for r in cur.fetchall()]

    if nuevo == "En curso":
        cur.execute("SELECT nombre FROM Tablas WHERE id = ANY(%s) AND estado <> 'Disponible'", (tablas_ids,))
        ocupadas = [r[0] for r in cur.fetchall()]
        if ocupadas:
            raise ErrorNegocio("Estas tablas no están disponibles: " + ", ".join(ocupadas))
        cur.execute("UPDATE Tablas SET estado = 'En Uso' WHERE id = ANY(%s)", (tablas_ids,))
    elif actual == "En curso":
        cur.execute("UPDATE Tablas SET estado = 'Disponible' WHERE id = ANY(%s) AND estado = 'En Uso'", (tablas_ids,))

    cur.execute("UPDATE Clases SET estado = %s WHERE id = %s", (nuevo, clase_id))

    # Si el paquete ya completó todas sus clases, se cierra solo
    if paquete_id and nuevo == "Completada":
        cur.execute("""UPDATE Paquetes P SET estado = 'Completado'
                       WHERE P.id = %s
                         AND (SELECT COUNT(*) FROM Clases C WHERE C.paquete_id = P.id AND C.estado = 'Completada')
                             >= P.clases_total""", (paquete_id,))
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# REPORTE DE VENTAS (alquileres + pagos de paquetes + clases sueltas)
# La hora se convierte de UTC (Render) a hora de Lima.
# ---------------------------------------------------------------------------
SQL_MOVIMIENTOS = """
    SELECT fecha, concepto, cliente, ref, monto FROM (
        SELECT (R.fecha_reserva AT TIME ZONE 'UTC') AT TIME ZONE 'America/Lima' AS fecha,
               T.nombre AS concepto, R.cliente_nombre AS cliente,
               COALESCE(R.comprobante_img, '') AS ref, R.monto_pago AS monto
        FROM Reservas R INNER JOIN Tablas T ON R.tabla_id = T.id
        UNION ALL
        SELECT G.fecha AT TIME ZONE 'America/Lima', 'Paquete #' || P.id, A.nombre,
               COALESCE(G.referencia, ''), G.monto
        FROM PagosPaquete G JOIN Paquetes P ON P.id = G.paquete_id JOIN Alumnos A ON A.id = P.alumno_id
        UNION ALL
        SELECT C.fecha_hora AT TIME ZONE 'America/Lima', 'Clase #' || C.id,
               COALESCE((SELECT string_agg(A.nombre, ', ') FROM Clase_Participantes CP
                         JOIN Alumnos A ON A.id = CP.alumno_id WHERE CP.clase_id = C.id), ''),
               '', C.monto
        FROM Clases C WHERE C.paquete_id IS NULL AND C.monto > 0 AND C.estado <> 'Cancelada'
    ) M ORDER BY fecha DESC
"""


def accion_listar_movimientos(cur, a):
    cur.execute(SQL_MOVIMIENTOS)
    return [{"fecha": r[0].strftime("%d/%m %H:%M"), "tabla": r[1], "cliente": r[2],
             "ref": r[3], "monto": float(r[4] or 0)} for r in cur.fetchall()]


ACCIONES = {
    "login": accion_login,
    "listar": accion_listar,
    "obtener_tabla": accion_obtener_tabla,
    "agregar_tabla": accion_agregar_tabla,
    "actualizar_estado": accion_actualizar_estado,
    "insertar_reserva": accion_insertar_reserva,
    "extender_reserva": accion_extender_reserva,
    "listar_instructores": accion_listar_instructores,
    "agregar_instructor": accion_agregar_instructor,
    "crear_paquete": accion_crear_paquete,
    "listar_paquetes": accion_listar_paquetes,
    "detalle_paquete": accion_detalle_paquete,
    "agregar_pago": accion_agregar_pago,
    "crear_clase": accion_crear_clase,
    "listar_clases": accion_listar_clases,
    "cambiar_estado_clase": accion_cambiar_estado_clase,
    "listar_movimientos": accion_listar_movimientos,
}


@app.route('/')
def inicio():
    return jsonify({"status": "ok", "app": "SurfFlow API"})


@app.route('/Servlet', methods=['GET'])
def gateway():
    accion = request.args.get('accion')
    funcion = ACCIONES.get(accion)
    if not funcion:
        return jsonify({"status": "error", "message": "acción no válida"})

    try:
        conn = get_connection()
    except Exception as e:
        return jsonify({"status": "error", "message": f"No hay conexión a la BD: {e}"}), 500

    cursor = conn.cursor()
    try:
        resultado = funcion(cursor, request.args)
        conn.commit()
        return jsonify(resultado)
    except ErrorNegocio as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)})
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)})
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
