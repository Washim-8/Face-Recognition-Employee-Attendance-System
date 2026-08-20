import os
from dotenv import load_dotenv

# Load .env file when running locally (no-op in production if not present)
load_dotenv()

# ── Base directory ────────────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ── Database ──────────────────────────────────────────────────────────────────
# Supabase / any PostgreSQL → set DATABASE_URL in the environment.
# Falls back to local SQLite for development.
DATABASE_URL = os.environ.get('DATABASE_URL', '')

# Render / some PaaS providers prefix the URL with "postgres://" which
# psycopg2 doesn't accept — normalise it to "postgresql://".
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

USE_POSTGRES = DATABASE_URL.startswith('postgresql://')

# SQLite paths (used only when USE_POSTGRES is False)
DATABASE_DIR  = os.path.join(BASE_DIR, 'database')
DATABASE_PATH = os.path.join(DATABASE_DIR, 'attendance.db')

# ── Local filesystem paths ────────────────────────────────────────────────────
# On Render the filesystem is ephemeral; dataset / model files don't persist
# across deploys.  Face encodings are stored in the DB so recognition still
# works.  The dataset dir is only needed for the capture → train workflow.
DATASET_DIR     = os.path.join(BASE_DIR, 'dataset')
MODELS_DIR      = os.path.join(BASE_DIR, 'models')
FACE_MODEL_PATH = os.path.join(MODELS_DIR, 'face_model.pkl')
REPORTS_DIR     = os.path.join(BASE_DIR, 'reports')

# ── Flask ─────────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-me-in-production')
DEBUG      = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
PORT       = int(os.environ.get('PORT', 5000))

# ── Admin credentials (used only to seed the DB on first run) ─────────────────
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# ── Face recognition ──────────────────────────────────────────────────────────
FACE_RECOGNITION_TOLERANCE = float(
    os.environ.get('FACE_RECOGNITION_TOLERANCE', '0.5')
)
IMAGES_PER_EMPLOYEE = int(os.environ.get('IMAGES_PER_EMPLOYEE', '30'))

# ── Working-hours ─────────────────────────────────────────────────────────────
WORK_START_TIME       = os.environ.get('WORK_START_TIME', '09:00')
LATE_THRESHOLD_MINUTES = int(os.environ.get('LATE_THRESHOLD_MINUTES', '15'))

# ── Ensure local directories exist (safe to call even on Render) ──────────────
for _dir in [DATABASE_DIR, DATASET_DIR, MODELS_DIR, REPORTS_DIR,
             os.path.join(BASE_DIR, 'static', 'css'),
             os.path.join(BASE_DIR, 'static', 'js'),
             os.path.join(BASE_DIR, 'static', 'images')]:
    os.makedirs(_dir, exist_ok=True)
