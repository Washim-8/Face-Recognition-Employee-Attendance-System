import os
import sys
import csv
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.db_manager import (
    mark_login, mark_logout, get_today_attendance,
    get_employee_attendance, get_attendance_stats,
    get_monthly_attendance, get_department_attendance,
    get_all_employees
)


def record_login(employee_id, name):
    """
    Record employee login with current time.
    Returns (success, message).
    """
    now = datetime.now()
    login_time = now.strftime('%H:%M:%S')
    today = now.strftime('%Y-%m-%d')
    
    # Check if late
    late_arrival = 0
    try:
        work_start = datetime.strptime(f"{today} {config.WORK_START_TIME}", '%Y-%m-%d %H:%M')
        threshold = work_start.replace(
            minute=work_start.minute + config.LATE_THRESHOLD_MINUTES
        )
        if now > threshold:
            late_arrival = 1
    except Exception:
        pass
    
    status = 'Late' if late_arrival else 'Present'
    return mark_login(employee_id, name, login_time, today, status, late_arrival)


def record_logout(employee_id):
    """
    Record employee logout with current time.
    Returns (success, message).
    """
    now = datetime.now()
    logout_time = now.strftime('%H:%M:%S')
    today = now.strftime('%Y-%m-%d')
    return mark_logout(employee_id, logout_time, today)


def get_today_stats():
    """Get attendance statistics for today."""
    today = date.today().strftime('%Y-%m-%d')
    return get_attendance_stats(today)


def get_today_records():
    """Get all attendance records for today."""
    today = date.today().strftime('%Y-%m-%d')
    return get_today_attendance(today)


def get_employee_history(employee_id):
    """Get complete attendance history for an employee."""
    return get_employee_attendance(employee_id)


def export_attendance_to_csv(start_date=None, end_date=None, employee_id=None):
    """
    Export attendance records to CSV file.
    Returns the path of the exported file.
    """
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    
    import sqlite3
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    
    query = "SELECT * FROM attendance WHERE 1=1"
    params = []
    
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    if employee_id:
        query += " AND employee_id = ?"
        params.append(employee_id)
    
    query += " ORDER BY date DESC, login_time DESC"
    
    records = conn.execute(query, params).fetchall()
    conn.close()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"attendance_report_{timestamp}.csv"
    filepath = os.path.join(config.REPORTS_DIR, filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['id', 'employee_id', 'name', 'date', 'login_time',
                      'logout_time', 'working_hours', 'status', 'late_arrival']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(dict(record))
    
    return filepath


def get_monthly_chart_data(year=None, month=None):
    """Get monthly attendance data formatted for Chart.js."""
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    
    records = get_monthly_attendance(year, month)
    
    # Fill in all days of the month
    import calendar
    num_days = calendar.monthrange(year, month)[1]
    
    chart_labels = []
    chart_data = []
    
    record_dict = {r['date']: r['present'] for r in records}
    
    for day in range(1, num_days + 1):
        date_str = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
        chart_labels.append(f"{day}")
        chart_data.append(record_dict.get(date_str, 0))
    
    return chart_labels, chart_data


def get_department_chart_data(date_str=None):
    """Get department-wise attendance for Chart.js."""
    if not date_str:
        date_str = date.today().strftime('%Y-%m-%d')
    
    records = get_department_attendance(date_str)
    
    departments = []
    present_counts = []
    absent_counts = []
    
    for r in records:
        departments.append(r['department'])
        present_counts.append(r['present'])
        absent_counts.append(r['total'] - r['present'])
    
    return departments, present_counts, absent_counts


def check_employee_login_status(employee_id):
    """
    Check if an employee is currently logged in today.
    Returns 'logged_in', 'logged_out', or 'not_recorded'.
    """
    today = date.today().strftime('%Y-%m-%d')
    
    import sqlite3
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    
    record = conn.execute(
        "SELECT logout_time FROM attendance WHERE employee_id=? AND date=? ORDER BY id DESC LIMIT 1",
        (employee_id, today)
    ).fetchone()
    
    conn.close()
    
    if record is None:
        return 'not_recorded'
    elif record['logout_time'] is None:
        return 'logged_in'
    else:
        return 'logged_out'
