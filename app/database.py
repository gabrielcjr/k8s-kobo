import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_DIR = os.environ.get("DATA_DIR", "/data")
if not os.path.exists(DB_DIR):
    try:
        os.makedirs(DB_DIR, exist_ok=True)
    except Exception:
        DB_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(DB_DIR, "kobo.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid TEXT UNIQUE NOT NULL,
        form_id TEXT NOT NULL DEFAULT 'a7FqboN3tiXKPo6hSc8MzJ',
        version TEXT NOT NULL DEFAULT '32 (2025-09-12 17:50:03)',
        data_date TEXT,
        nome TEXT,
        idade INTEGER,
        telefone TEXT,
        genero TEXT,
        recebeu_jesus TEXT,
        endereco TEXT,
        geopoint TEXT,
        latitude REAL,
        longitude REAL,
        altitude REAL,
        precision REAL,
        observacoes TEXT,
        missionario TEXT,
        device_id TEXT,
        submitted_by TEXT DEFAULT 'renovamechurch',
        submission_time TEXT NOT NULL,
        source TEXT DEFAULT 'kobo_collect',
        raw_xml TEXT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_time ON submissions(submission_time);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_missionario ON submissions(missionario);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recebeu_jesus ON submissions(recebeu_jesus);")
    conn.commit()
    conn.close()

def parse_geopoint(geopoint_str: Optional[str]):
    if not geopoint_str:
        return None, None, None, None
    parts = geopoint_str.strip().split()
    lat = float(parts[0]) if len(parts) > 0 and parts[0] != "" else None
    lon = float(parts[1]) if len(parts) > 1 and parts[1] != "" else None
    alt = float(parts[2]) if len(parts) > 2 and parts[2] != "" else None
    acc = float(parts[3]) if len(parts) > 3 and parts[3] != "" else None
    return lat, lon, alt, acc

def insert_submission(
    uuid: str,
    form_id: str,
    version: str,
    data_date: Optional[str],
    nome: Optional[str],
    idade: Optional[int],
    telefone: Optional[str],
    genero: Optional[str],
    recebeu_jesus: Optional[str],
    endereco: Optional[str],
    geopoint: Optional[str],
    observacoes: Optional[str],
    missionario: Optional[str],
    device_id: Optional[str],
    submitted_by: str = "renovamechurch",
    source: str = "kobo_collect",
    raw_xml: Optional[str] = None
) -> int:
    lat, lon, alt, acc = parse_geopoint(geopoint)
    sub_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO submissions (
        uuid, form_id, version, data_date, nome, idade, telefone,
        genero, recebeu_jesus, endereco, geopoint, latitude, longitude,
        altitude, precision, observacoes, missionario, device_id,
        submitted_by, submission_time, source, raw_xml
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        uuid, form_id, version, data_date, nome, idade, telefone,
        genero, recebeu_jesus, endereco, geopoint, lat, lon,
        alt, acc, observacoes, missionario, device_id,
        submitted_by, sub_time, source, raw_xml
    ))
    conn.commit()
    inserted_id = cursor.lastrowid
    conn.close()
    return inserted_id

def get_all_submissions() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM submissions ORDER BY id DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_submission_by_uuid(uuid: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM submissions WHERE uuid = ?", (uuid,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_stats() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM submissions")
    total = cursor.fetchone()[0]

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM submissions WHERE submission_time LIKE ?", (f"{today_str}%",))
    today_count = cursor.fetchone()[0]

    cursor.execute("SELECT recebeu_jesus, COUNT(*) FROM submissions GROUP BY recebeu_jesus")
    jesus_stats = {r[0] or "Não especificado": r[1] for r in cursor.fetchall()}

    cursor.execute("SELECT genero, COUNT(*) FROM submissions GROUP BY genero")
    gender_stats = {r[0] or "Não especificado": r[1] for r in cursor.fetchall()}

    cursor.execute("SELECT missionario, COUNT(*) as cnt FROM submissions WHERE missionario IS NOT NULL GROUP BY missionario ORDER BY cnt DESC LIMIT 10")
    top_missionaries = [{"name": r[0], "count": r[1]} for r in cursor.fetchall()]

    conn.close()
    return {
        "total": total,
        "today": today_count,
        "jesus_stats": jesus_stats,
        "gender_stats": gender_stats,
        "top_missionaries": top_missionaries
    }
