import sqlite3, json, os

DB = os.path.join(os.path.dirname(__file__), '..', 'indiaguessr.db')
DB = os.path.normpath(DB)
print('DB file:', DB)
conn = sqlite3.connect(DB)
cur = conn.cursor()
try:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print('tables:', cur.fetchall())
    cur.execute('SELECT COUNT(*) FROM locations')
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM locations WHERE lower(mode)='india'")
    india = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM locations WHERE lower(mode)='world'")
    world = cur.fetchone()[0]
    print(json.dumps({'total': total, 'india': india, 'world': world}, indent=2))
    # Dry-run: count India-mode rows whose stored country does not contain 'india'
    cur.execute("SELECT COUNT(*) FROM locations WHERE lower(mode)='india' AND (country IS NULL OR lower(country) NOT LIKE '%india%')")
    non_india = cur.fetchone()[0]
    print('India-mode rows with non-India stored country:', non_india)
    cur.execute("SELECT id, latitude, longitude, country, state, city, category, panorama_id, verified FROM locations ORDER BY id LIMIT 20")
    rows = cur.fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print('ERROR', e)
finally:
    conn.close()
