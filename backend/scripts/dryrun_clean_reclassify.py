import asyncio
import sqlite3
import os
import sys
import httpx
from typing import Optional, Tuple, Dict, Any

sys.stdout.reconfigure(encoding='utf-8')

DB = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'indiaguessr.db'))
print('DB file:', DB)

API_KEY = ""

def classify_category(country: str, state: str, city: str, meta: Dict[str, Any]) -> str:
    large_cities = {
        'mumbai', 'pune', 'delhi', 'new delhi', 'bangalore', 'bengaluru', 'chennai', 'hyderabad', 'ahmedabad',
        'kolkata', 'jaipur', 'chandigarh', 'kochi', 'surat', 'indore', 'lucknow'
    }
    
    co = (country or '').strip().lower()
    st = (state or '').strip().lower()
    ci = (city or '').strip().lower()
    
    if ci and any(x in ci for x in large_cities):
        return 'urban'
    if st and any(x in st for x in large_cities):
        return 'urban'
        
    provider = meta.get('provider')
    if provider == 'google':
        types = [t.lower() for t in meta.get('types', [])]
        comps = meta.get('components', {}) or {}
        raw = meta.get('raw') or {}
        formatted = (raw.get('formatted_address') or '').lower()
        
        # Landmark / POI signals
        if any(t in types for t in ("tourist_attraction", "point_of_interest", "establishment", "park", "natural_feature")):
            return 'landmark'
            
        # Highway/route signals
        if any('highway' in t or 'motorway' in t for t in types):
            return 'highway'
        if 'route' in types and not comps.get('locality'):
            return 'highway'
            
        # Neighborhood and sublocality -> suburban
        if comps.get('neighborhood') or comps.get('sublocality') or comps.get('sublocality_level_1') or comps.get('sublocality_level_2'):
            return 'suburban'
            
        # Locality / Postal town -> urban
        if comps.get('locality') or comps.get('postal_town') or comps.get('administrative_area_level_3'):
            return 'urban'
            
        # If the address contains words like village, rural, hamlet
        if any(kw in formatted for kw in ['village', 'hamlet', 'rural', 'farm', 'basti', 'khas']):
            return 'rural'
            
        if comps.get('administrative_area_level_2'):
            return 'suburban'
            
        return 'rural'
    else:
        if any(kw in ci for kw in ['village', 'hamlet', 'rural', 'farm', 'basti', 'khas']):
            return 'rural'
        if ci:
            return 'urban'
        if st:
            return 'suburban'
        return 'rural'

async def check_panorama(http: httpx.AsyncClient, lat: float, lng: float) -> Optional[dict]:
    # Query with source=outdoor to filter out indoor business/spheres
    url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={lat},{lng}&key={API_KEY}&source=outdoor"
    try:
        r = await http.get(url, timeout=10.0)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "OK":
                pano = data.get("pano_id") or data.get("panoId") or (data.get("location") or {}).get("pano") or ""
                copyright = data.get("copyright") or ""
                return {
                    'pano': pano,
                    'copyright': copyright,
                    'raw': data
                }
    except Exception:
        pass
    return None

async def reverse_geocode(http: httpx.AsyncClient, lat: float, lng: float) -> Tuple[Optional[str], Optional[str], Optional[str], dict]:
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={API_KEY}"
    try:
        r = await http.get(url, timeout=10.0)
        if r.status_code == 200:
            data = r.json()
            if data.get("results"):
                primary = data["results"][0]
                types = primary.get("types", [])
                comp_map = {}
                for c in primary.get("address_components", []):
                    for t in c.get("types", []):
                        comp_map.setdefault(t, c.get("long_name"))
                country = comp_map.get("country")
                state = comp_map.get("administrative_area_level_1")
                city = (
                    comp_map.get("locality")
                    or comp_map.get("postal_town")
                    or comp_map.get("administrative_area_level_2")
                )
                meta = {"provider": "google", "types": types, "components": comp_map, "raw": primary}
                return country, state, city, meta
    except Exception:
        pass
    return None, None, None, {}

async def dry_run():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT id, mode, latitude, longitude, country, state, city, category, panorama_id FROM locations")
    rows = cur.fetchall()
    conn.close()

    print(f"Total locations to analyze: {len(rows)}")

    stats = {
        'total': len(rows),
        'accepted_india': 0,
        'accepted_world': 0,
        'rejected_no_pano': 0,
        'rejected_photo_sphere': 0,
        'rejected_indoor': 0,
        'rejected_not_india': 0,
        'rejected_bangladesh': 0,
    }

    india_cats = {'urban': 0, 'suburban': 0, 'rural': 0, 'highway': 0, 'landmark': 0}
    world_cats = {'urban': 0, 'suburban': 0, 'rural': 0, 'highway': 0, 'landmark': 0}
    world_countries = {}

    semaphore = asyncio.Semaphore(15)

    async def process_row(http, row):
        lid, mode, lat, lng, country_db, state_db, city_db, cat_db, pano_db = row
        
        async with semaphore:
            pano_meta = await check_panorama(http, lat, lng)
            if not pano_meta:
                return 'rejected_no_pano', row, None, None, None, None
                
            pano_id = pano_meta['pano']
            copyright = pano_meta['copyright']
            
            copyright_lower = copyright.lower()
            is_official = False
            if 'google' in copyright_lower or 'trekker' in copyright_lower or 'street view' in copyright_lower:
                is_official = True
            elif pano_id.startswith('CAoS'):
                is_official = True
            
            if not is_official:
                return 'rejected_photo_sphere', row, None, None, None, None
                
            country, state, city, meta = await reverse_geocode(http, lat, lng)
            if not country:
                country = country_db
                state = state_db
                city = city_db
                meta = {'provider': 'db_fallback'}
                
            country_clean = (country or '').strip()
            country_lower = country_clean.lower()
            
            if mode == 'india' and 'india' not in country_lower:
                return 'rejected_not_india', row, country_clean, state, city, meta
                
            if 'bangladesh' in country_lower:
                return 'rejected_bangladesh', row, country_clean, state, city, meta
                
            indoor_reject = False
            formatted_address = (meta.get('raw', {}).get('formatted_address', '')).lower()
            types = [t.lower() for t in meta.get('types', [])]
            business_keywords = ['hotel', 'restaurant', 'museum', 'temple', 'inn', 'cafe', 'bar', 'mall', 'shop', 'clinic', 'hospital', 'resort', 'lodge']
            
            if any(k in formatted_address for k in business_keywords) and 'route' not in types:
                indoor_reject = True
                
            if indoor_reject:
                return 'rejected_indoor', row, country_clean, state, city, meta
                
            cat = classify_category(country_clean, state, city, meta)
            
            return 'accepted', row, country_clean, state, city, cat

    async with httpx.AsyncClient() as http:
        tasks = [process_row(http, r) for r in rows]
        results = await asyncio.gather(*tasks)

    to_delete = []
    to_update = []
    
    for res in results:
        status_code, row, country, state, city, val = res
        lid, mode, lat, lng, country_db, state_db, city_db, cat_db, pano_db = row
        
        if status_code == 'accepted':
            if mode == 'india':
                stats['accepted_india'] += 1
                india_cats[val] += 1
            else:
                stats['accepted_world'] += 1
                world_cats[val] += 1
                world_countries[country] = world_countries.get(country, 0) + 1
            to_update.append((lid, country, state, city, val))
        else:
            stats[status_code] = stats.get(status_code, 0) + 1
            to_delete.append((lid, mode, lat, lng, status_code))

    print("\n=== DRY-RUN RESULTS ===")
    print(f"Total processed: {stats['total']}")
    print(f"Accepted India: {stats['accepted_india']}")
    print(f"Accepted World: {stats['accepted_world']}")
    print(f"Rejected No Panorama (outdoor): {stats.get('rejected_no_pano', 0)}")
    print(f"Rejected Photo Sphere (User): {stats.get('rejected_photo_sphere', 0)}")
    print(f"Rejected Indoor / Business: {stats.get('rejected_indoor', 0)}")
    print(f"Rejected Not India (in India mode): {stats.get('rejected_not_india', 0)}")
    print(f"Rejected Bangladesh: {stats.get('rejected_bangladesh', 0)}")

    print("\n=== NEW INDIA CATEGORIES ===")
    for c, cnt in india_cats.items():
        print(f"  {c}: {cnt} ({cnt / max(1, stats['accepted_india']) * 100:.1f}%)")

    print("\n=== NEW WORLD CATEGORIES ===")
    for c, cnt in world_cats.items():
        print(f"  {c}: {cnt} ({cnt / max(1, stats['accepted_world']) * 100:.1f}%)")

    print("\n=== NEW WORLD COUNTRY DISTRIBUTION ===")
    sorted_countries = sorted(world_countries.items(), key=lambda x: x[1], reverse=True)
    for country, count in sorted_countries:
        print(f"  {country}: {count}")

    print(f"\nTotal to delete: {len(to_delete)}")
    print(f"Total to update: {len(to_update)}")

    if to_delete:
        print("\nSample rejections:")
        for r in to_delete[:15]:
            print(f"  ID={r[0]} mode={r[1]} lat={r[2]:.6f} lng={r[3]:.6f} reason={r[4]}")

if __name__ == '__main__':
    asyncio.run(dry_run())
