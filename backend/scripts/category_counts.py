import sqlite3, os, json
DB = os.path.join(os.path.dirname(__file__), '..', 'indiaguessr.db')
DB = os.path.normpath(DB)
conn = sqlite3.connect(DB)
cur = conn.cursor()
print('DB file:', DB)
try:
    cur.execute("SELECT category, COUNT(*) FROM locations WHERE lower(mode)='india' GROUP BY category")
    rows = cur.fetchall()
    print('India category counts:', json.dumps({r[0]: r[1] for r in rows}, indent=2))
    cur.execute("SELECT COUNT(*) FROM locations WHERE lower(mode)='world'")
    world = cur.fetchone()[0]
    print('World total:', world)
finally:
    conn.close()
