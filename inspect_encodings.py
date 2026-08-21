"""
Quick script to inspect stored face encodings.
Run with:  python inspect_encodings.py
"""
import sqlite3
import json

DB_PATH = "database/attendance.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT employee_id, name, department, position, face_encoding FROM employees"
).fetchall()

print(f"\n{'='*60}")
print(f"  Face Encodings Summary  —  {DB_PATH}")
print(f"{'='*60}")
print(f"  Total employees : {len(rows)}")

encoded = [r for r in rows if r['face_encoding']]
not_encoded = [r for r in rows if not r['face_encoding']]

print(f"  With encoding   : {len(encoded)}")
print(f"  Without encoding: {len(not_encoded)}")
print(f"{'='*60}\n")

for r in rows:
    has = r['face_encoding'] is not None
    if has:
        vec = json.loads(r['face_encoding'])
        status = f"✅  vector length = {len(vec)}"
    else:
        status = "❌  NO ENCODING (face not trained)"

    print(f"  [{r['employee_id']}]  {r['name']:<20}  {r['department']:<15}  {status}")

print()
conn.close()
