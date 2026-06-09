#!/usr/bin/env python3
import asyncio
import math
import random
import sys
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List

import httpx
from sqlalchemy import select, func, delete

from app.core.database import AsyncSessionLocal
from app.models.location import Location
from app.core.config import settings
from app.services.geo import point_in_india
from app.services.geocode import reverse_geocode, classify_category_from_meta

sys.stdout.reconfigure(encoding='utf-8')

API_KEY = settings.GOOGLE_MAPS_API_KEY
if not API_KEY:
    print("WARNING: GOOGLE_MAPS_API_KEY settings is empty. Seeding/verification will fail.")
    API_KEY = "" # Fallback key from code

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlon / 2.0) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

async def fetch_streetview_meta(http: httpx.AsyncClient, lat: float, lng: float, radius: int = 200) -> Optional[dict]:
    url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={lat},{lng}&radius={radius}&key={API_KEY}"
    try:
        r = await http.get(url, timeout=10.0)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "OK":
                pano = data.get("pano_id") or data.get("panoId") or (data.get("location") or {}).get("pano") or ""
                copyright = data.get("copyright") or ""
                loc_data = data.get("location") or {}
                actual_lat = loc_data.get("lat") or lat
                actual_lng = loc_data.get("lng") or lng
                return {
                    'pano': pano,
                    'copyright': copyright,
                    'lat': actual_lat,
                    'lng': actual_lng,
                    'raw': data
                }
    except Exception:
        pass
    return None

async def validate_location(http: httpx.AsyncClient, lat: float, lng: float, mode: str, db_country: Optional[str] = None) -> Tuple[bool, str, Optional[dict]]:
    # Get Street View meta (using a larger radius of 1000m to seed/find points more reliably)
    meta = await fetch_streetview_meta(http, lat, lng, radius=1000)
    if not meta:
        return False, "no_street_view_metadata", None
    
    # 1. Verify official Google coverage only
    copyright_lower = (meta['copyright'] or '').lower()
    pano_id = meta['pano']
    
    is_official = False
    if 'google' in copyright_lower or 'trekker' in copyright_lower or 'street view' in copyright_lower:
        is_official = True
    elif pano_id.startswith('CAoS'):
        is_official = True
        
    if not is_official:
        return False, "user_contributed_photo_sphere", meta

    # 2. Verify navigability (links check is deferred to frontend because HTTP metadata API doesn't return links count)

    # 3. Double check country and indoor/business status via reverse geocode
    country, state, city, geo_meta = await reverse_geocode(meta['lat'], meta['lng'])
    if not country:
        country = db_country or ""
        geo_meta = {}

    country_lower = country.lower()
    if mode.lower() == 'india' and 'india' not in country_lower:
        return False, "outside_india", meta

    # Check indoor business keywords
    formatted_address = (geo_meta.get('raw', {}).get('formatted_address', '')).lower()
    types = [t.lower() for t in geo_meta.get('types', [])]
    business_keywords = [
        'hotel', 'restaurant', 'museum', 'temple', 'inn', 'cafe', 'bar', 'mall', 
        'shop', 'clinic', 'hospital', 'resort', 'lodge', 'theater', 'office', 'temple_interior'
    ]
    
    indoor_reject = False
    if any(k in formatted_address for k in business_keywords) and 'route' not in types:
        indoor_reject = True
    
    if indoor_reject:
        return False, "indoor_or_business_premises", meta

    # Output details
    meta['country'] = country
    meta['state'] = state
    meta['city'] = city
    meta['geo_meta'] = geo_meta
    return True, "valid", meta

async def clean_database():
    print("=== STARTING DATABASE CLEANING PASS ===")
    async with AsyncSessionLocal() as db:
        stmt = select(Location).where((Location.verified != True) | (Location.verified == None))
        result = await db.execute(stmt)
        locations = result.scalars().all()
        
        print(f"Checking {len(locations)} unverified database entries...")
        
        deleted_count = 0
        updated_count = 0
        
        async with httpx.AsyncClient() as http:
            for loc in locations:
                valid, reason, meta = await validate_location(http, loc.latitude, loc.longitude, loc.mode, loc.country)
                if not valid:
                    print(f"REJECTED: ID={loc.id} mode={loc.mode} lat={loc.latitude:.6f} lng={loc.longitude:.6f} reason={reason}")
                    await db.delete(loc)
                    deleted_count += 1
                else:
                    new_cat = classify_category_from_meta(meta['geo_meta'], loc.city or meta['city'])
                    if new_cat and new_cat != (loc.category or '').lower():
                        loc.category = new_cat
                        updated_count += 1
                    
                    loc.panorama_id = meta['pano']
                    loc.country = meta['country'] or loc.country
                    loc.state = meta['state'] or loc.state
                    loc.city = meta['city'] or loc.city
                    loc.verified = True
                    loc.last_verified_at = datetime.utcnow()
                    db.add(loc)
                    
            await db.commit()
            
        print(f"Cleaning complete. Purged: {deleted_count} invalid locations. Re-verified/updated: {len(locations) - deleted_count} (updated category in {updated_count} rows).")

# SEEDING DATA DEFINITIONS

PRIORITIZED_CITIES = [
    {"name": "Mumbai", "lat": 19.0760, "lng": 72.8777},
    {"name": "Pune", "lat": 18.5204, "lng": 73.8567},
    {"name": "Delhi", "lat": 28.6139, "lng": 77.2090},
    {"name": "Bengaluru", "lat": 12.9716, "lng": 77.5946},
    {"name": "Chennai", "lat": 13.0827, "lng": 80.2707},
    {"name": "Hyderabad", "lat": 17.3850, "lng": 78.4867},
    {"name": "Ahmedabad", "lat": 23.0225, "lng": 72.5714},
    {"name": "Kolkata", "lat": 22.5726, "lng": 88.3639},
    {"name": "Jaipur", "lat": 26.9124, "lng": 75.7873},
    {"name": "Lucknow", "lat": 26.8467, "lng": 80.9462},
    {"name": "Chandigarh", "lat": 30.7333, "lng": 76.7794},
    {"name": "Kochi", "lat": 9.9312, "lng": 76.2673},
    {"name": "Surat", "lat": 21.1702, "lng": 72.8311},
    {"name": "Indore", "lat": 22.7196, "lng": 75.8577}
]

HIGHWAYS_INDIA = [
    {"start": (26.9124, 75.7873), "end": (28.6139, 77.2090)},
    {"start": (18.5204, 73.8567), "end": (17.6914, 73.9918)},
    {"start": (12.9716, 77.5946), "end": (11.6643, 78.1460)},
    {"start": (28.6139, 77.2090), "end": (27.1767, 78.0081)},
    {"start": (15.4909, 73.8278), "end": (14.8080, 74.1305)}
]

LANDMARKS_INDIA = [
    {"name": "Taj Mahal", "lat": 27.1751, "lng": 78.0421},
    {"name": "Gateway of India", "lat": 18.9220, "lng": 72.8347},
    {"name": "Qutub Minar", "lat": 28.5244, "lng": 77.1855},
    {"name": "Red Fort", "lat": 28.6562, "lng": 77.2410},
    {"name": "Humayun's Tomb", "lat": 28.5933, "lng": 77.2507},
    {"name": "Victoria Memorial", "lat": 22.5448, "lng": 88.3426},
    {"name": "Charminar", "lat": 17.3616, "lng": 78.4747},
    {"name": "Hawa Mahal", "lat": 26.9124, "lng": 75.8264},
    {"name": "Mysore Palace", "lat": 12.3052, "lng": 76.6552},
    {"name": "Amer Fort", "lat": 26.9855, "lng": 75.8513},
    {"name": "India Gate", "lat": 28.6129, "lng": 77.2295},
    {"name": "Brihadisvara Temple", "lat": 10.7828, "lng": 79.1322},
    {"name": "Sun Temple Konark", "lat": 19.8876, "lng": 86.0945},
    {"name": "Fatehpur Sikri", "lat": 27.0945, "lng": 77.6679},
    {"name": "Mehrangarh Fort", "lat": 26.2978, "lng": 73.0189}
]

CURATED_WORLD_CITIES = [
    (40.7128, -74.0060), # New York
    (34.0522, -118.2437), # Los Angeles
    (41.8781, -87.6298), # Chicago
    (51.5074, -0.1278), # London
    (48.8566, 2.3522), # Paris
    (52.5200, 13.4050), # Berlin
    (19.4326, -99.1332), # Mexico City
    (34.6937, 135.5023), # Osaka
    (35.6895, 139.6917), # Tokyo
    (31.2304, 121.4737), # Shanghai
    (39.9042, 116.4074), # Beijing
    (55.7558, 37.6173), # Moscow
    (28.6139, 77.2090), # Delhi
    (19.0760, 72.8777), # Mumbai
    (13.0827, 80.2707), # Chennai
    (12.9716, 77.5946), # Bengaluru
    (23.0225, 72.5714), # Ahmedabad
    (-23.5505, -46.6333), # Sao Paulo
    (-34.6037, -58.3816), # Buenos Aires
    (43.6532, -79.3832), # Toronto
    (1.3521, 103.8198), # Singapore
    (3.1390, 101.6869), # Kuala Lumpur
    (31.7683, 35.2137), # Jerusalem
    (30.0444, 31.2357), # Cairo
    (25.2048, 55.2708), # Dubai
    (39.9255, 32.8663), # Ankara
    (37.9838, 23.7275), # Athens
    (22.5726, 88.3639), # Kolkata
    (-33.9249, 18.4241), # Cape Town
    (6.5244, 3.3792), # Lagos
    (14.5995, 120.9842), # Manila
    (37.5665, 126.9780), # Seoul
    (55.9533, -3.1883), # Edinburgh
    (-37.8136, 144.9631), # Melbourne
    (-33.8688, 151.2093), # Sydney
    (50.1109, 8.6821), # Frankfurt
    (45.4642, 9.1900), # Milan
    (41.9028, 12.4964), # Rome
    (40.4168, -3.7038), # Madrid
    (59.9343, 30.3351), # Saint Petersburg
    (60.1699, 24.9384) # Helsinki
]

async def seed_locations(mode: str, target: int):
    mode = mode.lower()
    print(f"\n=== STARTING SEEDING PASS FOR {mode.upper()} MODE ===")
    
    async with httpx.AsyncClient() as http:
        async with AsyncSessionLocal() as db:
            res_cnt = await db.execute(select(func.count()).select_from(Location).where(func.lower(Location.mode) == mode, Location.verified == True))
            existing_count = res_cnt.scalar_one()
            
            res_coords = await db.execute(select(Location.latitude, Location.longitude).where(func.lower(Location.mode) == mode))
            existing_coords = [(round(lat, 4), round(lng, 4)) for lat, lng in res_coords.all()]
            
            needed = target - existing_count
            if needed <= 0:
                print(f"Target of {target} locations for {mode} already satisfied. Currently: {existing_count}")
                return
            
            print(f"Current count: {existing_count}. Seeding {needed} new verified locations to reach target of {target}...")
            
            seeded = 0
            attempts = 0
            
            if mode == 'india':
                target_cats = {
                    'urban': int(target * 0.50),
                    'suburban': int(target * 0.20),
                    'rural': int(target * 0.20),
                    'highway': int(target * 0.05),
                    'landmark': int(target * 0.05)
                }
                
                cat_counts = {'urban': 0, 'suburban': 0, 'rural': 0, 'highway': 0, 'landmark': 0}
                res_cat = await db.execute(select(Location.category, func.count()).where(func.lower(Location.mode) == 'india', Location.verified == True).group_by(Location.category))
                for c, count in res_cat.all():
                    if c in cat_counts:
                        cat_counts[c] = count
                
                print(f"Current category counts: {cat_counts}")
                print(f"Target category counts: {target_cats}")
                
                while seeded < needed and attempts < 5000:
                    attempts += 1
                    underfilled = [c for c in target_cats if cat_counts[c] < target_cats[c]]
                    if not underfilled:
                        underfilled = ['urban', 'suburban']
                        
                    chosen_cat = random.choice(underfilled)
                    lat, lng = 0.0, 0.0
                    
                    if chosen_cat == 'urban':
                        city = random.choice(PRIORITIZED_CITIES)
                        r_m = random.uniform(0, 4000)
                        theta = random.uniform(0, 2 * math.pi)
                        dlat = (r_m * math.cos(theta)) / 111320.0
                        dlng = (r_m * math.sin(theta)) / (111320.0 * math.cos(math.radians(city['lat'])))
                        lat = city['lat'] + dlat
                        lng = city['lng'] + dlng
                        
                    elif chosen_cat == 'suburban':
                        city = random.choice(PRIORITIZED_CITIES)
                        r_m = random.uniform(4000, 15000)
                        theta = random.uniform(0, 2 * math.pi)
                        dlat = (r_m * math.cos(theta)) / 111320.0
                        dlng = (r_m * math.sin(theta)) / (111320.0 * math.cos(math.radians(city['lat'])))
                        lat = city['lat'] + dlat
                        lng = city['lng'] + dlng
                        
                    elif chosen_cat == 'rural':
                        city = random.choice(PRIORITIZED_CITIES)
                        r_m = random.uniform(15000, 45000)
                        theta = random.uniform(0, 2 * math.pi)
                        dlat = (r_m * math.cos(theta)) / 111320.0
                        dlng = (r_m * math.sin(theta)) / (111320.0 * math.cos(math.radians(city['lat'])))
                        lat = city['lat'] + dlat
                        lng = city['lng'] + dlng
                        
                    elif chosen_cat == 'highway':
                        hwy = random.choice(HIGHWAYS_INDIA)
                        t = random.uniform(0, 1)
                        lat = hwy['start'][0] + t * (hwy['end'][0] - hwy['start'][0])
                        lng = hwy['start'][1] + t * (hwy['end'][1] - hwy['start'][1])
                        r_m = random.uniform(0, 50)
                        theta = random.uniform(0, 2 * math.pi)
                        dlat = (r_m * math.cos(theta)) / 111320.0
                        dlng = (r_m * math.sin(theta)) / (111320.0 * math.cos(math.radians(lat)))
                        lat += dlat
                        lng += dlng
                        
                    elif chosen_cat == 'landmark':
                        landmark = random.choice(LANDMARKS_INDIA)
                        lat = landmark['lat']
                        lng = landmark['lng']
                        r_m = random.uniform(0, 50)
                        theta = random.uniform(0, 2 * math.pi)
                        dlat = (r_m * math.cos(theta)) / 111320.0
                        dlng = (r_m * math.sin(theta)) / (111320.0 * math.cos(math.radians(lat)))
                        lat += dlat
                        lng += dlng

                    rounded_coord = (round(lat, 4), round(lng, 4))
                    if rounded_coord in existing_coords:
                        continue
                        
                    valid, reason, SV_meta = await validate_location(http, lat, lng, mode)
                    if valid and SV_meta:
                        derived_cat = chosen_cat
                            
                        loc = Location(
                            latitude=SV_meta['lat'],
                            longitude=SV_meta['lng'],
                            country=SV_meta['country'] or "India",
                            state=SV_meta['state'],
                            city=SV_meta['city'],
                            mode=mode,
                            category=derived_cat,
                            panorama_id=SV_meta['pano'],
                            verified=True,
                            last_verified_at=datetime.utcnow()
                        )
                        db.add(loc)
                        await db.commit()
                        
                        existing_coords.append((round(SV_meta['lat'], 4), round(SV_meta['lng'], 4)))
                        cat_counts[derived_cat] += 1
                        seeded += 1
                        print(f"SUCCESS {seeded}: category={derived_cat} in {SV_meta['city'] or city.get('name', 'Unknown')}, lat={SV_meta['lat']:.6f}, lng={SV_meta['lng']:.6f}, pano={SV_meta['pano']}")
                        await asyncio.sleep(0.05)
                        
            elif mode == 'world':
                city_iter = iter(CURATED_WORLD_CITIES)
                while seeded < needed and attempts < 5000:
                    attempts += 1
                    try:
                        base = next(city_iter)
                    except StopIteration:
                        city_iter = iter(CURATED_WORLD_CITIES)
                        base = next(city_iter)
                        
                    lat0, lng0 = base
                    r_m = random.uniform(0, 15000)
                    theta = random.uniform(0, 2 * math.pi)
                    dlat = (r_m * math.cos(theta)) / 111320.0
                    dlng = (r_m * math.sin(theta)) / (111320.0 * math.cos(math.radians(lat0)))
                    lat = lat0 + dlat
                    lng = lng0 + dlng
                    
                    rounded_coord = (round(lat, 4), round(lng, 4))
                    if rounded_coord in existing_coords:
                        continue
                        
                    valid, reason, SV_meta = await validate_location(http, lat, lng, mode)
                    if valid and SV_meta:
                        derived_cat = classify_category_from_meta(SV_meta['geo_meta'], SV_meta['city'])
                        if derived_cat == 'unknown':
                            derived_cat = 'urban'
                            
                        loc = Location(
                            latitude=SV_meta['lat'],
                            longitude=SV_meta['lng'],
                            country=SV_meta['country'] or "",
                            state=SV_meta['state'],
                            city=SV_meta['city'],
                            mode=mode,
                            category=derived_cat,
                            panorama_id=SV_meta['pano'],
                            verified=True,
                            last_verified_at=datetime.utcnow()
                        )
                        db.add(loc)
                        await db.commit()
                        
                        existing_coords.append((round(SV_meta['lat'], 4), round(SV_meta['lng'], 4)))
                        seeded += 1
                        print(f"SUCCESS {seeded}: country={SV_meta['country']}, city={SV_meta['city']}, lat={SV_meta['lat']:.6f}, lng={SV_meta['lng']:.6f}, pano={SV_meta['pano']}")
                        await asyncio.sleep(0.05)

            print(f"Seeding completed. Added {seeded} new locations for {mode}.")

async def main():
    await clean_database()
    await seed_locations('india', 300)
    await seed_locations('world', 500)

if __name__ == '__main__':
    asyncio.run(main())
