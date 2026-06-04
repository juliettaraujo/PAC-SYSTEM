import sqlite3
import os
from models import Circuit
from datetime import datetime

DB_PATH = 'data/circuits.db'

def get_db():
    # El timeout evita errores de "database is locked"
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs('data', exist_ok=True)
    conn = get_db()
    
    # Tabla principal
    conn.execute('''
        CREATE TABLE IF NOT EXISTS circuits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, nomenclature TEXT, voltage REAL, block TEXT,
            amps REAL DEFAULT 0.0, status TEXT DEFAULT 'ACTIVO',
            start_time TEXT DEFAULT '', end_time TEXT DEFAULT '',
            duration TEXT DEFAULT '', mw REAL DEFAULT 0.0,
            pac INTEGER DEFAULT 0, is_consigned INTEGER DEFAULT 0, last_outage_duration INTEGER DEFAULT 0
        )
    ''')
    
    # Tabla de historial 
    # Tabla de historial técnico
    conn.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        name TEXT,
        nomenclature TEXT,
        event TEXT,
        details TEXT,
        mw REAL,
        recovered_mw REAL DEFAULT 0.0,
        start_time TEXT,
        end_time TEXT,
        duration TEXT
    )
''')
    conn.commit()
    conn.close()

def calculate_duration(start_time, end_time):
    """
    Calcula duración entre hora inicio y fin.
    Retorna:
    - minutos totales
    - texto visual
    """

    if not start_time or not end_time:
        return {
            "minutes": 0,
            "label": "--",
            "range": "--:-- - --:--"
        }

    try:
        fmt = "%H:%M"

        start = datetime.strptime(start_time, fmt)
        end = datetime.strptime(end_time, fmt)

        diff = end - start

        minutes = int(diff.total_seconds() / 60)

        # Si cruza medianoche
        if minutes < 0:
            minutes += 1440

        hours = minutes // 60
        mins = minutes % 60

        if hours > 0:
            label = f"{hours}h {mins}min"
        else:
            label = f"{mins}min"

        return {
            "label": label,
            "range": f"{start_time} - {end_time}"
        }

    except:
        return {
            "minutes": 0,
            "label": "--",
            "range": "--:-- - --:--"
        }

# --- FUNCIONES DE CONFIGURACIÓN ---

def add_circuit(name, nomenclature, voltage, block):
    conn = get_db()
    conn.execute('''
        INSERT INTO circuits (name, nomenclature, voltage, block)
        VALUES (?, ?, ?, ?)
    ''', (name.upper(), nomenclature.upper(), float(voltage), block.upper()))
    conn.commit()
    conn.close()

def update_circuit(c_id, name, nomenclature, voltage, block, amps):
    conn = get_db()
    c_obj = Circuit(voltage=voltage, amps=float(amps))
    conn.execute('''
        UPDATE circuits 
        SET name=?, nomenclature=?, voltage=?, block=?, amps=?, mw=?
        WHERE id=?
    ''', (name.upper(), nomenclature.upper(), float(voltage), block.upper(), float(amps), c_obj.mw, c_id))
    conn.commit()
    conn.close()

def delete_circuit(c_id):
    conn = get_db()
    conn.execute('DELETE FROM circuits WHERE id=?', (c_id,))
    conn.commit()
    conn.close()

def toggle_consignation(name, nomenclature, action):

    conn = get_db()

    try:

        # =========================
        # NORMALIZAR DATOS
        # =========================

        name = name.strip().upper()
        nomenclature = nomenclature.strip().upper()

        # =========================
        # BUSCAR CIRCUITO
        # =========================

        circuit = conn.execute('''
            SELECT * FROM circuits
            WHERE UPPER(name)=?
            AND UPPER(nomenclature)=?
        ''', (name, nomenclature)).fetchone()

        # Si no existe
        if not circuit:
            print("Circuito no encontrado")
            return False
        
        local_time = datetime.now().strftime('%Y-%m-%d %H:%M')

        # =========================
        # CONSIGNAR
        # =========================

        if action == 'consignar':

            conn.execute('''
                UPDATE circuits
                SET
                    is_consigned = 1,
                    status = 'CONSIGNADO',
                    amps = 0.0,
                    mw = 0.0,
                    start_time = '',
                    end_time = '',
                    duration = ''
                WHERE id=?
            ''', (circuit['id'],))

            conn.execute('''
                INSERT INTO history (
                    timestamp,
                    name,
                    nomenclature,
                    event,
                    details,
                    mw,
                    recovered_mw,
                    start_time,
                    end_time,
                    duration
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                local_time,
                circuit['name'],
                circuit['nomenclature'],
                'CONSIGNACION',
                'Circuito consignado manualmente',
                0.0,
                0.0,
                '',
                '',
                '0 min'
            ))

        # =========================
        # LIBERAR
        # =========================

        elif action == 'liberar':

            conn.execute('''
                UPDATE circuits
                SET
                    is_consigned = 0,
                    status = 'ACTIVO',
                    amps = 0.0,
                    mw = 0.0,
                    start_time = '',
                    end_time = '',
                    duration = ''
                WHERE id=?
            ''', (circuit['id'],))

            conn.execute('''
                INSERT INTO history (
                    timestamp,
                    name,
                    nomenclature,
                    event,
                    details,
                    mw,
                    recovered_mw,
                    start_time,
                    end_time,
                    duration
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                local_time,
                circuit['name'],
                circuit['nomenclature'],
                'LIBERACION',
                'Circuito liberado nuevamente al sistema',
                0.0,
                0.0,
                '',
                '',
                '0 min'
            ))

        conn.commit()
        return True

    except Exception as e:
        print("ERROR EN CONSIGNACION:", e)

    finally:
        conn.close()

# --- LÓGICA DEL MONITOR Y ESTADÍSTICAS ---

def update_monitor(c_id, status, start, end, amps):
    conn = get_db()
    curr = conn.execute('SELECT * FROM circuits WHERE id=?', (c_id,)).fetchone()
    if not curr: 
        conn.close()
        return
    # =========================
    # VALIDACIÓN DE HORAS
    # =========================

    current_time = datetime.now().strftime('%H:%M')

    # No permitir horas futuras
    if end.strip():

        # Hora de cierre mayor a hora actual
        if end > current_time:
            conn.close()
            return

        # Validar que inicio exista
        if not start.strip():
            conn.close()
            return
        
    # Si se indica hora de cierre, se mueve al historial y se resetea el circuito
    if end.strip():
        duration_val = Circuit.calculate_duration(start, end)
        # CONVERTIR DURACION A MINUTOS
        duration_minutes = int(duration_val.split()[0])
        c_obj = Circuit(
            voltage=curr['voltage'],
            amps=float(amps)
        )
        mw_snapshot = c_obj.mw
        local_time = datetime.now().strftime('%Y-%m-%d %H:%M')

        # Solo guardamos en historial si no es el estado 'ACTIVO' por defecto
        if status in ['PAC', 'FALLA', 'MANTENIMIENTO']:
            
            conn.execute('''
    INSERT INTO history (timestamp, name, nomenclature, event, details, mw, recovered_mw, start_time, end_time, duration)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    local_time, curr['name'], curr['nomenclature'], status, f"Desde {start} hasta {end}", mw_snapshot, mw_snapshot, start, end, duration_val
))    
            
        new_pac = curr['pac']
        if status == 'PAC':
            new_pac += 1

        # NUEVO: Creamos el texto del rango de horas del último corte
        time_range = f"{start} - {end}"

        # MODIFICADO: Guardamos 'time_range' en la columna 'duration' en lugar de limpiarla con ''
        conn.execute('''
            UPDATE circuits 
            SET status='ACTIVO', start_time='', end_time='', duration=?, amps=0.0, mw=0.0, pac=?, last_outage_duration=? 
            WHERE id=?
        ''', (time_range, new_pac, duration_minutes, c_id))
    else:
        # Actualización en tiempo real (mientras sigue fuera de servicio)
        c_obj = Circuit(voltage=curr['voltage'], amps=float(amps))
        conn.execute('''
            UPDATE circuits SET status=?, start_time=?, amps=?, mw=? WHERE id=?
        ''', (status, start, float(amps), c_obj.mw, c_id))
    
    conn.commit()
    conn.close()

def get_mw_stats():

    conn = get_db()

    today = datetime.now().strftime('%Y-%m-%d')

    # =========================================
    # MW ACTUALMENTE FUERA DE SERVICIO
    # =========================================

    pac_activo = conn.execute("""

        SELECT SUM(mw)
        FROM circuits
        WHERE status IN ('PAC', 'FALLA', 'MANTENIMIENTO')

    """).fetchone()[0] or 0.0

    # =========================================
    # MW RECUPERADOS DEL DIA
    # =========================================

    recuperados = conn.execute("""

        SELECT SUM(mw)
        FROM history
        WHERE timestamp LIKE ?

    """, (f"{today}%",)).fetchone()[0] or 0.0

    # =========================================
    # CARGA TOTAL DEL DIA
    # =========================================

    total_dia = pac_activo + recuperados

    conn.close()

    return (
        round(total_dia, 2),
        round(pac_activo, 2),
        round(recuperados, 2)
    )

def get_all_circuits():
    conn = get_db()
    query = '''
    SELECT * FROM circuits
    ORDER BY
    block ASC,
    CASE
        WHEN status = 'ACTIVO' THEN 0
        ELSE 1
    END ASC,
    last_outage_duration ASC,
    nomenclature ASC
    '''
    rows = conn.execute(query).fetchall()
    conn.close() 
    
    all_circuits = []
    for r in rows:
        c = Circuit(**dict(r))
        
        if c.status == 'ACTIVO':
            # 1. Asignar Duración Histórica
            if c.last_outage_duration and int(c.last_outage_duration) > 0:
                c.display_duration = f"{c.last_outage_duration} min"
            else:
                c.display_duration = "--"
            
            # 2. Asignar Rango Histórico (leído desde la columna duration de la fila 'r')
            if r['duration'] and r['duration'].strip():
                c.display_range = r['duration']
            else:
                c.display_range = "--:-- - --:--"
        else:
            # Si está fuera de servicio (PAC, FALLA, MANTENIMIENTO)
            # Usamos el tiempo en vivo de models.py y el inicio dinámico
            c.display_duration = c.outage_time if c.outage_time else "--"
            c.display_range = f"Desde {c.start_time}" if c.start_time else "--:--"
            
        all_circuits.append(c)

    # Separar las listas para el frontend
    activos = [c for c in all_circuits if c.is_consigned == 0]
    consignados = [c for c in all_circuits if c.is_consigned == 1]
    
    return activos, consignados, all_circuits
    
def get_grouped_history():
    conn = get_db()
    circuits = conn.execute('SELECT DISTINCT name, nomenclature FROM history').fetchall()
    grouped_data = []
    for c in circuits:
        events = conn.execute('''
            SELECT * FROM history WHERE name=? AND nomenclature=? 
            ORDER BY timestamp DESC
        ''', (c['name'], c['nomenclature'])).fetchall()
        grouped_data.append({
            'name': c['name'], 
            'nomenclature': c['nomenclature'], 
            'events': events, 
            'count': len(events)
        })
    conn.close()
    return grouped_data

def delete_history_item(h_id):
    conn = get_db()
    conn.execute('DELETE FROM history WHERE id=?', (h_id,))
    conn.commit()
    conn.close()

def clear_all_history():
    conn = get_db()
    conn.execute("DELETE FROM history")
    conn.commit()
    conn.close()