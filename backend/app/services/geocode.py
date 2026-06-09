import asyncio
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import settings


async def _google_reverse_geocode(lat: float, lng: float) -> Optional[Dict[str, Any]]:
    key = settings.GOOGLE_MAPS_API_KEY
    if not key:
        return None
    url = (
        "https://maps.googleapis.com/maps/api/geocode/json"
        f"?latlng={lat},{lng}&key={key}"
    )
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data.get("results"):
            return None
        return data


async def _nominatim_reverse_geocode(lat: float, lng: float) -> Optional[Dict[str, Any]]:
    url = (
        "https://nominatim.openstreetmap.org/reverse"
        f"?format=jsonv2&lat={lat}&lon={lng}&zoom=18&addressdetails=1"
    )
    headers = {"User-Agent": "indiaguessr/1.0 (research)"}
    async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return None
        return r.json()


async def reverse_geocode(lat: float, lng: float) -> Tuple[Optional[str], Optional[str], Optional[str], Dict[str, Any]]:
    """Return (country, state, city, meta) for the given lat/lng.

    Meta is a dict with provider-specific fields and raw payload under `raw`.
    """
    # Try Google first when API key present
    has_google_key = bool(settings.GOOGLE_MAPS_API_KEY)
    try:
        if has_google_key:
            gd = await _google_reverse_geocode(lat, lng)
            if gd and gd.get("results"):
                primary = gd["results"][0]
                types = primary.get("types", [])
                # extract address components
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
        # swallow and fallback (only if no Google key)
        pass

    if has_google_key:
        # If we have a Google key and it failed or returned nothing, do not fallback to Nominatim
        # as it is highly restricted and causes huge timeouts.
        return None, None, None, {}

    # Nominatim fallback
    try:
        nd = await _nominatim_reverse_geocode(lat, lng)
        if nd:
            addr = nd.get("address", {}) or {}
            country = addr.get("country")
            state = addr.get("state")
            city = addr.get("city") or addr.get("town") or addr.get("village")
            meta = {"provider": "nominatim", "type": nd.get("type"), "address": addr, "raw": nd}
            return country, state, city, meta
    except Exception:
        pass

    return None, None, None, {}


def classify_category_from_meta(meta: Optional[Dict[str, Any]], city_hint: Optional[str] = None, default: str = "unknown") -> str:
    """Heuristic classifier that returns one of: urban, suburban, rural, highway, landmark.

    Uses provider-specific meta produced by reverse_geocode.
    """
    if not meta:
        return default

    provider = meta.get("provider")

    # Known large city hints to bias classification
    large_cities = {
        'mumbai','pune','delhi','new delhi','bangalore','bengaluru','chennai','hyderabad','ahmedabad',
        'kolkata','jaipur','chandigarh','kochi','surat','indore','lucknow','bengaluru','bangalore'
    }

    # Helper to normalize strings
    def _norm(s: Optional[str]) -> str:
        return (s or '').strip().lower()

    # Nominatim provider often includes extratags with population
    if provider == "nominatim":
        t = (meta.get("type") or "").lower()
        addr = meta.get("address", {}) or {}
        raw = meta.get("raw") or {}
        extratags = (raw.get('extratags') or {}) if isinstance(raw, dict) else {}

        # population heuristics when available
        pop = None
        pop_val = extratags.get('population') or addr.get('population') or extratags.get('population:2001')
        if pop_val:
            try:
                pop = int(str(pop_val).replace(',', '').split('.')[0])
            except Exception:
                pop = None
        if pop is not None:
            if pop >= 300000:
                return 'urban'
            if pop >= 50000:
                return 'suburban'
            return 'rural'

        # Type-based heuristics
        if t in ("city", "town"):
            return 'urban'
        if t in ("village", "hamlet"):
            return 'rural'
        if t in ("residential", "road", "street"):
            return 'urban'
        if t in ("highway",):
            return 'highway'
        if t in ("attraction", "tourism"):
            return 'landmark'
        if addr.get('suburb') or addr.get('neighbourhood'):
            return 'suburban'
        if city_hint and _norm(city_hint) in large_cities:
            return 'urban'
        return default

    # Google provider: use address components, types, and formatted address
    if provider == "google":
        types: List[str] = [t.lower() for t in meta.get("types", [])]
        comps: Dict[str, str] = meta.get("components", {}) or {}
        raw: Dict[str, Any] = meta.get('raw') or {}
        formatted = _norm(raw.get('formatted_address') if isinstance(raw, dict) else '')

        # Landmark / POI signals
        if any(t in types for t in ("tourist_attraction", "point_of_interest", "establishment", "park", "natural_feature")):
            return 'landmark'

        # Highway/route signals
        if any('highway' in t or 'motorway' in t for t in types):
            return 'highway'
        if any(t in types for t in ('route',)) and not comps.get('locality'):
            # route without locality is likely a larger road/hwy
            return 'highway'

        # Neighborhood and sublocality -> suburban
        if comps.get('neighborhood') or comps.get('sublocality'):
            return 'suburban'

        # Explicit locality signals -> urban
        if comps.get('locality') or comps.get('postal_town') or comps.get('administrative_area_level_3'):
            return 'urban'

        # Business/indoor hints should be classified as landmark (but rejected during seeding)
        business_keywords = ['hotel', 'restaurant', 'museum', 'temple', 'inn', 'cafe', 'bar', 'mall', 'shop', 'clinic', 'hospital']
        if any(k in formatted for k in business_keywords):
            return 'landmark'

        # City hint or administrative area matches a known large city -> urban
        citynorm = _norm(city_hint or comps.get('locality') or comps.get('administrative_area_level_2'))
        if citynorm and any(name in citynorm for name in large_cities):
            return 'urban'

        # Fallback to weak signals
        if any(t in types for t in ('neighborhood', 'sublocality')):
            return 'suburban'
        if any(t in types for t in ('locality',)):
            return 'urban'

        if city_hint:
            return 'urban'

        return default

    # Unknown provider - use city hint when available
    if city_hint and _norm(city_hint) in large_cities:
        return 'urban'
    if city_hint:
        return 'urban'
    return default
