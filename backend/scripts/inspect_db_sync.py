import sqlite3
import os
import json

DB = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'indiaguessr.db'))
print('DB file:', DB)
conn = sqlite3.connect(DB)
cur = conn.cursor()

try:
    # Mode count
    cur.execute("SELECT mode, COUNT(*) FROM locations GROUP BY mode")
    print("Mode counts:", cur.fetchall())

    # Categories for India
    cur.execute("SELECT category, COUNT(*) FROM locations WHERE lower(mode)='india' GROUP BY category")
    print("India Category counts:", cur.fetchall())

    # Categories for World
    cur.execute("SELECT category, COUNT(*) FROM locations WHERE lower(mode)='world' GROUP BY category")
    print("World Category counts:", cur.fetchall())

    # Country counts in World Mode
    cur.execute("SELECT country, COUNT(*) FROM locations WHERE lower(mode)='world' GROUP BY country ORDER BY COUNT(*) DESC")
    print("World Country counts (all):", cur.fetchall())

    # Duplicate panorama IDs in DB
    cur.execute("SELECT panorama_id, COUNT(*) FROM locations GROUP BY panorama_id HAVING COUNT(*) > 1")
    dup_panos = cur.fetchall()
    print("Duplicate panorama IDs in DB:", len(dup_panos), dup_panos)

    # Let's inspect some of the India-mode coordinates that might be outside India
    cur.execute("SELECT id, latitude, longitude, country, city, category, panorama_id FROM locations WHERE lower(mode)='india' LIMIT 5")
    print("India samples:")
    for r in cur.fetchall():
        print(r)

except Exception as e:
    print('ERROR:', e)
finally:
    conn.close()
