import os

# Base directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Database configuration
DATABASE_DIR = os.path.join(BASE_DIR, 'database')
DATABASE_PATH = os.path.join(DATABASE_DIR, 'attendance.db')

# Dataset configuration
DATASET_DIR = os.path.join(BASE_DIR, 'dataset')

# Models configuration
MODELS_DIR = os.path.join(BASE_DIR, 'models')
FACE_MODEL_PATH = os.path.join(MODELS_DIR, 'face_model.pkl')

# Reports configuration
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')

# Flask configuration
SECRET_KEY = 'face_recognition_attendance_secret_key_2024'
DEBUG = True

# Face recognition configuration
FACE_RECOGNITION_TOLERANCE = 0.5   # Lower = more strict (0.4-0.6 recommended)
IMAGES_PER_EMPLOYEE = 30            # Number of face images to capture per employee

# Admin credentials (initial)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

# Working hours configuration
WORK_START_TIME = '09:00'
LATE_THRESHOLD_MINUTES = 15

# Ensure directories exist
for directory in [DATABASE_DIR, DATASET_DIR, MODELS_DIR, REPORTS_DIR,
                  os.path.join(BASE_DIR, 'static', 'css'),
                  os.path.join(BASE_DIR, 'static', 'js'),
                  os.path.join(BASE_DIR, 'static', 'images')]:
    os.makedirs(directory, exist_ok=True)
