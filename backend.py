# backend.py
from datetime import datetime, timedelta
from models import Circuit
# Importamos la lógica de la base de datos desde el nuevo módulo
from database import get_db, init_db 

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
        name = name.strip().upper()
        nomenclature = nomenclature.strip().upper()

        circuit = conn.execute('''
            SELECT * FROM circuits WHERE UPPER(name)=? AND UPPER(nomenclature)=?
        ''', (name, nomenclature)).fetchone()

        if not circuit:
            return False
        
        local_time = datetime.now().strftime('%Y-%m-%d %H:%M')

        if action == 'consignar':
            conn.execute('''
                UPDATE circuits
                SET is_consigned = 1, status = 'CONSIGNADO', amps = 0.0, mw = 0.0,
                    start_time = '', end_time = '', duration = ''
                WHERE id=?
            ''', (circuit['id'],))

            conn.execute('''
                INSERT INTO history (timestamp, name, nomenclature, event, details, mw, recovered_mw, start_time, end_time, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (local_time, circuit['name'], circuit['nomenclature'], 'CONSIGNACION', 'Circuito consignado manualmente', 0.0, 0.0, '', '', '-'))

        elif action == 'liberar':
            conn.execute('''
                UPDATE circuits
                SET is_consigned = 0, status = 'ACTIVO', amps = 0.0, mw = 0.0,
                    start_time = '', end_time = '', duration = ''
                WHERE id=?
            ''', (circuit['id'],))

            conn.execute('''
                INSERT INTO history (timestamp, name, nomenclature, event, details, mw, recovered_mw, start_time, end_time, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (local_time, circuit['name'], circuit['nomenclature'], 'LIBERACION', 'Circuito liberado nuevamente al sistema', 0.0, 0.0, '', '', '-'))

        conn.commit()
        return True
    except Exception as e:
        print("ERROR EN CONSIGNACION:", e)
    finally:
        conn.close()

def calcular_duracion_hm(start_time_str, end_time_str):
    """
    Calcula la hora en formato 'HH:MM'.
    """
    if not start_time_str or not end_time_str or start_time_str in ['--:--', 'None', '']:
        return "--"
    
    try:
        # Parsear las horas y minutos
        start = datetime.strptime(start_time_str.strip(), "%H:%M")
        end = datetime.strptime(end_time_str.strip(), "%H:%M")
        
        # Si la hora de fin es menor, significa que la maniobra pasó la medianoche
        if end < start:
            end += timedelta(days=1)
            
        diff = end - start
        total_segundos = int(diff.total_seconds())
        
        horas = total_segundos // 3600
        minutos = (total_segundos % 3600) // 60
        
        return f"{horas}h {minutos}m"
    except Exception as e:
        print(f"Error al calcular duración: {e}")
        return "--"

def update_monitor(c_id, status, start, end, amps):
    conn = get_db()
    curr = conn.execute('SELECT * FROM circuits WHERE id=?', (c_id,)).fetchone()
    if not curr: 
        conn.close()
        return

    # 🌟 PROTECCIÓN ANTI-CRASH: Si el amperaje viene vacío o inválido, forzamos un 0.0
    try:
        amps_val = float(amps)
    except ValueError:
        amps_val = 0.0

    current_time = datetime.now().strftime('%H:%M')

    if end.strip():
        if end > current_time or not start.strip():
            conn.close()
            return
        
    if end.strip():
        duration_val = Circuit.calculate_duration(start, end)
        duration_minutes = int(duration_val.split()[0])
        
        #Calcula el string formateado para la tabla history
        duration_hm = calcular_duracion_hm(start, end)

        c_obj = Circuit(voltage=curr['voltage'], amps=amps_val)
        mw_snapshot = c_obj.mw
        local_time = datetime.now().strftime('%Y-%m-%d %H:%M')

        if status in ['PAC', 'FALLA', 'MANTENIMIENTO']:
            conn.execute('''
                INSERT INTO history (timestamp, name, nomenclature, event, details, mw, recovered_mw, start_time, end_time, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (local_time, curr['name'], curr['nomenclature'], status, f"Desde {start} hasta {end}", mw_snapshot, mw_snapshot, start, end, duration_hm))    
            
        new_pac = curr['pac']
        if status == 'PAC':
            new_pac += 1

        time_range = f"{start} - {end}"
        conn.execute('''
            UPDATE circuits 
            SET status='ACTIVO', start_time='', end_time='', duration=?, amps=0.0, mw=0.0, pac=?, last_outage_duration=? 
            WHERE id=?
        ''', (time_range, new_pac, duration_minutes, c_id))
    else:
        # Usamos nuestra variable segura amps_val
        c_obj = Circuit(voltage=curr['voltage'], amps=amps_val)
        conn.execute('''
            UPDATE circuits SET status=?, start_time=?, amps=?, mw=? WHERE id=?
        ''', (status, start, amps_val, c_obj.mw, c_id))
    
    conn.commit()
    conn.close()

def get_mw_stats():
    conn = get_db()
    today = datetime.now().strftime('%Y-%m-%d')

    pac_activo = conn.execute("""
        SELECT SUM(mw) FROM circuits WHERE status IN ('PAC', 'FALLA', 'MANTENIMIENTO')
    """).fetchone()[0] or 0.0

    recuperados = conn.execute("""
        SELECT SUM(mw) FROM history WHERE timestamp LIKE ?
    """, (f"{today}%",)).fetchone()[0] or 0.0

    total_dia = pac_activo + recuperados
    conn.close()

    return round(total_dia, 2), round(pac_activo, 2), round(recuperados, 2)

def get_all_circuits():
    conn = get_db()
    query = '''
    SELECT * FROM circuits
    ORDER BY block ASC, CASE WHEN status = 'ACTIVO' THEN 0 ELSE 1 END ASC, last_outage_duration ASC, nomenclature ASC
    '''
    rows = conn.execute(query).fetchall()
    conn.close() 
    
    all_circuits = []
    for r in rows:
        c = Circuit(**dict(r))
        if c.status == 'ACTIVO':
            c.display_duration = f"{c.last_outage_duration} min" if c.last_outage_duration and int(c.last_outage_duration) > 0 else "--"
            c.display_range = r['duration'] if r['duration'] and r['duration'].strip() else "--:-- - --:--"
        else:
            c.display_duration = c.outage_time if c.outage_time else "--"
            c.display_range = f"Desde {c.start_time}" if c.start_time else "--:--"
        all_circuits.append(c)

    activos = [c for c in all_circuits if c.is_consigned == 0]
    consignados = [c for c in all_circuits if c.is_consigned == 1]
    return activos, consignados, all_circuits
    
def get_grouped_history():
    conn = get_db()
    circuits = conn.execute('SELECT DISTINCT name, nomenclature FROM history').fetchall()
    grouped_data = []
    for c in circuits:
        events = conn.execute('''
            SELECT * FROM history WHERE name=? AND nomenclature=? ORDER BY timestamp DESC
        ''', (c['name'], c['nomenclature'])).fetchall()
        grouped_data.append({
            'name': c['name'], 'nomenclature': c['nomenclature'], 'events': events, 'count': len(events)
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

def reset_system_states():
    conn = get_db()
    
    # 1. Reseteamos todos los parámetros eléctricos y de estado de los circuitos
    conn.execute('''
        UPDATE circuits 
        SET 
            status = 'ACTIVO', 
            amps = 0.0,
            mw = 0.0,
            start_time = '',
            end_time = '',
            duration = '',
            pac = 0,
            last_outage_duration = 0,
            is_consigned = 0
    ''')

    # 2. BORRADO TOTAL: Eliminamos el historial. Esto obligará a las tarjetas a mostrar 0.0
    conn.execute('DELETE FROM history')

    conn.commit()
    conn.close()

def perform_shift_change():
    conn = get_db()
    # Capturamos la fecha de hoy (Ej: 2026-06-22)
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    circuits = conn.execute('SELECT * FROM circuits').fetchall()
    
    for c in circuits:
        # REGLA 1: Si el circuito está afectado actualmente (PAC, FALLA), no se toca nada.
        if c['status'] != 'ACTIVO':
            continue
            
        # REGLA 2: Si está ACTIVO, buscamos si tiene un registro en la tabla history de HOY.
        history_today = conn.execute('''
            SELECT 1 FROM history 
            WHERE name = ? AND timestamp LIKE ?
            LIMIT 1
        ''', (c['name'], f"{today_date}%")).fetchone()
        
        # REGLA 3: Si no hay registro de hoy, significa que la información es de guardias anteriores. La limpiamos.
        if not history_today:
            conn.execute('''
                UPDATE circuits 
                SET amps = 0.0,
                mw = 0.0,
                start_time = '',
                end_time = '',
                duration = ''
                WHERE id = ?
            ''', (c['id'],))
            
    conn.commit()
    conn.close()