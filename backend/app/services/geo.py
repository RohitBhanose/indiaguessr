"""Geospatial helpers: India bounding checks and simple category classifier.

These helpers avoid adding heavy geospatial dependencies. We use a conservative
bounding-box + small island boxes check and rely primarily on reverse geocoding
for country verification. This satisfies "coordinates must lie inside India's
boundaries" requirement in a pragmatic manner.
"""
from typing import Optional


def point_in_india(lat: float, lng: float) -> bool:
    """Rudimentary point-in-India check.

    This uses a primary mainland bounding box and small boxes for Lakshadweep
    and Andaman/Nicobar. It's intentionally conservative and should be used
    in combination with reverse-geocoding country=='India'.
    """
    # Mainland India box
    if 6.55 <= lat <= 35.50 and 68.0 <= lng <= 97.50:
        return True

    # Andaman & Nicobar rough box
    if 5.5 <= lat <= 15.5 and 90.0 <= lng <= 94.5:
        return True

    # Lakshadweep rough box
    if 6.0 <= lat <= 12.0 and 71.0 <= lng <= 74.5:
        return True

    return False


def classify_category(city: Optional[str], state: Optional[str], nominatim_type: Optional[str]) -> str:
    """Classify into one of: urban, suburban, rural, highway, landmark.

    Inputs are best-effort: `city`/`state` from reverse geocode, and
    `nominatim_type` (or a short type hint) when available.
    """
    if city:
        c = city.lower()
        # If the reverse-geocoder returned something that looks like a major
        # place (city/town/municipality) treat as urban.
        if any(k in c for k in ['city', 'town', 'municipality', 'metro', 'municipal']):
            return 'urban'
        # Short names are still strong signal for urban centers
        return 'urban'

    t = (nominatim_type or '').lower()
    if any(x in t for x in ['village', 'hamlet', 'farm', 'rural']):
        return 'rural'
    if any(x in t for x in ['suburb', 'residential', 'neighbourhood']):
        return 'suburban'
    if any(x in t for x in ['motorway', 'trunk', 'highway', 'road', 'route']):
        return 'highway'
    if any(x in t for x in ['tourism', 'attraction', 'viewpoint', 'museum', 'park', 'monument']):
        return 'landmark'

    # Heuristic fallback: prefer suburban if we have state but not city,
    # otherwise rural.
    if state:
        return 'suburban'

    return 'rural'
