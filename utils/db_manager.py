import sqlite3
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    """Initialize the database with required tables."""
    os.makedirs(config.DATABASE_DIR, exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Employees Table
    cursor.execute('''
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
        )
    ''')
    
    # Attendance Table
    cursor.execute('''
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
        )
    ''')
    
    # Admin Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            last_login TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    
    # Insert default admin if not exists
    cursor.execute('''
        INSERT OR IGNORE INTO admin (username, password, email)
        VALUES (?, ?, ?)
    ''', (config.ADMIN_USERNAME, config.ADMIN_PASSWORD, 'admin@company.com'))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")


def get_all_employees():
    """Fetch all active employees."""
    conn = get_db_connection()
    employees = conn.execute(
        "SELECT * FROM employees WHERE is_active=1 ORDER BY name"
    ).fetchall()
    conn.close()
    return [dict(e) for e in employees]


def get_employee_by_id(employee_id):
    """Fetch employee by employee_id."""
    conn = get_db_connection()
    emp = conn.execute(
        "SELECT * FROM employees WHERE employee_id=?", (employee_id,)
    ).fetchone()
    conn.close()
    return dict(emp) if emp else None


def add_employee(employee_id, name, department, email, phone, position, join_date):
    """Add a new employee to the database."""
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO employees (employee_id, name, department, email, phone, position, join_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (employee_id, name, department, email, phone, position, join_date))
        conn.commit()
        return True, "Employee added successfully!"
    except sqlite3.IntegrityError:
        return False, "Employee ID already exists!"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def update_employee(employee_id, name, department, email, phone, position):
    """Update employee details."""
    conn = get_db_connection()
    try:
        conn.execute('''
            UPDATE employees
            SET name=?, department=?, email=?, phone=?, position=?
            WHERE employee_id=?
        ''', (name, department, email, phone, position, employee_id))
        conn.commit()
        return True, "Employee updated successfully!"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def delete_employee(employee_id):
    """Soft-delete an employee."""
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE employees SET is_active=0 WHERE employee_id=?",
            (employee_id,)
        )
        conn.commit()
        return True, "Employee deleted successfully!"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def update_face_encoding(employee_id, encoding_str):
    """Update the face encoding for an employee."""
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE employees SET face_encoding=? WHERE employee_id=?",
            (encoding_str, employee_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating face encoding: {e}")
        return False
    finally:
        conn.close()


def get_all_face_encodings():
    """Fetch all employees with face encodings."""
    conn = get_db_connection()
    employees = conn.execute(
        "SELECT employee_id, name, face_encoding FROM employees WHERE face_encoding IS NOT NULL AND is_active=1"
    ).fetchall()
    conn.close()
    return [dict(e) for e in employees]


def mark_login(employee_id, name, login_time, date, status='Present', late_arrival=0):
    """Mark employee login attendance."""
    conn = get_db_connection()
    try:
        # Check if already logged in today
        existing = conn.execute(
            "SELECT id, logout_time FROM attendance WHERE employee_id=? AND date=?",
            (employee_id, date)
        ).fetchone()
        
        if existing:
            if existing['logout_time'] is None:
                conn.close()
                return False, "Already logged in for today."
            else:
                # Allow re-login after logout (second shift, etc.)
                conn.execute('''
                    INSERT INTO attendance (employee_id, name, login_time, date, status, late_arrival)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (employee_id, name, login_time, date, status, late_arrival))
        else:
            conn.execute('''
                INSERT INTO attendance (employee_id, name, login_time, date, status, late_arrival)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (employee_id, name, login_time, date, status, late_arrival))
        
        conn.commit()
        return True, "Login recorded successfully!"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def mark_logout(employee_id, logout_time, date):
    """Mark employee logout and calculate working hours."""
    conn = get_db_connection()
    try:
        record = conn.execute(
            "SELECT id, login_time FROM attendance WHERE employee_id=? AND date=? AND logout_time IS NULL ORDER BY id DESC LIMIT 1",
            (employee_id, date)
        ).fetchone()
        
        if not record:
            conn.close()
            return False, "No active login session found."
        
        # Calculate working hours
        from datetime import datetime
        login_dt = datetime.strptime(record['login_time'], '%H:%M:%S')
        logout_dt = datetime.strptime(logout_time, '%H:%M:%S')
        working_seconds = (logout_dt - login_dt).total_seconds()
        working_hours = max(0, working_seconds / 3600)
        
        conn.execute('''
            UPDATE attendance
            SET logout_time=?, working_hours=?
            WHERE id=?
        ''', (logout_time, round(working_hours, 2), record['id']))
        
        conn.commit()
        return True, f"Logout recorded. Working hours: {round(working_hours, 2)}h"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def get_today_attendance(date):
    """Get all attendance records for a specific date."""
    conn = get_db_connection()
    records = conn.execute(
        "SELECT * FROM attendance WHERE date=? ORDER BY login_time",
        (date,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in records]


def get_employee_attendance(employee_id):
    """Get all attendance records for a specific employee."""
    conn = get_db_connection()
    records = conn.execute(
        "SELECT * FROM attendance WHERE employee_id=? ORDER BY date DESC, login_time DESC",
        (employee_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in records]


def get_attendance_stats(date):
    """Get attendance statistics for a specific date."""
    conn = get_db_connection()
    total_employees = conn.execute(
        "SELECT COUNT(*) as count FROM employees WHERE is_active=1"
    ).fetchone()['count']
    
    present_today = conn.execute(
        "SELECT COUNT(DISTINCT employee_id) as count FROM attendance WHERE date=?",
        (date,)
    ).fetchone()['count']
    
    late_today = conn.execute(
        "SELECT COUNT(*) as count FROM attendance WHERE date=? AND late_arrival=1",
        (date,)
    ).fetchone()['count']
    
    avg_hours = conn.execute(
        "SELECT AVG(working_hours) as avg FROM attendance WHERE date=? AND working_hours > 0",
        (date,)
    ).fetchone()['avg']
    
    conn.close()
    return {
        'total_employees': total_employees,
        'present_today': present_today,
        'absent_today': total_employees - present_today,
        'late_today': late_today,
        'avg_working_hours': round(avg_hours or 0, 2),
        'attendance_rate': round((present_today / total_employees * 100) if total_employees > 0 else 0, 1)
    }


def get_monthly_attendance(year, month):
    """Get daily attendance count for a specific month."""
    conn = get_db_connection()
    records = conn.execute('''
        SELECT date, COUNT(DISTINCT employee_id) as present
        FROM attendance
        WHERE strftime('%Y', date)=? AND strftime('%m', date)=?
        GROUP BY date
        ORDER BY date
    ''', (str(year), str(month).zfill(2))).fetchall()
    conn.close()
    return [dict(r) for r in records]


def get_department_attendance(date):
    """Get attendance grouped by department for a specific date."""
    conn = get_db_connection()
    records = conn.execute('''
        SELECT e.department,
               COUNT(DISTINCT e.employee_id) as total,
               COUNT(DISTINCT a.employee_id) as present
        FROM employees e
        LEFT JOIN attendance a ON e.employee_id = a.employee_id AND a.date = ?
        WHERE e.is_active = 1
        GROUP BY e.department
    ''', (date,)).fetchall()
    conn.close()
    return [dict(r) for r in records]


def verify_admin(username, password):
    """Verify admin credentials."""
    conn = get_db_connection()
    admin = conn.execute(
        "SELECT * FROM admin WHERE username=? AND password=?",
        (username, password)
    ).fetchone()
    
    if admin:
        conn.execute(
            "UPDATE admin SET last_login=datetime('now','localtime') WHERE username=?",
            (username,)
        )
        conn.commit()
    
    conn.close()
    return admin is not None


if __name__ == '__main__':
    init_database()
