import os
import sys
import json
import base64
import numpy as np
import cv2
from datetime import datetime, date
from functools import wraps

from flask import (Flask, render_template, request, jsonify,
                   session, redirect, url_for, flash, Response, send_file)

# Configuration
import config
from utils.db_manager import (
    init_database, get_all_employees, get_employee_by_id,
    add_employee, update_employee, delete_employee,
    get_today_attendance, get_employee_attendance,
    get_attendance_stats, get_monthly_attendance,
    get_department_attendance, verify_admin
)
from utils.face_recognition_utils import (
    load_known_encodings, recognize_face_from_frame,
    encode_employee_from_dataset, encode_face_from_image_bytes,
    match_face_from_encoding, save_face_model
)
from utils.dataset_capture import (
    save_captured_frame, get_captured_count, clear_dataset
)
from utils.attendance_manager import (
    record_login, record_logout, get_today_stats,
    get_today_records, export_attendance_to_csv,
    get_monthly_chart_data, get_department_chart_data,
    check_employee_login_status
)

# ============================================================
# App Initialization
# ============================================================
app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Initialize DB on startup
init_database()

# Global face recognition cache
face_cache = {
    'encodings': [],
    'ids': [],
    'names': [],
    'last_loaded': None
}


def reload_face_encodings():
    """Reload face encodings from database into memory cache."""
    encodings, ids, names = load_known_encodings()
    face_cache['encodings'] = encodings
    face_cache['ids'] = ids
    face_cache['names'] = names
    face_cache['last_loaded'] = datetime.now()
    print(f"✅ Loaded {len(ids)} face encodings into memory.")


# Load on startup
reload_face_encodings()


# ============================================================
# Auth Decorators
# ============================================================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Please login first.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# ============================================================
# Main Routes
# ============================================================
@app.route('/')
def index():
    """Landing page — face recognition attendance terminal."""
    return render_template('index.html')


@app.route('/about-contact')
def about_contact():
    """About & Contact portfolio page."""
    return render_template('about_contact.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_logged_in' in session:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if verify_admin(username, password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
    
    return render_template('login.html')


@app.route('/admin/logout_session')
def admin_logout_session():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin_login'))


# ============================================================
# Admin Dashboard
# ============================================================
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    today = date.today().strftime('%Y-%m-%d')
    stats = get_attendance_stats(today)
    employees = get_all_employees()
    today_records = get_today_attendance(today)
    
    # Chart data
    now = datetime.now()
    chart_labels, chart_data = get_monthly_chart_data(now.year, now.month)
    dept_labels, dept_present, dept_absent = get_department_chart_data(today)
    
    return render_template('admin_dashboard.html',
                           stats=stats,
                           employees=employees,
                           today_records=today_records,
                           today=today,
                           chart_labels=json.dumps(chart_labels),
                           chart_data=json.dumps(chart_data),
                           dept_labels=json.dumps(dept_labels),
                           dept_present=json.dumps(dept_present),
                           dept_absent=json.dumps(dept_absent),
                           admin_username=session.get('admin_username', 'Admin'))


# ============================================================
# Employee Management
# ============================================================
@app.route('/admin/employees')
@login_required
def manage_employees():
    employees = get_all_employees()
    return render_template('employees.html', employees=employees)


@app.route('/admin/employees/add', methods=['GET', 'POST'])
@login_required
def add_employee_route():
    if request.method == 'POST':
        data = request.form
        success, message = add_employee(
            employee_id=data.get('employee_id', '').strip(),
            name=data.get('name', '').strip(),
            department=data.get('department', '').strip(),
            email=data.get('email', '').strip(),
            phone=data.get('phone', '').strip(),
            position=data.get('position', '').strip(),
            join_date=data.get('join_date', date.today().strftime('%Y-%m-%d'))
        )
        if success:
            flash(message, 'success')
            emp_id = data.get('employee_id', '').strip()
            return redirect(url_for('capture_face_route', employee_id=emp_id))
        else:
            flash(message, 'danger')
    
    return render_template('register_employee.html')


@app.route('/admin/employees/edit/<employee_id>', methods=['GET', 'POST'])
@login_required
def edit_employee_route(employee_id):
    employee = get_employee_by_id(employee_id)
    if not employee:
        flash('Employee not found.', 'danger')
        return redirect(url_for('manage_employees'))
    
    if request.method == 'POST':
        data = request.form
        success, message = update_employee(
            employee_id=employee_id,
            name=data.get('name', '').strip(),
            department=data.get('department', '').strip(),
            email=data.get('email', '').strip(),
            phone=data.get('phone', '').strip(),
            position=data.get('position', '').strip()
        )
        if success:
            flash(message, 'success')
            return redirect(url_for('manage_employees'))
        else:
            flash(message, 'danger')
    
    return render_template('edit_employee.html', employee=employee)


@app.route('/admin/employees/delete/<employee_id>', methods=['POST'])
@login_required
def delete_employee_route(employee_id):
    success, message = delete_employee(employee_id)
    if success:
        reload_face_encodings()
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('manage_employees'))


# ============================================================
# Face Dataset Capture (Web Camera)
# ============================================================
@app.route('/admin/capture-face/<employee_id>')
@login_required
def capture_face_route(employee_id):
    employee = get_employee_by_id(employee_id)
    if not employee:
        flash('Employee not found.', 'danger')
        return redirect(url_for('manage_employees'))
    
    captured_count = get_captured_count(employee_id)
    return render_template('capture_face.html',
                           employee=employee,
                           captured_count=captured_count,
                           required_images=config.IMAGES_PER_EMPLOYEE)


@app.route('/api/capture-frame', methods=['POST'])
@login_required
def api_capture_frame():
    """API endpoint to receive and save a single webcam frame."""
    data = request.get_json()
    employee_id = data.get('employee_id')
    frame_data = data.get('frame')  # base64 encoded
    frame_index = data.get('frame_index', 1)
    
    if not employee_id or not frame_data:
        return jsonify({'success': False, 'message': 'Missing data'})
    
    try:
        # Decode base64 image
        img_data = base64.b64decode(frame_data.split(',')[1])
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'success': False, 'message': 'Invalid image'})
        
        success = save_captured_frame(employee_id, frame, frame_index)
        captured_count = get_captured_count(employee_id)
        
        return jsonify({
            'success': success,
            'captured_count': captured_count,
            'required': config.IMAGES_PER_EMPLOYEE
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/clear-dataset', methods=['POST'])
@login_required
def api_clear_dataset():
    data = request.get_json()
    employee_id = data.get('employee_id')
    if employee_id:
        clear_dataset(employee_id)
        return jsonify({'success': True})
    return jsonify({'success': False})


@app.route('/api/train-model', methods=['POST'])
@login_required
def api_train_model():
    """Train face model for an employee from captured dataset."""
    data = request.get_json()
    employee_id = data.get('employee_id')
    
    if not employee_id:
        return jsonify({'success': False, 'message': 'Missing employee ID'})
    
    success, message = encode_employee_from_dataset(employee_id)
    
    if success:
        reload_face_encodings()  # Reload cache
        save_face_model()
    
    return jsonify({'success': success, 'message': message})


# ============================================================
# Face Recognition API (for attendance terminal)
# ============================================================
@app.route('/api/recognize-face', methods=['POST'])
def api_recognize_face():
    """
    Recognize a face from a webcam frame.
    Used by the main attendance terminal.
    """
    data = request.get_json()
    frame_data = data.get('frame')
    action = data.get('action', 'login')  # 'login' or 'logout'
    
    if not frame_data:
        return jsonify({'success': False, 'message': 'No frame data'})
    
    if not face_cache['encodings']:
        return jsonify({'success': False, 'message': 'No face models trained yet. Please add employees first.'})
    
    try:
        # Decode base64 image
        img_data = base64.b64decode(frame_data.split(',')[1])
        nparr = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'success': False, 'message': 'Invalid image'})
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        results = recognize_face_from_frame(
            rgb_frame,
            face_cache['encodings'],
            face_cache['ids'],
            face_cache['names']
        )
        
        if not results:
            return jsonify({'success': False, 'message': 'No face detected in frame'})
        
        # Process first recognized face
        recognized = [r for r in results if r['recognized']]
        
        if not recognized:
            return jsonify({'success': False, 'message': 'Face not recognized. Please try again.'})
        
        person = recognized[0]
        employee_id = person['employee_id']
        name = person['name']
        confidence = person['confidence']
        
        # Check current status
        status = check_employee_login_status(employee_id)
        
        if action == 'login':
            if status == 'logged_in':
                return jsonify({
                    'success': False,
                    'message': f'{name} is already logged in today.',
                    'employee_id': employee_id,
                    'name': name,
                    'confidence': confidence,
                    'status': status
                })
            
            success, message = record_login(employee_id, name)
            return jsonify({
                'success': success,
                'message': message,
                'employee_id': employee_id,
                'name': name,
                'confidence': confidence,
                'action': 'login',
                'time': datetime.now().strftime('%I:%M:%S %p')
            })
        
        elif action == 'logout':
            if status == 'not_recorded':
                return jsonify({
                    'success': False,
                    'message': f'{name} has not logged in today.',
                    'employee_id': employee_id,
                    'name': name
                })
            elif status == 'logged_out':
                return jsonify({
                    'success': False,
                    'message': f'{name} has already logged out today.',
                    'employee_id': employee_id,
                    'name': name
                })
            
            success, message = record_logout(employee_id)
            return jsonify({
                'success': success,
                'message': message,
                'employee_id': employee_id,
                'name': name,
                'confidence': confidence,
                'action': 'logout',
                'time': datetime.now().strftime('%I:%M:%S %p')
            })
        
        return jsonify({'success': False, 'message': 'Invalid action'})
    
    except Exception as e:
        print(f"Recognition error: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})


# ============================================================
# Attendance Management
# ============================================================
@app.route('/admin/attendance')
@login_required
def attendance_page():
    today = date.today().strftime('%Y-%m-%d')
    selected_date = request.args.get('date', today)
    selected_employee = request.args.get('employee_id', '')
    
    if selected_employee:
        records = get_employee_attendance(selected_employee)
    else:
        records = get_today_attendance(selected_date)
    
    stats = get_attendance_stats(selected_date)
    employees = get_all_employees()
    
    return render_template('attendance.html',
                           records=records,
                           stats=stats,
                           employees=employees,
                           selected_date=selected_date,
                           selected_employee=selected_employee,
                           today=today)


@app.route('/admin/attendance/export')
@login_required
def export_attendance():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    employee_id = request.args.get('employee_id')
    
    filepath = export_attendance_to_csv(start_date, end_date, employee_id)
    return send_file(filepath, as_attachment=True,
                     download_name=os.path.basename(filepath))


# ============================================================
# Analytics
# ============================================================
@app.route('/admin/analytics')
@login_required
def analytics_page():
    today = date.today().strftime('%Y-%m-%d')
    now = datetime.now()
    
    # Monthly data
    chart_labels, chart_data = get_monthly_chart_data(now.year, now.month)
    dept_labels, dept_present, dept_absent = get_department_chart_data(today)
    stats = get_attendance_stats(today)
    
    # Last 7 days trend
    from datetime import timedelta
    week_labels = []
    week_data = []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        day_stats = get_attendance_stats(d)
        week_labels.append((datetime.now() - timedelta(days=i)).strftime('%a'))
        week_data.append(day_stats['present_today'])
    
    return render_template('analytics.html',
                           stats=stats,
                           chart_labels=json.dumps(chart_labels),
                           chart_data=json.dumps(chart_data),
                           dept_labels=json.dumps(dept_labels),
                           dept_present=json.dumps(dept_present),
                           dept_absent=json.dumps(dept_absent),
                           week_labels=json.dumps(week_labels),
                           week_data=json.dumps(week_data),
                           today=today)


# ============================================================
# Employee Profile
# ============================================================
@app.route('/admin/employee/<employee_id>')
@login_required
def employee_profile(employee_id):
    employee = get_employee_by_id(employee_id)
    if not employee:
        flash('Employee not found.', 'danger')
        return redirect(url_for('manage_employees'))
    
    records = get_employee_attendance(employee_id)
    
    # Calculate summary stats
    total_days = len(records)
    total_hours = sum(r.get('working_hours', 0) or 0 for r in records)
    avg_hours = round(total_hours / total_days, 2) if total_days > 0 else 0
    late_days = sum(1 for r in records if r.get('late_arrival', 0))
    
    return render_template('employee_profile.html',
                           employee=employee,
                           records=records,
                           total_days=total_days,
                           total_hours=round(total_hours, 2),
                           avg_hours=avg_hours,
                           late_days=late_days)


# ============================================================
# API: Dashboard stats (for AJAX refresh)
# ============================================================
@app.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats():
    today = date.today().strftime('%Y-%m-%d')
    stats = get_attendance_stats(today)
    return jsonify(stats)


@app.route('/api/today-attendance')
@login_required
def api_today_attendance():
    today = date.today().strftime('%Y-%m-%d')
    records = get_today_attendance(today)
    return jsonify(records)


# ============================================================
# Run
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("  Face Recognition Attendance System")
    print("  Starting Flask Server...")
    print("  URL: http://127.0.0.1:5000")
    print("  Admin: http://127.0.0.1:5000/admin/login")
    print("  Admin Login: admin / admin123")
    print("=" * 60)
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5000)
