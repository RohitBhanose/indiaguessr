#!/usr/bin/env python3
"""
Seed verified Street View locations into the database.

Usage:
  python seed_verified_locations.py --mode india --target 500 --apikey YOUR_GOOGLE_API_KEY

This script samples candidate coordinates (randomly within a bounding box), checks
Google Street View metadata for panorama availability, reverse-geocodes the location
for country/state/city, and inserts verified locations into the `locations` table.

Notes:
- If you do not provide a Google API key, the script will still attempt to reverse
  geocode using Nominatim (OSM), but the Street View verification requires a
  Google key (otherwise panorama checks will always fail).
- The seeding process may take time depending on desired `--target` size and the
  success rate of the sampled points. Consider providing a CSV of candidate points
  for faster seeding in production.
"""
import argparse
import asyncio
import math
import random
from datetime import datetime
from typing import Optional, Tuple

import httpx
from app.services.geocode import reverse_geocode, classify_category_from_meta
from app.services.geo import point_in_india

from app.core.database import AsyncSessionLocal
from app.models.location import Location
from app.core.config import settings


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def check_panorama_meta(http: httpx.AsyncClient, lat: float, lng: float, api_key: str) -> Optional[dict]:
    """Fetch Street View metadata for a panorama near (lat,lng).

    Returns a dict with keys: pano, copyright, links (list), links_count, raw, status
    or None if no panorama metadata is available.
    """
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
            # Extract pano id and navigation links if present
            pano = (
                data.get("pano_id")
                or data.get("panoId")
                or data.get("pano")
                or data.get("id")
                or ""
            )
            # Links may be at top-level or under 'location'
            links = data.get('links') or (data.get('location') or {}).get('links') or []
            copyright = data.get('copyright') or ''
            return {
                'pano': pano,
                'copyright': copyright,
                'links': links,
                'links_count': len(links) if links else 0,
                'raw': data,
                'status': status,
            }
    except Exception:
        pass
    return None


async def seed(mode: str, target: int, api_key: Optional[str], min_distance_m: int, sleep_s: float):
    mode = mode.lower()
    async with httpx.AsyncClient() as http:
        async with AsyncSessionLocal() as db:
            # Count existing verified locations for this mode (case-insensitive)
            from sqlalchemy import select, func
            result = await db.execute(select(func.count()).select_from(Location).where(func.lower(Location.mode) == mode, Location.verified == True))
            existing_count = result.scalar_one()
            print(f"Existing verified locations for mode={mode}: {existing_count}")

            seeded = 0
            target_remaining = max(0, target - existing_count)
            if target_remaining <= 0:
                print("Target already satisfied; nothing to do.")
                return

            print(f"Seeding {target_remaining} new verified locations for mode={mode}...")

            # Bounding boxes (used for random sampling fallback)
            if mode == "india":
                lat_min, lat_max = 6.55, 35.5
                lon_min, lon_max = 68.0, 97.5
            else:
                # global - fallback boxes; for world mode we use a curated city list
                lat_min, lat_max = -58.0, 72.0
                lon_min, lon_max = -180.0, 180.0

            # Curated world cities (lat,lng) to seed world mode more reliably
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
                (19.0760, 72.8777), # Mumbai (duplicate allowed)
                (22.5726, 88.3639), # Kolkata
                (-33.9249, 18.4241), # Cape Town
                (35.6762, 139.6503), # Tokyo alt
                (6.5244, 3.3792), # Lagos
                (14.5995, 120.9842), # Manila
                (37.5665, 126.9780), # Seoul
                (28.7041, 77.1025), # Delhi alt
                (30.3165, 78.0322), # Dehradun (example)
                (55.9533, -3.1883), # Edinburgh
                (-37.8136, 144.9631), # Melbourne
                (-33.8688, 151.2093), # Sydney
                (50.1109, 8.6821), # Frankfurt
                (45.4642, 9.1900), # Milan
                (41.9028, 12.4964), # Rome
                (40.4168, -3.7038), # Madrid
                (59.9343, 30.3351), # Saint Petersburg
                (60.1699, 24.9384), # Helsinki
                (25.276987, 55.296249), # Dubai alt
            ]

            attempts = 0
            attempts = 0
            seen = []  # list of (lat,lng) already inserted in this run
            rejected = []  # collect rejection reasons for reporting
            # panorama diagnostics
            diag_accepted_official = 0
            diag_rejected_photo_sphere = 0
            diag_rejected_indoor = 0
            diag_rejected_dead_end = 0
            diag_rejected_no_links = 0

            # Helper to commit a found panorama
            async def commit_location(latp, lngp, pano, country, state, city, meta):
                nonlocal seeded, rejected
                # Use conservative default to avoid biased 'urban' assignment
                cat = classify_category_from_meta(meta, city, default='unknown')
                loc = Location(
                    latitude=latp,
                    longitude=lngp,
                    country=country or "",
                    state=state,
                    city=city,
                    mode=mode,
                    category=cat or "unknown",
                    panorama_id=pano,
                    verified=True,
                    last_verified_at=datetime.utcnow()
                )
                db.add(loc)
                try:
                    await db.commit()
                    seeded += 1
                    seen.append((latp, lngp))
                    if seeded % 10 == 0:
                        print(f"Seeded {seeded}/{target_remaining} new locations...")
                    # Log acceptance with id and pano
                    try:
                        lid = getattr(loc, 'id', None)
                        print(f"ACCEPTED id={lid} pano={pano} lat={latp:.6f} lng={lngp:.6f} country={country} category={loc.category}")
                    except Exception:
                        pass
                    return True
                except Exception as e:
                    await db.rollback()
                    err = str(e)
                    print("DB insert failed:", err)
                    rejected.append({'lat': latp, 'lng': lngp, 'reason': 'db_insert_failed', 'error': err})
                return False

            # For world mode, prefer curated city sampling for reliable coverage
            if mode == 'world':
                city_iter = iter(curated_world_cities)
                while seeded < target_remaining:
                    try:
                        base = next(city_iter)
                    except StopIteration:
                        # restart once we've exhausted the list to add more offsets
                        city_iter = iter(curated_world_cities)
                        base = next(city_iter)

                    lat0, lng0 = base
                    # try a handful of offsets around the city
                    for _ in range(20):
                        if seeded >= target_remaining:
                            break
                        attempts += 1
                        # small offset in meters (up to ~2000m)
                        r_m = random.uniform(0, 2000)
                        theta = random.uniform(0, 2 * math.pi)
                        # approx conversion: 1 deg lat ~ 111320 m
                        dlat = (r_m * math.cos(theta)) / 111320.0
                        dlng = (r_m * math.sin(theta)) / (111320.0 * math.cos(math.radians(lat0)) if abs(lat0) < 89 else 1)
                        lat = lat0 + dlat
                        lng = lng0 + dlng

                        # quick in-memory proximity dedupe
                        too_close = False
                        for (olat, olng) in seen:
                            if haversine_km(lat, lng, olat, olng) * 1000.0 < min_distance_m:
                                too_close = True
                                break
                        if too_close:
                            rejected.append({'lat': lat, 'lng': lng, 'reason': 'too_close_in_memory'})
                            continue

                        panomet = await check_panorama_meta(http, lat, lng, api_key)
                        if not panomet:
                            rejected.append({'lat': lat, 'lng': lng, 'reason': 'no_pano'})
                            continue

                        # Reject zero-link panoramas
                        if panomet.get('links_count', 0) == 0:
                            diag_rejected_no_links += 1
                            rejected.append({'lat': lat, 'lng': lng, 'reason': 'no_links'})
                            continue
                        # Reject one-link / dead-end panoramas (one-way dead-ends)
                        if panomet.get('links_count', 0) <= 1:
                            diag_rejected_dead_end += 1
                            rejected.append({'lat': lat, 'lng': lng, 'reason': 'dead_end'})
                            continue

                        # Reject user-contributed Photo Spheres / non-official panoramas
                        copyright = (panomet.get('copyright') or '').lower()
                        pano_id = panomet.get('pano') or ''
                        is_official = False
                        if 'google' in copyright:
                            is_official = True
                        # heuristics: many official pano ids start with 'CAoS' / 'CAoSF' — accept those
                        if pano_id and pano_id.startswith('CAoS'):
                            is_official = True
                        if not is_official:
                            diag_rejected_photo_sphere += 1
                            rejected.append({'lat': lat, 'lng': lng, 'reason': 'photo_sphere'})
                            continue

                        # Reverse-geocode for classification and further indoor/business checks
                        country, state, city, meta = await reverse_geocode(lat, lng)

                        # Basic indoor/business heuristics: reject if geocode indicates indoor/business premises
                        prov = meta.get('provider')
                        indoor_reject = False
                        if prov == 'google':
                            raw = meta.get('raw') or {}
                            types = [t.lower() for t in (meta.get('types') or [])]
                            formatted = (raw.get('formatted_address') or '').lower() if isinstance(raw, dict) else ''
                            business_keywords = ['hotel', 'restaurant', 'museum', 'temple', 'inn', 'cafe', 'bar', 'mall', 'shop', 'clinic', 'hospital']
                            if any(k in formatted for k in business_keywords) and 'route' not in types:
                                indoor_reject = True
                        elif prov == 'nominatim':
                            raw = meta.get('raw') or {}
                            addr = (raw.get('address') or {}) if isinstance(raw, dict) else {}
                            amen = (addr.get('amenity') or '').lower()
                            if amen in ('restaurant', 'cafe', 'hotel', 'museum', 'place_of_worship', 'library'):
                                indoor_reject = True

                        if indoor_reject:
                            diag_rejected_indoor += 1
                            rejected.append({'lat': lat, 'lng': lng, 'reason': 'indoor_or_business'})
                            continue

                        # Passed all panorama quality checks — commit
                        ok = await commit_location(lat, lng, panomet.get('pano'), country, state, city, meta)
                        if ok:
                            diag_accepted_official += 1
                        await asyncio.sleep(sleep_s)

                print(f"World seeding finished. Seeded {seeded} new locations (attempts={attempts}).")
                # Panorama diagnostics summary
                print("Panorama diagnostics summary:")
                print(f"  accepted_official: {diag_accepted_official}")
                print(f"  rejected_photo_sphere: {diag_rejected_photo_sphere}")
                print(f"  rejected_indoor_or_business: {diag_rejected_indoor}")
                print(f"  rejected_dead_end: {diag_rejected_dead_end}")
                print(f"  rejected_no_links: {diag_rejected_no_links}")
                # Print rejection reasons
                print(f"Rejected count: {len(rejected)}")
                for i, r in enumerate(rejected, 1):
                    print(f"REJ[{i}] reason={r.get('reason')} lat={r.get('lat'):.6f} lng={r.get('lng'):.6f} {r.get('error','')}")
                return

            # fallback random sampling (india and other modes)
            while seeded < target_remaining and attempts < target_remaining * 200:
                attempts += 1
                # Random sample; bias toward populated latitudes by using sine transform for latitude
                lat = random.uniform(lat_min, lat_max)
                lng = random.uniform(lon_min, lon_max)

                # Quick proximity check against already-seeded in-memory list
                too_close = False
                for (olat, olng) in seen:
                    if haversine_km(lat, lng, olat, olng) * 1000.0 < min_distance_m:
                        too_close = True
                        break
                if too_close:
                    continue

                # Check DB for nearby points using bounding box (approx)
                deg_delta = min_distance_m / 111320.0  # approx degrees for given meters
                from sqlalchemy import select
                stmt = select(Location).where(
                    func.lower(Location.mode) == mode,
                    Location.latitude.between(lat - deg_delta, lat + deg_delta),
                    Location.longitude.between(lng - deg_delta, lng + deg_delta)
                ).limit(5)
                res = await db.execute(stmt)
                nearby = res.scalars().all()
                if nearby:
                    # check real distance
                    close = False
                    for n in nearby:
                        if haversine_km(lat, lng, n.latitude, n.longitude) * 1000.0 < min_distance_m:
                            close = True
                            break
                    if close:
                        continue

                # Check Street View panorama availability and metadata
                panomet = await check_panorama_meta(http, lat, lng, api_key)
                if not panomet:
                    # no panorama nearby
                    await asyncio.sleep(sleep_s)
                    continue

                # Reject zero-link panoramas
                if panomet.get('links_count', 0) == 0:
                    diag_rejected_no_links += 1
                    await asyncio.sleep(sleep_s)
                    continue
                # Reject one-link / dead-end panoramas
                if panomet.get('links_count', 0) <= 1:
                    diag_rejected_dead_end += 1
                    await asyncio.sleep(sleep_s)
                    continue

                # Reject non-official photo spheres
                copyright = (panomet.get('copyright') or '').lower()
                pano_id = panomet.get('pano') or ''
                is_official = False
                if 'google' in copyright:
                    is_official = True
                if pano_id and pano_id.startswith('CAoS'):
                    is_official = True
                if not is_official:
                    diag_rejected_photo_sphere += 1
                    await asyncio.sleep(sleep_s)
                    continue

                # Reverse geocode for metadata (use shared geocode helper)
                country, state, city, meta = await reverse_geocode(lat, lng)

                # India-mode validations
                if mode == 'india':
                    if not country or 'india' not in country.lower():
                        # reject non-India countries
                        continue
                    # ensure inside approximate India polygon too
                    if not point_in_india(lat, lng):
                        # if reverse geocode says India but polygon says outside, log and reject
                        print(f"Rejected point outside India polygon lat={lat} lng={lng} country_rev={country}")
                        continue

                # Indoor/business heuristics using reverse geocode meta
                prov = meta.get('provider')
                indoor_reject = False
                if prov == 'google':
                    raw = meta.get('raw') or {}
                    types = [t.lower() for t in (meta.get('types') or [])]
                    formatted = (raw.get('formatted_address') or '').lower() if isinstance(raw, dict) else ''
                    business_keywords = ['hotel', 'restaurant', 'museum', 'temple', 'inn', 'cafe', 'bar', 'mall', 'shop', 'clinic', 'hospital']
                    if any(k in formatted for k in business_keywords) and 'route' not in types:
                        indoor_reject = True
                elif prov == 'nominatim':
                    raw = meta.get('raw') or {}
                    addr = (raw.get('address') or {}) if isinstance(raw, dict) else {}
                    amen = (addr.get('amenity') or '').lower()
                    if amen in ('restaurant', 'cafe', 'hotel', 'museum', 'place_of_worship', 'library'):
                        indoor_reject = True

                if indoor_reject:
                    diag_rejected_indoor += 1
                    await asyncio.sleep(sleep_s)
                    continue

                # classify category from meta (conservative default)
                cat = classify_category_from_meta(meta, city, default='unknown')

                # Insert into DB
                added = await commit_location(lat, lng, panomet.get('pano'), country, state, city, meta)
                if added:
                    diag_accepted_official += 1
                    await asyncio.sleep(sleep_s)

                # be polite to APIs
                await asyncio.sleep(sleep_s)

            print(f"Seeding finished. Seeded {seeded} new locations (attempts={attempts}).")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["india", "world"], default="india")
    p.add_argument("--target", type=int, default=200, help="Total desired verified locations (per mode)")
    p.add_argument("--min-distance", type=int, default=100, help="Minimum distance (meters) between stored locations")
    p.add_argument("--apikey", type=str, default=None, help="Google Maps API key (optional; recommended) ")
    p.add_argument("--sleep", type=float, default=0.2, help="Delay between external API calls (seconds)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    api_key = args.apikey
    if not api_key:
        # Try environment variable
        import os
        api_key = os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("VITE_GOOGLE_MAPS_API_KEY") or getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
    try:
        asyncio.run(seed(args.mode, args.target, api_key, args.min_distance, args.sleep))
    except Exception as e:
        import traceback
        print("Seeder failed:")
        traceback.print_exc()
        raise
