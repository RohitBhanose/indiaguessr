import sqlite3
import os

DB = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'indiaguessr.db'))
conn = sqlite3.connect(DB)
cur = conn.cursor()

try:
    cur.execute("SELECT id, country, state, city, category FROM locations WHERE lower(mode)='india'")
    rows = cur.fetchall()
    print("India-mode locations (state, city, category):")
    for r in rows:
        print(f"ID={r[0]}: state={r[2]}, city={r[3]}, current_cat={r[4]}")
finally:
    conn.close()
