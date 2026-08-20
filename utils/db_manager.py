"""
db_manager.py — database abstraction layer
Supports PostgreSQL (Supabase) when DATABASE_URL is set, otherwise SQLite.

Key differences handled transparently:
  - Placeholder: SQLite uses ?, PostgreSQL uses %s
  - Auto-increment: SQLite uses INTEGER PRIMARY KEY AUTOINCREMENT,
                    PostgreSQL uses SERIAL PRIMARY KEY
  - datetime default: SQLite uses datetime('now','localtime'),
                      PostgreSQL uses NOW()
  - RETURNING clause used for Postgres INSERT … RETURNING id
  - Connection/cursor lifecycle differs between sqlite3 and psycopg2
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# ── Pick driver ───────────────────────────────────────────────────────────────
if config.USE_POSTGRES:
    import psycopg2
    import psycopg2.extras   # RealDictCursor


# ─────────────────────────────────────────────────────────────────────────────
# Connection helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_db_connection():
    """Return an open DB connection (psycopg2 or sqlite3)."""
    if config.USE_POSTGRES:
        conn = psycopg2.connect(config.DATABASE_URL)
        conn.autocommit = False
        return conn
    else:
        os.makedirs(config.DATABASE_DIR, exist_ok=True)
        conn = sqlite3.connect(config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn


def _cursor(conn):
    """Return a dict-like cursor regardless of driver."""
    if config.USE_POSTGRES:
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return conn.cursor()


def _ph(n=1):
    """Return n comma-separated placeholders (%s or ?)."""
    ph = '%s' if config.USE_POSTGRES else '?'
    return ', '.join([ph] * n)


def _one(cursor):
    """Fetch one row as a plain dict (works for both drivers)."""
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(row)


def _all(cursor):
    """Fetch all rows as a list of plain dicts."""
    return [dict(r) for r in cursor.fetchall()]


# ─────────────────────────────────────────────────────────────────────────────
# Schema initialisation
# ─────────────────────────────────────────────────────────────────────────────

def init_database():
    """Create tables and seed default admin if not present."""
    conn = get_db_connection()
    cur  = _cursor(conn)

    if config.USE_POSTGRES:
        # ── PostgreSQL DDL ─────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id           SERIAL PRIMARY KEY,
                employee_id  TEXT UNIQUE NOT NULL,
                name         TEXT NOT NULL,
                department   TEXT NOT NULL,
                email        TEXT,
                phone        TEXT,
                position     TEXT,
                join_date    TEXT,
                face_encoding TEXT,
                profile_image TEXT,
                created_at   TIMESTAMP DEFAULT NOW(),
                is_active    INTEGER DEFAULT 1
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id            SERIAL PRIMARY KEY,
                employee_id   TEXT NOT NULL,
                name          TEXT NOT NULL,
                login_time    TEXT,
                logout_time   TEXT,
                date          TEXT NOT NULL,
                working_hours REAL DEFAULT 0.0,
                status        TEXT DEFAULT 'Present',
                late_arrival  INTEGER DEFAULT 0,
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                id         SERIAL PRIMARY KEY,
                username   TEXT UNIQUE NOT NULL,
                password   TEXT NOT NULL,
                email      TEXT,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute(
            "INSERT INTO admin (username, password, email) "
            "VALUES (%s, %s, %s) ON CONFLICT (username) DO NOTHING",
            (config.ADMIN_USERNAME, config.ADMIN_PASSWORD, 'admin@company.com')
        )
    else:
        # ── SQLite DDL ─────────────────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id   TEXT UNIQUE NOT NULL,
                name          TEXT NOT NULL,
                department    TEXT NOT NULL,
                email         TEXT,
                phone         TEXT,
                position      TEXT,
                join_date     TEXT,
                face_encoding TEXT,
                profile_image TEXT,
                created_at    TEXT DEFAULT (datetime('now', 'localtime')),
                is_active     INTEGER DEFAULT 1
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id   TEXT NOT NULL,
                name          TEXT NOT NULL,
                login_time    TEXT,
                logout_time   TEXT,
                date          TEXT NOT NULL,
                working_hours REAL DEFAULT 0.0,
                status        TEXT DEFAULT 'Present',
                late_arrival  INTEGER DEFAULT 0,
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT UNIQUE NOT NULL,
                password   TEXT NOT NULL,
                email      TEXT,
                last_login TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        cur.execute(
            "INSERT OR IGNORE INTO admin (username, password, email) VALUES (?, ?, ?)",
            (config.ADMIN_USERNAME, config.ADMIN_PASSWORD, 'admin@company.com')
        )

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database initialised successfully!")


# ─────────────────────────────────────────────────────────────────────────────
# Employee CRUD
# ─────────────────────────────────────────────────────────────────────────────

def get_all_employees():
    conn = get_db_connection()
    cur  = _cursor(conn)
    cur.execute("SELECT * FROM employees WHERE is_active=1 ORDER BY name")
    rows = _all(cur)
    cur.close(); conn.close()
    return rows


def get_employee_by_id(employee_id):
    ph   = '%s' if config.USE_POSTGRES else '?'
    conn = get_db_connection()
    cur  = _cursor(conn)
    cur.execute(f"SELECT * FROM employees WHERE employee_id={ph}", (employee_id,))
    row  = _one(cur)
    cur.close(); conn.close()
    return row


def add_employee(employee_id, name, department, email, phone, position, join_date):
    ph   = '%s' if config.USE_POSTGRES else '?'
    conn = get_db_connection()
    cur  = _cursor(conn)
    try:
        cur.execute(
            f"INSERT INTO employees "
            f"(employee_id, name, department, email, phone, position, join_date) "
            f"VALUES ({_ph(7)})",
            (employee_id, name, department, email, phone, position, join_date)
        )
        conn.commit()
        return True, "Employee added successfully!"
    except (psycopg2.errors.UniqueViolation if config.USE_POSTGRES else sqlite3.IntegrityError):
        conn.rollback()
        return False, "Employee ID already exists!"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cur.close(); conn.close()


def update_employee(employee_id, name, department, email, phone, position):
    ph   = '%s' if config.USE_POSTGRES else '?'
    conn = get_db_connection()
    cur  = _cursor(conn)
    try:
        cur.execute(
            f"UPDATE employees "
            f"SET name={ph}, department={ph}, email={ph}, phone={ph}, position={ph} "
            f"WHERE employee_id={ph}",
            (name, department, email, phone, position, employee_id)
        )
        conn.commit()
        return True, "Employee updated successfully!"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cur.close(); conn.close()


def delete_employee(employee_id):
    ph   = '%s' if config.USE_POSTGRES else '?'
    conn = get_db_connection()
    cur  = _cursor(conn)
    try:
        cur.execute(
            f"UPDATE employees SET is_active=0 WHERE employee_id={ph}",
            (employee_id,)
        )
        conn.commit()
        return True, "Employee deleted successfully!"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cur.close(); conn.close()


def update_face_encoding(employee_id, encoding_str):
    ph   = '%s' if config.USE_POSTGRES else '?'
    conn = get_db_connection()
    cur  = _cursor(conn)
    try:
        cur.execute(
            f"UPDATE employees SET face_encoding={ph} WHERE employee_id={ph}",
            (encoding_str, employee_id)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error updating face encoding: {e}")
        return False
    finally:
        cur.close(); conn.close()


def get_all_face_encodings():
    conn = get_db_connection()
    cur  = _cursor(conn)
    cur.execute(
        "SELECT employee_id, name, face_encoding "
        "FROM employees "
        "WHERE face_encoding IS NOT NULL AND is_active=1"
    )
    rows = _all(cur)
    cur.close(); conn.close()
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Attendance
# ─────────────────────────────────────────────────────────────────────────────

def mark_login(employee_id, name, login_time, date, status='Present', late_arrival=0):
    ph   = '%s' if config.USE_POSTGRES else '?'
    conn = get_db_connection()
    cur  = _cursor(conn)
    try:
        cur.execute(
            f"SELECT id, logout_time FROM attendance "
            f"WHERE employee_id={ph} AND date={ph}",
            (employee_id, date)
        )
        existing = _one(cur)

        if existing:
            if existing['logout_time'] is None:
                return False, "Already logged in for today."
            # Allow re-login after logout (second shift)
            cur.execute(
                f"INSERT INTO attendance "
                f"(employee_id, name, login_time, date, status, late_arrival) "
                f"VALUES ({_ph(6)})",
                (employee_id, name, login_time, date, status, late_arrival)
            )
        else:
            cur.execute(
                f"INSERT INTO attendance "
                f"(employee_id, name, login_time, date, status, late_arrival) "
                f"VALUES ({_ph(6)})",
                (employee_id, name, login_time, date, status, late_arrival)
            )

        conn.commit()
        return True, "Login recorded successfully!"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cur.close(); conn.close()


def mark_logout(employee_id, logout_time, date):
    ph   = '%s' if config.USE_POSTGRES else '?'
    conn = get_db_connection()
    cur  = _cursor(conn)
    try:
        cur.execute(
            f"SELECT id, login_time FROM attendance "
            f"WHERE employee_id={ph} AND date={ph} AND logout_time IS NULL "
            f"ORDER BY id DESC LIMIT 1",
            (employee_id, date)
        )
        record = _one(cur)

        if not record:
            return False, "No active login session found."

        from datetime import datetime as dt
        login_dt   = dt.strptime(record['login_time'], '%H:%M:%S')
        logout_dt  = dt.strptime(logout_time, '%H:%M:%S')
        working_h  = max(0, (logout_dt - login_dt).total_seconds() / 3600)

        cur.execute(
            f"UPDATE attendance SET logout_time={ph}, working_hours={ph} WHERE id={ph}",
            (logout_time, round(working_h, 2), record['id'])
        )
        conn.commit()
        return True, f"Logout recorded. Working hours: {round(working_h, 2)}h"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cur.close(); conn.close()


def get_today_attendance(date):
    ph   = '%s' if config.USE_POSTGRES else '?'
    conn = get_db_connection()
    cur  = _cursor(conn)
    cur.execute(
        f"SELECT * FROM attendance WHERE date={ph} ORDER BY login_time",
        (date,)
    )
    rows = _all(cur)
    cur.close(); conn.close()
    return rows


def get_employee_attendance(employee_id):
    ph   = '%s' if config.USE_POSTGRES else '?'
    conn = get_db_connection()
    cur  = _cursor(conn)
    cur.execute(
        f"SELECT * FROM attendance "
        f"WHERE employee_id={ph} ORDER BY date DESC, login_time DESC",
        (employee_id,)
    )
    rows = _all(cur)
    cur.close(); conn.close()
    return rows


def get_attendance_stats(date):
    ph   = '%s' if config.USE_POSTGRES else '?'
    conn = get_db_connection()
    cur  = _cursor(conn)

    cur.execute("SELECT COUNT(*) AS count FROM employees WHERE is_active=1")
    total_employees = _one(cur)['count']

    cur.execute(
        f"SELECT COUNT(DISTINCT employee_id) AS count FROM attendance WHERE date={ph}",
        (date,)
    )
    present_today = _one(cur)['count']

    cur.execute(
        f"SELECT COUNT(*) AS count FROM attendance WHERE date={ph} AND late_arrival=1",
        (date,)
    )
    late_today = _one(cur)['count']

    cur.execute(
        f"SELECT AVG(working_hours) AS avg FROM attendance "
        f"WHERE date={ph} AND working_hours > 0",
        (date,)
    )
    avg_hours = _one(cur)['avg'] or 0

    cur.close(); conn.close()
    return {
        'total_employees':  total_employees,
        'present_today':    present_today,
        'absent_today':     total_employees - present_today,
        'late_today':       late_today,
        'avg_working_hours': round(avg_hours, 2),
        'attendance_rate':  round(
            (present_today / total_employees * 100) if total_employees > 0 else 0, 1
        ),
    }


def get_monthly_attendance(year, month):
    conn = get_db_connection()
    cur  = _cursor(conn)

    if config.USE_POSTGRES:
        cur.execute(
            "SELECT date, COUNT(DISTINCT employee_id) AS present "
            "FROM attendance "
            "WHERE EXTRACT(YEAR FROM date::date)=%s "
            "  AND EXTRACT(MONTH FROM date::date)=%s "
            "GROUP BY date ORDER BY date",
            (year, month)
        )
    else:
        cur.execute(
            "SELECT date, COUNT(DISTINCT employee_id) AS present "
            "FROM attendance "
            "WHERE strftime('%Y', date)=? AND strftime('%m', date)=? "
            "GROUP BY date ORDER BY date",
            (str(year), str(month).zfill(2))
        )

    rows = _all(cur)
    cur.close(); conn.close()
    return rows


def get_department_attendance(date):
    ph   = '%s' if config.USE_POSTGRES else '?'
    conn = get_db_connection()
    cur  = _cursor(conn)
    cur.execute(
        f"SELECT e.department, "
        f"       COUNT(DISTINCT e.employee_id) AS total, "
        f"       COUNT(DISTINCT a.employee_id) AS present "
        f"FROM employees e "
        f"LEFT JOIN attendance a "
        f"       ON e.employee_id = a.employee_id AND a.date = {ph} "
        f"WHERE e.is_active = 1 "
        f"GROUP BY e.department",
        (date,)
    )
    rows = _all(cur)
    cur.close(); conn.close()
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Admin
# ─────────────────────────────────────────────────────────────────────────────

def verify_admin(username, password):
    ph   = '%s' if config.USE_POSTGRES else '?'
    conn = get_db_connection()
    cur  = _cursor(conn)
    cur.execute(
        f"SELECT * FROM admin WHERE username={ph} AND password={ph}",
        (username, password)
    )
    row = _one(cur)
    cur.close(); conn.close()
    return row is not None
