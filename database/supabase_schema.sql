-- ─────────────────────────────────────────────────────────────────────────────
-- Supabase / PostgreSQL schema
-- Run this once in the Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- before deploying the application.
-- ─────────────────────────────────────────────────────────────────────────────

-- Employees ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS employees (
    id            SERIAL PRIMARY KEY,
    employee_id   TEXT UNIQUE NOT NULL,
    name          TEXT NOT NULL,
    department    TEXT NOT NULL,
    email         TEXT,
    phone         TEXT,
    position      TEXT,
    join_date     TEXT,
    face_encoding TEXT,          -- JSON-serialised 128-d numpy array
    profile_image TEXT,
    created_at    TIMESTAMP DEFAULT NOW(),
    is_active     INTEGER DEFAULT 1
);

-- Attendance ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS attendance (
    id            SERIAL PRIMARY KEY,
    employee_id   TEXT NOT NULL REFERENCES employees(employee_id),
    name          TEXT NOT NULL,
    login_time    TEXT,          -- stored as 'HH:MM:SS' string
    logout_time   TEXT,
    date          TEXT NOT NULL, -- stored as 'YYYY-MM-DD' string
    working_hours REAL DEFAULT 0.0,
    status        TEXT DEFAULT 'Present',
    late_arrival  INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_attendance_date
    ON attendance (date);

CREATE INDEX IF NOT EXISTS idx_attendance_employee_date
    ON attendance (employee_id, date);

-- Admin ───────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin (
    id         SERIAL PRIMARY KEY,
    username   TEXT UNIQUE NOT NULL,
    password   TEXT NOT NULL,   -- store hashed passwords in a future upgrade
    email      TEXT,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Default admin (change the password immediately after first login) ───────────
INSERT INTO admin (username, password, email)
VALUES ('admin', 'admin123', 'admin@company.com')
ON CONFLICT (username) DO NOTHING;
