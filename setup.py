"""
Setup script — initializes the database and creates necessary directories.
Run this ONCE before starting the Flask app.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("  Face Recognition Attendance System — Setup")
print("=" * 60)

# 1. Import config (creates directories)
import config

print("\n[OK] Directories created:")
for d in [config.DATABASE_DIR, config.DATASET_DIR, config.MODELS_DIR, config.REPORTS_DIR]:
    print(f"   {d}")

# 2. Initialize database
from utils.db_manager import init_database
init_database()

print("\n[OK] Setup complete!")
print("\n[INFO] Next Steps:")
print("   1. Install dependencies:  pip install -r requirements.txt")
print("   2. Start the app:         python app.py")
print("   3. Open browser:          http://127.0.0.1:5000")
print("   4. Admin login:           http://127.0.0.1:5000/admin/login")
print("   5. Credentials:           admin / admin123")
print("\n" + "=" * 60)
