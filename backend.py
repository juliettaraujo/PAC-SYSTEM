# backend.py
from datetime import datetime
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
            ''', (local_time, circuit['name'], circuit['nomenclature'], 'CONSIGNACION', 'Circuito consignado manualmente', 0.0, 0.0, '', '', '0 min'))

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
            ''', (local_time, circuit['name'], circuit['nomenclature'], 'LIBERACION', 'Circuito liberado nuevamente al sistema', 0.0, 0.0, '', '', '0 min'))

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

    current_time = datetime.now().strftime('%H:%M')

    if end.strip():
        if end > current_time or not start.strip():
            conn.close()
            return
        
    if end.strip():
        duration_val = Circuit.calculate_duration(start, end)
        duration_minutes = int(duration_val.split()[0])
        c_obj = Circuit(voltage=curr['voltage'], amps=float(amps))
        mw_snapshot = c_obj.mw
        local_time = datetime.now().strftime('%Y-%m-%d %H:%M')

        if status in ['PAC', 'FALLA', 'MANTENIMIENTO']:
            conn.execute('''
                INSERT INTO history (timestamp, name, nomenclature, event, details, mw, recovered_mw, start_time, end_time, duration)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (local_time, curr['name'], curr['nomenclature'], status, f"Desde {start} hasta {end}", mw_snapshot, mw_snapshot, start, end, duration_val))    
            
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
        c_obj = Circuit(voltage=curr['voltage'], amps=float(amps))
        conn.execute('''
            UPDATE circuits SET status=?, start_time=?, amps=?, mw=? WHERE id=?
        ''', (status, start, float(amps), c_obj.mw, c_id))
    
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
    # Modificamos solo las variables operativas, dejando intactos los datos del circuito
    conn.execute('''
        UPDATE circuits 
        SET status = 'ACTIVO', 
            amps = 0.0,
            mw = 0.0,
            start_time = '',
            end_time = '',
            duration = '',
            pac = 0,
            last_outage_duration = 0
    ''')

    conn.execute("DELETE FROM history")

    conn.commit()
    conn.close()