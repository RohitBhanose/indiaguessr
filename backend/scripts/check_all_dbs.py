import os, sqlite3, json, datetime

workspace = os.path.abspath(os.getcwd())
paths = [
    os.path.join(workspace, 'indiaguessr.db'),
    os.path.join(workspace, 'backend', 'indiaguessr.db')
]

for p in paths:
    print('DB path:', p)
    if not os.path.exists(p):
        print('  MISSING')
        continue
    stat = os.stat(p)
    print('  size:', stat.st_size, 'bytes')
    print('  mtime:', datetime.datetime.fromtimestamp(stat.st_mtime).isoformat())
    conn = sqlite3.connect(p)
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        print('  tables:', cur.fetchall())
        cur.execute('SELECT COUNT(*) FROM locations')
        total = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM locations WHERE lower(mode)='india'")
        india = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM locations WHERE lower(mode)='world'")
        world = cur.fetchone()[0]
        print('  counts:', json.dumps({'total': total, 'india': india, 'world': world}))
        cur.execute("SELECT id, mode, category, country, panorama_id, last_verified_at FROM locations ORDER BY id LIMIT 10")
        rows = cur.fetchall()
        print('  sample rows:')
        for r in rows:
            print('   ', r)
    except Exception as e:
        print('  ERROR reading DB:', e)
    finally:
        conn.close()
    print()
