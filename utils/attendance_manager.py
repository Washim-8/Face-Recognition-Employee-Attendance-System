"""
attendance_manager.py — business-logic layer for attendance actions.
All raw DB calls go through db_manager; this file is driver-agnostic.
The only direct DB access here is the CSV export query, which uses
get_db_connection() / _cursor() helpers from db_manager so it works
with both SQLite and PostgreSQL.
"""

import os
import sys
import csv
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.db_manager import (
    get_db_connection, _cursor, _all,
    mark_login, mark_logout, get_today_attendance,
    get_employee_attendance, get_attendance_stats,
    get_monthly_attendance, get_department_attendance,
    get_all_employees,
)


# ─────────────────────────────────────────────────────────────────────────────
# Login / Logout
# ─────────────────────────────────────────────────────────────────────────────

def record_login(employee_id, name):
    """Record employee login with current time. Returns (success, message)."""
    now        = datetime.now()
    login_time = now.strftime('%H:%M:%S')
    today      = now.strftime('%Y-%m-%d')

    late_arrival = 0
    try:
        work_start = datetime.strptime(f"{today} {config.WORK_START_TIME}", '%Y-%m-%d %H:%M')
        threshold  = work_start.replace(
            minute=work_start.minute + config.LATE_THRESHOLD_MINUTES
        )
        if now > threshold:
            late_arrival = 1
    except Exception:
        pass

    status = 'Late' if late_arrival else 'Present'
    return mark_login(employee_id, name, login_time, today, status, late_arrival)


def record_logout(employee_id):
    """Record employee logout with current time. Returns (success, message)."""
    now         = datetime.now()
    logout_time = now.strftime('%H:%M:%S')
    today       = now.strftime('%Y-%m-%d')
    return mark_logout(employee_id, logout_time, today)


# ─────────────────────────────────────────────────────────────────────────────
# Today helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_today_stats():
    return get_attendance_stats(date.today().strftime('%Y-%m-%d'))


def get_today_records():
    return get_today_attendance(date.today().strftime('%Y-%m-%d'))


def get_employee_history(employee_id):
    return get_employee_attendance(employee_id)


# ─────────────────────────────────────────────────────────────────────────────
# Login status check
# ─────────────────────────────────────────────────────────────────────────────

def check_employee_login_status(employee_id):
    """
    Return 'logged_in', 'logged_out', or 'not_recorded' for today.
    Uses db_manager helpers so it works with both SQLite and PostgreSQL.
    """
    today = date.today().strftime('%Y-%m-%d')
    ph    = '%s' if config.USE_POSTGRES else '?'

    conn = get_db_connection()
    cur  = _cursor(conn)
    cur.execute(
        f"SELECT logout_time FROM attendance "
        f"WHERE employee_id={ph} AND date={ph} "
        f"ORDER BY id DESC LIMIT 1",
        (employee_id, today)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        return 'not_recorded'
    row = dict(row)
    return 'logged_in' if row['logout_time'] is None else 'logged_out'


# ─────────────────────────────────────────────────────────────────────────────
# CSV export
# ─────────────────────────────────────────────────────────────────────────────

def export_attendance_to_csv(start_date=None, end_date=None, employee_id=None):
    """
    Export attendance records to a CSV file.
    Returns the local filesystem path of the exported file.
    Works with both SQLite and PostgreSQL.
    """
    os.makedirs(config.REPORTS_DIR, exist_ok=True)

    ph     = '%s' if config.USE_POSTGRES else '?'
    query  = "SELECT * FROM attendance WHERE 1=1"
    params = []

    if start_date:
        query += f" AND date >= {ph}"
        params.append(start_date)
    if end_date:
        query += f" AND date <= {ph}"
        params.append(end_date)
    if employee_id:
        query += f" AND employee_id = {ph}"
        params.append(employee_id)

    query += " ORDER BY date DESC, login_time DESC"

    conn = get_db_connection()
    cur  = _cursor(conn)
    cur.execute(query, params)
    records = _all(cur)
    cur.close()
    conn.close()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath  = os.path.join(config.REPORTS_DIR, f"attendance_report_{timestamp}.csv")

    fieldnames = ['id', 'employee_id', 'name', 'date', 'login_time',
                  'logout_time', 'working_hours', 'status', 'late_arrival']

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(records)

    return filepath


# ─────────────────────────────────────────────────────────────────────────────
# Chart data helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_monthly_chart_data(year=None, month=None):
    """Return (labels, data) lists formatted for Chart.js monthly bar chart."""
    import calendar
    now   = datetime.now()
    year  = year  or now.year
    month = month or now.month

    records    = get_monthly_attendance(year, month)
    record_map = {r['date']: r['present'] for r in records}
    num_days   = calendar.monthrange(year, month)[1]

    labels, data = [], []
    for day in range(1, num_days + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        labels.append(str(day))
        data.append(record_map.get(date_str, 0))

    return labels, data


def get_department_chart_data(date_str=None):
    """Return (departments, present_counts, absent_counts) for Chart.js."""
    if not date_str:
        date_str = date.today().strftime('%Y-%m-%d')

    records        = get_department_attendance(date_str)
    departments    = []
    present_counts = []
    absent_counts  = []

    for r in records:
        departments.append(r['department'])
        present_counts.append(r['present'])
        absent_counts.append(r['total'] - r['present'])

    return departments, present_counts, absent_counts
