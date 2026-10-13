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
        raw_xml TEXT,
        cidade TEXT DEFAULT 'Cruz das Almas',
        povoado TEXT DEFAULT 'Centro',
        acao TEXT DEFAULT ''
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sub_time ON submissions(submission_time);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_missionario ON submissions(missionario);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recebeu_jesus ON submissions(recebeu_jesus);")

    # Settings table for active action, city, and neighborhood
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    # Check for existing table migration
    cursor.execute("PRAGMA table_info(submissions)")
    existing_cols = [r["name"] for r in cursor.fetchall()]
    if "cidade" not in existing_cols:
        cursor.execute("ALTER TABLE submissions ADD COLUMN cidade TEXT DEFAULT 'Cruz das Almas'")
    if "povoado" not in existing_cols:
        cursor.execute("ALTER TABLE submissions ADD COLUMN povoado TEXT DEFAULT 'Centro'")
    if "acao" not in existing_cols:
        cursor.execute("ALTER TABLE submissions ADD COLUMN acao TEXT DEFAULT ''")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cidade ON submissions(cidade);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_povoado ON submissions(povoado);")

    # Defaults for active action if not set
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('active_cidade', 'Cruz das Almas')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('active_povoado', 'Centro')")
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('active_acao', 'Missão Cruz das Almas')")

    conn.commit()
    conn.close()

def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (key, value))
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
    raw_xml: Optional[str] = None,
    cidade: Optional[str] = None,
    povoado: Optional[str] = None,
    acao: Optional[str] = None
) -> int:
    lat, lon, alt, acc = parse_geopoint(geopoint)
    sub_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    final_cidade = (cidade or "").strip() or get_setting("active_cidade", "Cruz das Almas")
    final_povoado = (povoado or "").strip() or get_setting("active_povoado", "Centro")
    final_acao = (acao or "").strip() or get_setting("active_acao", "Missão Cruz das Almas")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO submissions (
        uuid, form_id, version, data_date, nome, idade, telefone,
        genero, recebeu_jesus, endereco, geopoint, latitude, longitude,
        altitude, precision, observacoes, missionario, device_id,
        submitted_by, submission_time, source, raw_xml,
        cidade, povoado, acao
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        uuid, form_id, version, data_date, nome, idade, telefone,
        genero, recebeu_jesus, endereco, geopoint, lat, lon,
        alt, acc, observacoes, missionario, device_id,
        submitted_by, sub_time, source, raw_xml,
        final_cidade, final_povoado, final_acao
    ))
    conn.commit()
    inserted_id = cursor.lastrowid
    conn.close()
    return inserted_id

def get_all_submissions(
    cidade: Optional[str] = None,
    povoado: Optional[str] = None,
    recebeu_jesus: Optional[str] = None,
    missionario: Optional[str] = None,
    genero: Optional[str] = None,
    search: Optional[str] = None,
    data_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM submissions"
    params = []
    conditions = []
    if cidade and cidade.strip():
        conditions.append("cidade = ?")
        params.append(cidade.strip())
    if povoado and povoado.strip():
        conditions.append("povoado = ?")
        params.append(povoado.strip())
    if recebeu_jesus and recebeu_jesus.strip():
        conditions.append("recebeu_jesus = ?")
        params.append(recebeu_jesus.strip())
    if missionario and missionario.strip():
        conditions.append("missionario = ?")
        params.append(missionario.strip())
    if genero and genero.strip():
        conditions.append("genero = ?")
        params.append(genero.strip())
    if data_date and data_date.strip():
        conditions.append("(data_date = ? OR submission_time LIKE ?)")
        params.append(data_date.strip())
        params.append(f"{data_date.strip()}%")
    if search and search.strip():
        s_term = f"%{search.strip().lower()}%"
        conditions.append("""(
            LOWER(COALESCE(nome, '')) LIKE ? OR
            LOWER(COALESCE(telefone, '')) LIKE ? OR
            LOWER(COALESCE(endereco, '')) LIKE ? OR
            LOWER(COALESCE(observacoes, '')) LIKE ? OR
            LOWER(COALESCE(missionario, '')) LIKE ? OR
            LOWER(COALESCE(cidade, '')) LIKE ? OR
            LOWER(COALESCE(povoado, '')) LIKE ?
        )""")
        params.extend([s_term] * 7)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"
    
    cursor.execute(query, tuple(params))
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

def get_submission_by_id(submission_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_submission(submission_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def update_submission(submission_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        return None

    # Handle geopoint updates
    if "geopoint" in updates and updates["geopoint"]:
        lat, lon, alt, acc = parse_geopoint(updates["geopoint"])
        updates["latitude"] = lat
        updates["longitude"] = lon
        updates["altitude"] = alt
        updates["precision"] = acc

    allowed_fields = [
        "data_date", "nome", "idade", "telefone", "genero", "recebeu_jesus",
        "endereco", "geopoint", "latitude", "longitude", "altitude", "precision",
        "observacoes", "missionario", "cidade", "povoado", "acao"
    ]
    
    set_clauses = []
    params = []
    for field in allowed_fields:
        if field in updates:
            set_clauses.append(f"{field} = ?")
            params.append(updates[field])
            
    if not set_clauses:
        conn.close()
        return dict(existing)
        
    params.append(submission_id)
    query = f"UPDATE submissions SET {', '.join(set_clauses)} WHERE id = ?"
    cursor.execute(query, tuple(params))
    conn.commit()
    
    cursor.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,))
    updated_row = cursor.fetchone()
    conn.close()
    return dict(updated_row) if updated_row else None

