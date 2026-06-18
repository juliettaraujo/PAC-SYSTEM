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