from flask import Flask, render_template, request, jsonify, redirect, session
import sqlite3
from datetime import datetime
import os
from config import *

app = Flask(__name__)
app.secret_key = "rifa2026"

# ==========================
# CONFIGURACIÓN DE RUTAS ABSOLUTAS
# ==========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "rifa.db")

# ==========================
# CONFIGURACION
# ==========================
ADMIN_PASSWORD = "0000"
VALOR_NUMERO = 10000
WHATSAPP = "573001234567"

NOMBRE_RIFA = "GRAN RIFA DIGITAL"
PREMIO = "$800.000"
VALOR = "$10.000"
FECHA_SORTEO = "15 Junio 2026"
HORA_SORTEO = "8:00 PM"

TOTAL_NUMEROS = 100

# ==========================
# BASE DE DATOS
# ==========================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # TABLA COMPRAS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compras(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero INTEGER UNIQUE,
        nombre TEXT,
        telefono TEXT,
        estado TEXT,
        fecha TEXT,
        valor INTEGER
    )
    """)

    # TABLA CONFIGURACION
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS configuracion(
        id INTEGER PRIMARY KEY,
        nombre_rifa TEXT,
        premio TEXT,
        valor TEXT,
        fecha_sorteo TEXT,
        whatsapp TEXT,
        estado TEXT,
        ganador INTEGER DEFAULT 0,
        bloqueada TEXT DEFAULT 'NO'
    )
    """)

    cursor.execute("""
    INSERT OR IGNORE INTO configuracion(
        id,
        nombre_rifa,
        premio,
        valor,
        fecha_sorteo,
        whatsapp,
        estado
    )
    VALUES(
        1,
        'GRAN RIFA DIGITAL',
        '$800.000',
        '$10.000',
        '15 Junio 2026',
        '573001234567',
        'Activa'
    )
    """)

    try:
        cursor.execute("""
        ALTER TABLE configuracion
        ADD COLUMN ganador INTEGER DEFAULT 0
    """)
    except:
        pass

    try:
       cursor.execute("""
       ALTER TABLE configuracion
       ADD COLUMN fecha_bloqueada TEXT DEFAULT 'NO'
    """)
    except:
        pass

    try:
        cursor.execute("""
        ALTER TABLE configuracion
        ADD COLUMN bloqueada TEXT DEFAULT 'NO'
    """)
    except:
        pass

    try:
        cursor.execute("""
        ALTER TABLE compras
        ADD COLUMN liberaciones INTEGER DEFAULT 0
    """)
    except:
        pass

    conn.commit()
    conn.close()

# Inicializamos la base de datos justo aquí para asegurar que las tablas existan
init_db()

# ==========================
# PAGINA PRINCIPAL
# ==========================
@app.route('/')
def inicio():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT
        nombre_rifa,
        premio,
        valor,
        fecha_sorteo,
        whatsapp,
        estado,
        ganador,
        bloqueada
    FROM configuracion
    WHERE id=1
    """)

    config = cursor.fetchone()

    nombre_rifa = config[0]
    premio = config[1]
    valor = config[2]
    fecha_sorteo = config[3]
    whatsapp = config[4]
    estado_rifa = config[5]
    ganador = config[6]
    bloqueada = config[7]
    
    cursor.execute("""
    SELECT numero, estado
    FROM compras
    """)

    registros = cursor.fetchall()
    conn.close()

    estados = {}
    for numero, estado in registros:
        estados[numero] = estado

    # --- CAMBIO AQUÍ: Genera exactamente del 0 al 99 ---
    numeros = []
    for i in range(0, TOTAL_NUMEROS):
        estado = estados.get(i, "libre")
        numeros.append({
            "numero": i,
            "estado": estado
        })

    reservados = 0
    pagados = 0

    for estado in estados.values():
        if estado == "reservado":
            reservados += 1
        elif estado == "pagado":
            pagados += 1

    disponibles = TOTAL_NUMEROS - (reservados + pagados)

    return render_template(
        "index.html",
        numeros=numeros,
        nombre_rifa=nombre_rifa,
        premio=premio,
        valor=valor,
        fecha=fecha_sorteo,
        whatsapp=whatsapp,
        estado_rifa=estado_rifa,
        reservados=reservados,
        pagados=pagados,
        disponibles=disponibles,
        ganador=ganador,
        bloqueada=bloqueada
    )

# ==========================
# RESERVAR NUMERO
# ==========================
@app.route('/reservar', methods=['POST'])
def reservar():
    try:
        datos = request.get_json()
        numero = int(datos["numero"])
        nombre = datos["nombre"]
        telefono = datos["telefono"]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT bloqueada
        FROM configuracion
        WHERE id=1
        """)

        estado_bloqueo = cursor.fetchone()

        if estado_bloqueo and estado_bloqueo[0] == "SI":
            conn.close()
            return jsonify({
                "success": False,
                "error": "La rifa ya fue finalizada"
            })
        cursor.execute("""
        INSERT INTO compras(
            numero,
            nombre,
            telefono,
            estado,
            fecha,
            valor
        )
        VALUES(?,?,?,?,?,?)
        """, (
            numero,
            nombre,
            telefono,
            "reservado",
            datetime.now().strftime("%d/%m/%Y %H:%M"),
            VALOR_NUMERO
        ))

        conn.commit()
        conn.close()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

# ==========================
# LOGIN ADMIN
# ==========================
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/panel")

    return render_template("admin_login.html")

# ==========================
# PANEL ADMIN
# ==========================
@app.route('/panel')
def panel():
    if not session.get("admin"):
        return redirect("/admin")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM compras
    ORDER BY numero
    """)
    compras = cursor.fetchall()

    cursor.execute("""
    SELECT COUNT(*)
    FROM compras
    WHERE estado='reservado'
    """)
    reservados = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM compras
    WHERE estado='pagado'
    """)
    pagados = cursor.fetchone()[0]

    disponibles = TOTAL_NUMEROS - (reservados + pagados)

    cursor.execute("""
    SELECT IFNULL(SUM(valor),0)
    FROM compras
    WHERE estado='pagado'
    """)
    recaudado = cursor.fetchone()[0]
    
    cursor.execute("""
    SELECT ganador, bloqueada
    FROM configuracion
    WHERE id=1
    """)

    datos_rifa = cursor.fetchone()

    ganador = datos_rifa[0]
    bloqueada = datos_rifa[1]
    
    cursor.execute("""
    SELECT
       nombre_rifa,
       premio,
       valor,
       fecha_sorteo,
       whatsapp,
       fecha_bloqueada
    FROM configuracion
    WHERE id=1
    """)

    config = cursor.fetchone()

    nombre_rifa_cfg = config[0]
    premio_cfg = config[1]
    valor_cfg = config[2]
    fecha_cfg = config[3]
    whatsapp_cfg = config[4]
    fecha_bloqueada = config[5]

    conn.close()

    return render_template(
        "panel.html",
        compras=compras,
        reservados=reservados,
        pagados=pagados,
        disponibles=disponibles,
        recaudado=recaudado,
        total_numeros=TOTAL_NUMEROS,
        ganador=ganador,
        bloqueada=bloqueada,

        nombre_rifa_cfg=nombre_rifa_cfg,
        premio_cfg=premio_cfg,
        valor_cfg=valor_cfg,
        fecha_cfg=fecha_cfg,
        whatsapp_cfg=whatsapp_cfg,
        fecha_bloqueada=fecha_bloqueada,
    )

# ==========================
# MARCAR PAGADO
# ==========================
@app.route('/pagado/<int:numero>')
def pagado(numero):
    if not session.get("admin"):
        return redirect("/admin")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT bloqueada
    FROM configuracion
    WHERE id=1
    """)

    if cursor.fetchone()[0] == "SI":
        conn.close()
        return redirect("/panel")

    cursor.execute("""
    UPDATE compras
    SET estado='pagado'
    WHERE numero=?
    """, (numero,))

    conn.commit()
    conn.close()

    return redirect("/panel")

# ==========================
# MARCAR RESERVADO
# ==========================
@app.route('/reservado/<int:numero>')
def reservado(numero):
    if not session.get("admin"):
        return redirect("/admin")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT bloqueada
    FROM configuracion
    WHERE id=1
    """)

    if cursor.fetchone()[0] == "SI":
        conn.close()
        return redirect("/panel")
    
    cursor.execute("""
    UPDATE compras
    SET estado='reservado'
    WHERE numero=?
    """, (numero,))

    conn.commit()
    conn.close()

    return redirect("/panel")

# ==========================
# LIBERAR NUMERO
# ==========================
@app.route('/liberar/<int:numero>')
def liberar(numero):

    if not session.get("admin"):
        return redirect("/admin")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT bloqueada
    FROM configuracion
    WHERE id=1
    """)

    if cursor.fetchone()[0] == "SI":
        conn.close()
        return redirect("/panel")
    
    cursor.execute("""
    SELECT liberaciones
    FROM compras
    WHERE numero=?
    """, (numero,))

    dato = cursor.fetchone()

    if not dato:
        conn.close()
        return redirect("/panel")

    liberaciones = dato[0]

    if liberaciones >= 1:
        conn.close()
        return """
        2. Este número ya utilizó su única liberación permitida.
        <a href='/panel'>Volver al panel</a>
        """

    cursor.execute("""
    UPDATE compras
    SET liberaciones = liberaciones + 1
    WHERE numero=?
    """, (numero,))

    cursor.execute("""
    DELETE FROM compras
    WHERE numero=?
    """, (numero,))

    conn.commit()
    conn.close()

    return redirect("/panel")


# ==========================
# GUARDAR CONFIGURACION
# ==========================
@app.route('/guardar_configuracion', methods=['POST'])
def guardar_configuracion():

    if not session.get("admin"):
        return redirect("/admin")

    nombre_rifa = request.form.get("nombre_rifa")
    premio = request.form.get("premio")
    valor = request.form.get("valor")
    fecha_sorteo = request.form.get("fecha_sorteo") # --- CORREGIDO: recibe la fecha ---
    whatsapp = request.form.get("whatsapp")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- CORREGIDO: Actualiza la fecha_sorteo en la DB ---
    cursor.execute("""
    UPDATE configuracion
    SET nombre_rifa=?,
        premio=?,
        valor=?,
        fecha_sorteo=?,
        whatsapp=?
    WHERE id=1
    """, (
        nombre_rifa,
        premio,
        valor,
        fecha_sorteo,
        whatsapp
    ))

    conn.commit()
    conn.close()

    return redirect("/panel")

# ==========================
# FINALIZAR RIFA & LOGOUT
# ==========================

@app.route('/finalizar_rifa/<int:numero>')
def finalizar_rifa(numero):

    if not session.get("admin"):
        return redirect("/admin")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE configuracion
    SET ganador=?,
        bloqueada='SI',
        estado='Finalizada'
    WHERE id=1
    """, (numero,))

    conn.commit()
    conn.close()

    return redirect("/panel")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ==========================
# EJECUTAR
# ==========================
if __name__ == "__main__":
    app.run(debug=True)
