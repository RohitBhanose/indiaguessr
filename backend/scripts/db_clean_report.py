import sqlite3, os, json
DB = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'indiaguessr.db'))
print('DB file:', DB)
conn = sqlite3.connect(DB)
cur = conn.cursor()
try:
    cur.execute("SELECT COUNT(*) FROM locations WHERE lower(mode)='india'")
    total_india = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM locations WHERE lower(mode)='india' AND (country IS NULL OR lower(country) NOT LIKE '%india%')")
    non_india = cur.fetchone()[0]
    print(json.dumps({'total_india': total_india, 'non_india_by_country_field': non_india}, indent=2))
    cur.execute("SELECT id, latitude, longitude, country FROM locations WHERE lower(mode)='india' AND (country IS NULL OR lower(country) NOT LIKE '%india%') LIMIT 20")
    rows = cur.fetchall()
    for r in rows:
        print(r)
finally:
    conn.close()
