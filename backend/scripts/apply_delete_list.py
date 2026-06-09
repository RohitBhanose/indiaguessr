import sqlite3, os

DB = os.path.join(os.path.dirname(__file__), '..', 'indiaguessr.db')
DB = os.path.normpath(DB)
print('DB file:', DB)
conn = sqlite3.connect(DB)
cur = conn.cursor()
try:
    cur.execute("SELECT COUNT(*) FROM locations WHERE lower(mode)='india'")
    before = cur.fetchone()[0]
    print('india_before', before)
    ids = [4,43,46,57,61,71,78,84,100,101,107,117,119,132,137,152,174]
    placeholders = ','.join(['?']*len(ids))
    cur.execute(f"DELETE FROM locations WHERE id IN ({placeholders})", ids)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM locations WHERE lower(mode)='india'")
    after = cur.fetchone()[0]
    print('india_after', after)
    cur.execute("SELECT COUNT(*) FROM locations WHERE lower(mode)='india' AND (country IS NULL OR lower(country) NOT LIKE '%india%')")
    non_india = cur.fetchone()[0]
    print('india_non_india_remaining', non_india)
except Exception as e:
    print('ERROR', e)
finally:
    conn.close()
