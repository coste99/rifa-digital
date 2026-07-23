from flask import Flask, render_template, request, jsonify, redirect, session
import sqlite3
import psycopg2
import psycopg2.extras
from datetime import datetime
import os
from config import *

app = Flask(__name__)
app.secret_key = "rifa2026"

# ==========================
# CONFIGURACIÓN DE BASE DE DATOS (POSTGRESQL / SQLITE)
# ==========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "rifa.db")

def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(db_url)
        return conn, "postgres"
    else:
        conn = sqlite3.connect(DB_PATH)
        return conn, "sqlite"

def get_placeholder(db_type):
    return "%s" if db_type == "postgres" else "?"

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
# BASE DE DATOS INICIALIZACIÓN
# ==========================
def init_db():
    conn, db_type = get_db_connection()
    cursor = conn.cursor()

    pk_type = "SERIAL PRIMARY KEY" if db_type == "postgres" else "INTEGER PRIMARY KEY AUTOINCREMENT"

    # 1. Crear tabla compras
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS compras(
        id {pk_type},
        numero INTEGER UNIQUE,
        nombre TEXT,
        telefono TEXT,
        estado TEXT,
        fecha TEXT,
        valor INTEGER,
        liberaciones INTEGER DEFAULT 0
    );
    """)
    conn.commit()

    # 2. Crear tabla configuracion
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
        fecha_bloqueada TEXT DEFAULT 'NO',
        bloqueada TEXT DEFAULT 'NO'
    );
    """)
    conn.commit()

    # 3. Insertar datos iniciales si no existen
    if db_type == "postgres":
        cursor.execute("""
        INSERT INTO configuracion(id, nombre_rifa, premio, valor, fecha_sorteo, whatsapp, estado)
        VALUES(1, 'GRAN RIFA DIGITAL', '$800.000', '$10.000', '15 Junio 2026', '573001234567', 'Activa')
        ON CONFLICT (id) DO NOTHING;
        """)
    else:
        cursor.execute("""
        INSERT OR IGNORE INTO configuracion(id, nombre_rifa, premio, valor, fecha_sorteo, whatsapp, estado)
        VALUES(1, 'GRAN RIFA DIGITAL', '$800.000', '$10.000', '15 Junio 2026', '573001234567', 'Activa');
        """)

    conn.commit()
    conn.close()

init_db()

# ==========================
# PAGINA PRINCIPAL
# ==========================
@app.route('/')
def inicio():
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT nombre_rifa, premio, valor, fecha_sorteo, whatsapp, estado, ganador, bloqueada
    FROM configuracion
    WHERE id=1
    """)
    config = cursor.fetchone()

    nombre_rifa, premio, valor, fecha_sorteo, whatsapp, estado_rifa, ganador, bloqueada = config
    
    cursor.execute("SELECT numero, estado FROM compras")
    registros = cursor.fetchall()
    conn.close()

    estados = {numero: estado for numero, estado in registros}

    # Genera los números del 0 al 99
    numeros = []
    for i in range(0, TOTAL_NUMEROS):
        estado = estados.get(i, "libre")
        numeros.append({
            "numero": i,
            "estado": estado
        })

    reservados = sum(1 for e in estados.values() if e == "reservado")
    pagados = sum(1 for e in estados.values() if e == "pagado")
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

        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        p = get_placeholder(db_type)
        
        cursor.execute("SELECT bloqueada FROM configuracion WHERE id=1")
        estado_bloqueo = cursor.fetchone()

        if estado_bloqueo and estado_bloqueo[0] == "SI":
            conn.close()
            return jsonify({"success": False, "error": "La rifa ya fue finalizada"})

        cursor.execute(f"""
        INSERT INTO compras(numero, nombre, telefono, estado, fecha, valor)
        VALUES({p}, {p}, {p}, {p}, {p}, {p})
        """, (numero, nombre, telefono, "reservado", datetime.now().strftime("%d/%m/%Y %H:%M"), VALOR_NUMERO))

        conn.commit()
        conn.close()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

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

    conn, db_type = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM compras ORDER BY numero")
    compras = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM compras WHERE estado='reservado'")
    reservados = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM compras WHERE estado='pagado'")
    pagados = cursor.fetchone()[0]

    disponibles = TOTAL_NUMEROS - (reservados + pagados)

    cursor.execute("SELECT COALESCE(SUM(valor), 0) FROM compras WHERE estado='pagado'")
    recaudado = cursor.fetchone()[0]
    
    cursor.execute("SELECT ganador, bloqueada FROM configuracion WHERE id=1")
    datos_rifa = cursor.fetchone()

    ganador = datos_rifa[0]
    bloqueada = datos_rifa[1]
    
    cursor.execute("""
    SELECT nombre_rifa, premio, valor, fecha_sorteo, whatsapp, fecha_bloqueada
    FROM configuracion
    WHERE id=1
    """)

    config = cursor.fetchone()

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

        nombre_rifa_cfg=config[0],
        premio_cfg=config[1],
        valor_cfg=config[2],
        fecha_cfg=config[3],
        whatsapp_cfg=config[4],
        fecha_bloqueada=config[5],
    )

# ==========================
# MARCAR PAGADO
# ==========================
@app.route('/pagado/<int:numero>')
def pagado(numero):
    if not session.get("admin"):
        return redirect("/admin")

    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    p = get_placeholder(db_type)

    cursor.execute("SELECT bloqueada FROM configuracion WHERE id=1")
    if cursor.fetchone()[0] == "SI":
        conn.close()
        return redirect("/panel")

    cursor.execute(f"UPDATE compras SET estado='pagado' WHERE numero={p}", (numero,))

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

    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    p = get_placeholder(db_type)

    cursor.execute("SELECT bloqueada FROM configuracion WHERE id=1")
    if cursor.fetchone()[0] == "SI":
        conn.close()
        return redirect("/panel")
    
    cursor.execute(f"UPDATE compras SET estado='reservado' WHERE numero={p}", (numero,))

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

    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    p = get_placeholder(db_type)

    cursor.execute("SELECT bloqueada FROM configuracion WHERE id=1")
    if cursor.fetchone()[0] == "SI":
        conn.close()
        return redirect("/panel")
    
    cursor.execute(f"SELECT liberaciones FROM compras WHERE numero={p}", (numero,))
    dato = cursor.fetchone()

    if not dato:
        conn.close()
        return redirect("/panel")

    liberaciones = dato[0]

    if liberaciones >= 1:
        conn.close()
        return """
        <h2>❌ Este número ya utilizó su única liberación permitida.</h2>
        <a href='/panel'>Volver al panel</a>
        """

    cursor.execute(f"UPDATE compras SET liberaciones = liberaciones + 1 WHERE numero={p}", (numero,))
    cursor.execute(f"DELETE FROM compras WHERE numero={p}", (numero,))

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
    fecha_sorteo = request.form.get("fecha_sorteo")
    whatsapp = request.form.get("whatsapp")

    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    p = get_placeholder(db_type)

    cursor.execute(f"""
    UPDATE configuracion
    SET nombre_rifa={p},
        premio={p},
        valor={p},
        fecha_sorteo={p},
        whatsapp={p}
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

    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    p = get_placeholder(db_type)

    cursor.execute(f"""
    UPDATE configuracion
    SET ganador={p},
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
