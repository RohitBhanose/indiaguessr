import sqlite3
import os

DB = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'indiaguessr.db'))
conn = sqlite3.connect(DB)
cur = conn.cursor()

cities = ['mumbai','pune','delhi','bengaluru','bangalore','chennai','hyderabad','ahmedabad','kolkata','jaipur','chandigarh','kochi','surat','indore','lucknow']

try:
    cur.execute("SELECT id, city, state, latitude, longitude FROM locations WHERE lower(mode)='india'")
    rows = cur.fetchall()
    matched = 0
    unmatched = 0
    city_counts = {c: 0 for c in cities}
    for r in rows:
        city_name = (r[1] or '').lower()
        state_name = (r[2] or '').lower()
        found = False
        for c in cities:
            if c in city_name or c in state_name:
                city_counts[c] += 1
                found = True
        if found:
            matched += 1
        else:
            unmatched += 1
            
    print(f"Total India locations: {len(rows)}")
    print(f"Matched prioritized cities: {matched}")
    print(f"Unmatched: {unmatched}")
    print("Prioritized City counts:")
    for c, count in city_counts.items():
        if count > 0:
            print(f"  {c}: {count}")
finally:
    conn.close()
