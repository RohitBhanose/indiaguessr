#!/usr/bin/env python3
"""Verbose test harness for world seeding (diagnostics only).

Usage:
  python world_seed_test.py --target 25 --min-distance 100 --sleep 0.1

This script replicates the `mode=='world'` branch from `seed_verified_locations.py`
but prints verbose accept/reject reasons and final DB counts. It writes to the DB
configured by `DATABASE_URL` / settings.DATABASE_URL.
"""
import argparse
import asyncio
import math
import random
import os
import sqlite3
from datetime import datetime

import httpx
from sqlalchemy import select, func

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.location import Location
from app.services.geocode import reverse_geocode, classify_category_from_meta


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def check_panorama(http: httpx.AsyncClient, lat: float, lng: float, api_key: str):
    if not api_key:
        return None
    url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={lat},{lng}&key={api_key}"
    try:
        r = await http.get(url, timeout=10.0)
        if r.status_code != 200:
            return None
        data = r.json()
        status = data.get("status")
        if status == "OK":
            pano = (
                data.get("pano_id")
                or data.get("panoId")
                or data.get("pano")
                or data.get("id")
                or ""
            )
            return pano
    except Exception as e:
        return None
    return None


async def run_test(target: int, min_distance_m: int, sleep_s: float, apikey: str):
    print('Using DATABASE_URL=', settings.DATABASE_URL)
    curated_world_cities = [
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
        (-33.9249, 18.4241), # Cape Town
        (6.5244, 3.3792), # Lagos
        (14.5995, 120.9842), # Manila
        (37.5665, 126.9780), # Seoul
        (-33.8688, 151.2093), # Sydney
    ]

    attempts = 0
    accepted = 0
    rejected = []
    seen = []

    async with httpx.AsyncClient() as http:
        async with AsyncSessionLocal() as db:
            # Count existing world verified locations
            res = await db.execute(select(func.count()).select_from(Location).where(func.lower(Location.mode) == 'world', Location.verified == True))
            existing = res.scalar_one()
            print(f'Existing verified world locations: {existing}')
            target_remaining = max(0, target - existing)
            if target_remaining <= 0:
                print('Target already satisfied; nothing to do.')
                return

            print(f'Target remaining: {target_remaining}')

            city_iter = iter(curated_world_cities)
            while accepted < target_remaining:
                try:
                    base = next(city_iter)
                except StopIteration:
                    city_iter = iter(curated_world_cities)
                    base = next(city_iter)

                lat0, lng0 = base
                for _ in range(40):
                    if accepted >= target_remaining:
                        break
                    attempts += 1
                    # small offset up to ~2000m
                    r_m = random.uniform(0, 2000)
                    theta = random.uniform(0, 2 * math.pi)
                    dlat = (r_m * math.cos(theta)) / 111320.0
                    dlng = (r_m * math.sin(theta)) / (111320.0 * math.cos(math.radians(lat0)) if abs(lat0) < 89 else 1)
                    lat = lat0 + dlat
                    lng = lng0 + dlng

                    # in-memory dedupe
                    too_close = False
                    for (olat, olng) in seen:
                        if haversine_km(lat, lng, olat, olng) * 1000.0 < min_distance_m:
                            too_close = True
                            break
                    if too_close:
                        rejected.append({'lat': lat, 'lng': lng, 'reason': 'too_close_in_memory'})
                        if len(rejected) % 25 == 0:
                            print(f'Rejected so far: {len(rejected)}')
                        continue

                    # DB bounding box proximity check
                    deg_delta = min_distance_m / 111320.0
                    stmt = select(Location).where(
                        func.lower(Location.mode) == 'world',
                        Location.latitude.between(lat - deg_delta, lat + deg_delta),
                        Location.longitude.between(lng - deg_delta, lng + deg_delta)
                    ).limit(5)
                    res = await db.execute(stmt)
                    nearby = res.scalars().all()
                    if nearby:
                        close = False
                        for n in nearby:
                            if haversine_km(lat, lng, n.latitude, n.longitude) * 1000.0 < min_distance_m:
                                close = True
                                break
                        if close:
                            rejected.append({'lat': lat, 'lng': lng, 'reason': 'too_close_db'})
                            continue

                    pano = await check_panorama(http, lat, lng, apikey)
                    if not pano:
                        rejected.append({'lat': lat, 'lng': lng, 'reason': 'no_pano'})
                        continue

                    country, state, city, meta = await reverse_geocode(lat, lng)
                    # World mode accepts any country

                    # classify
                    cat = classify_category_from_meta(meta, city, default='unknown')

                    loc = Location(
                        latitude=lat,
                        longitude=lng,
                        country=country or "",
                        state=state,
                        city=city,
                        mode='world',
                        category=cat or 'unknown',
                        panorama_id=pano,
                        verified=True,
                        last_verified_at=datetime.utcnow()
                    )
                    db.add(loc)
                    try:
                        await db.commit()
                        accepted += 1
                        seen.append((lat, lng))
                        print(f'ACCEPTED id={getattr(loc, "id", "? ")} pano={pano} lat={lat:.6f} lng={lng:.6f} country={country} category={loc.category}')
                    except Exception as e:
                        await db.rollback()
                        rejected.append({'lat': lat, 'lng': lng, 'reason': 'db_insert_failed', 'error': str(e)})

                    await asyncio.sleep(sleep_s)

            # summary
            print('\n=== SUMMARY ===')
            print('DB file:', settings.DATABASE_URL)
            print('attempts:', attempts)
            print('accepted:', accepted)
            print('rejected:', len(rejected))
            for i, r in enumerate(rejected[:500], 1):
                print(f"REJ[{i}] reason={r.get('reason')} lat={r.get('lat'):.6f} lng={r.get('lng'):.6f} {r.get('error','')}")

    # final DB counts (sqlite quick-check)
    db_path = None
    if settings.DATABASE_URL.startswith('sqlite'):
        # extract path after triple slash
        db_path = settings.DATABASE_URL.split('///')[-1]
    else:
        db_path = None
    if db_path and os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM locations WHERE lower(mode)='world'")
        total_world = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM locations WHERE lower(mode)='world' AND verified=1")
        verified_world = cur.fetchone()[0]
        conn.close()
        print('final_total_world:', total_world)
        print('final_verified_world:', verified_world)
    else:
        print('Could not locate sqlite DB path from settings.DATABASE_URL')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--target', type=int, default=25)
    p.add_argument('--min-distance', type=int, default=100)
    p.add_argument('--sleep', type=float, default=0.2)
    p.add_argument('--apikey', type=str, default=None)
    args = p.parse_args()
    api_key = args.apikey
    if not api_key:
        api_key = os.environ.get('GOOGLE_MAPS_API_KEY') or os.environ.get('VITE_GOOGLE_MAPS_API_KEY') or getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
    asyncio.run(run_test(args.target, args.min_distance, args.sleep, api_key))
