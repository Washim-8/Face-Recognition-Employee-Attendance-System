"""
sync_to_supabase.py — Direct sync script to push local SQLite database data to Supabase (PostgreSQL).

Usage:
    python sync_to_supabase.py
    python sync_to_supabase.py "postgresql://postgres.xxx:password@aws-0-xxx.pooler.supabase.com:6543/postgres"
"""

import os
import sys
import json
import sqlite3
import psycopg2
import psycopg2.extras

import config

def sync_database(target_url=None):
    db_url = target_url or config.DATABASE_URL or os.environ.get('DATABASE_URL')
    if not db_url:
        print("[ERROR] DATABASE_URL is not set.")
        print("Please provide the connection string: python sync_to_supabase.py <DATABASE_URL>")
        return False

    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    if 'sslmode=' not in db_url and 'localhost' not in db_url and '127.0.0.1' not in db_url:
        separator = '&' if '?' in db_url else '?'
        db_url += f"{separator}sslmode=require"

    print(f"==> Connecting to PostgreSQL...")
    try:
        pg_conn = psycopg2.connect(db_url)
        pg_conn.autocommit = False
        pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        print("[OK] Connected to PostgreSQL successfully!")
    except Exception as e:
        print(f"[ERROR] Failed to connect to PostgreSQL: {e}")
        if 'db.' in db_url and '.supabase.co' in db_url:
            print("[TIP] Supabase direct host (db.*.supabase.co) is IPv6 only.")
            print("[TIP] Use the Supabase Connection Pooler URI (aws-0-*.pooler.supabase.com:6543).")
        return False

    # Read from local seed_data.json or SQLite
    seed_path = os.path.join(config.DATABASE_DIR, 'seed_data.json')
    if os.path.exists(seed_path):
        print(f"==> Loading data from {seed_path}...")
        with open(seed_path, 'r', encoding='utf-8') as f:
            seed = json.load(f)
    else:
        print(f"==> Reading from local SQLite database {config.DATABASE_PATH}...")
        sq_conn = sqlite3.connect(config.DATABASE_PATH)
        sq_conn.row_factory = sqlite3.Row
        sq_cur = sq_conn.cursor()
        sq_cur.execute("SELECT * FROM employees")
        employees = [dict(r) for r in sq_cur.fetchall()]
        sq_cur.execute("SELECT * FROM attendance")
        attendance = [dict(r) for r in sq_cur.fetchall()]
        sq_cur.execute("SELECT * FROM admin")
        admins = [dict(r) for r in sq_cur.fetchall()]
        sq_conn.close()
        seed = {'employees': employees, 'attendance': attendance, 'admins': admins}

    # Ensure PostgreSQL tables exist
    print("==> Creating tables on PostgreSQL if needed...")
    pg_cur.execute("""
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
        );
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
        );
        CREATE TABLE IF NOT EXISTS admin (
            id         SERIAL PRIMARY KEY,
            username   TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            email      TEXT,
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Sync Admin
    for adm in seed.get('admins', []):
        pg_cur.execute("""
            INSERT INTO admin (username, password, email)
            VALUES (%s, %s, %s)
            ON CONFLICT (username) DO UPDATE
            SET password = EXCLUDED.password, email = EXCLUDED.email
        """, (adm.get('username'), adm.get('password'), adm.get('email')))

    # Sync Employees
    emp_synced = 0
    for emp in seed.get('employees', []):
        pg_cur.execute("""
            INSERT INTO employees (employee_id, name, department, email, phone, position, join_date, face_encoding, profile_image, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (employee_id) DO UPDATE
            SET name = EXCLUDED.name,
                department = EXCLUDED.department,
                email = EXCLUDED.email,
                phone = EXCLUDED.phone,
                position = EXCLUDED.position,
                join_date = EXCLUDED.join_date,
                face_encoding = EXCLUDED.face_encoding,
                profile_image = EXCLUDED.profile_image,
                is_active = EXCLUDED.is_active
        """, (
            emp.get('employee_id'), emp.get('name'), emp.get('department'),
            emp.get('email'), emp.get('phone'), emp.get('position'),
            emp.get('join_date'), emp.get('face_encoding'), emp.get('profile_image'),
            emp.get('is_active', 1)
        ))
        emp_synced += 1

    # Sync Attendance (clean and rewrite or append)
    att_synced = 0
    for att in seed.get('attendance', []):
        pg_cur.execute("""
            SELECT id FROM attendance
            WHERE employee_id = %s AND date = %s AND login_time = %s
        """, (att.get('employee_id'), att.get('date'), att.get('login_time')))
        if not pg_cur.fetchone():
            pg_cur.execute("""
                INSERT INTO attendance (employee_id, name, login_time, logout_time, date, working_hours, status, late_arrival)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                att.get('employee_id'), att.get('name'), att.get('login_time'),
                att.get('logout_time'), att.get('date'), att.get('working_hours', 0.0),
                att.get('status', 'Present'), att.get('late_arrival', 0)
            ))
            att_synced += 1

    pg_conn.commit()
    pg_cur.close()
    pg_conn.close()

    print(f"🎉 SUCCESS! Synced {emp_synced} employees and {att_synced} attendance records to Supabase!")
    return True

if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else None
    sync_database(url)
