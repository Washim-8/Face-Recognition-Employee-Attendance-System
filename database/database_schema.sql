-- Face Recognition Attendance System Database Schema
-- SQLite Database

-- Employees Table
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    position TEXT,
    join_date TEXT,
    face_encoding TEXT,
    profile_image TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    is_active INTEGER DEFAULT 1
);

-- Attendance Table
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    name TEXT NOT NULL,
    login_time TEXT,
    logout_time TEXT,
    date TEXT NOT NULL,
    working_hours REAL DEFAULT 0.0,
    status TEXT DEFAULT 'Present',
    late_arrival INTEGER DEFAULT 0,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);

-- Admin Table
CREATE TABLE IF NOT EXISTS admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    email TEXT,
    last_login TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

-- Insert default admin
INSERT OR IGNORE INTO admin (username, password, email)
VALUES ('admin', 'admin123', 'admin@company.com');
