import math
import uuid
import random
from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload, selectinload
from fastapi import HTTPException, status
import logging
import httpx

from app.core.config import settings
from app.models.location import Location
from app.models.game import GameSession, Round

logger = logging.getLogger(__name__)


# Helper: call Google Street View Metadata API to verify panorama availability
async def _verify_panorama_api(lat: float, lng: float) -> Optional[str]:
    api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
    if not api_key:
        return None
    url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={lat},{lng}&key={api_key}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return None
            data = r.json()
            if data.get('status') == 'OK':
                # pano may appear under several keys
                pano = data.get('pano_id') or data.get('panoId') or (data.get('location') or {}).get('pano')
                return pano
    except Exception as e:
        logger.debug("_verify_panorama_api: request failed %s", e)
    return None


# Helper: reverse geocode to get country/state/city (Google first, Nominatim fallback)
async def _reverse_geocode(lat: float, lng: float) -> Tuple[str, Optional[str], Optional[str]]:
    api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
    if api_key:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={api_key}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(url)
                if r.status_code == 200:
                    data = r.json()
                    results = data.get('results', [])
                    if results:
                        comp = results[0].get('address_components', [])
                        country = None
                        state = None
                        city = None
                        for c in comp:
                            types = c.get('types', [])
                            if 'country' in types:
                                country = c.get('long_name')
                            if 'administrative_area_level_1' in types:
                                state = c.get('long_name')
                            if 'locality' in types or 'postal_town' in types:
                                city = c.get('long_name')
                        return country or '', state, city
        except Exception as e:
            logger.debug("_reverse_geocode: google request failed %s", e)

    # Fallback to Nominatim
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lng}"
        headers = {'User-Agent': 'IndiaGuessrServer/1.0 (seed@example.com)'}
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                data = r.json()
                address = data.get('address', {})
                country = address.get('country')
                state = address.get('state') or address.get('region')
                city = address.get('city') or address.get('town') or address.get('village')
                return country or '', state, city
    except Exception as e:
        logger.debug("_reverse_geocode: nominatim request failed %s", e)

    return '', None, None

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on the Earth's surface
    using the Haversine formula. Returns distance in kilometers.
    """
    # Earth radius in kilometers
    R = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_score(distance_km: float, mode: str) -> int:
    """
    Calculate the score based on distance and game mode using exponential decay.
    Max score per round is 5000.
    """
    MAX_SCORE = 5000
    
    # Scale parameter k based on mode
    # India Mode (smaller scale, higher precision needed): k = 200
    # World Mode (larger scale): k = 2000
    if mode.lower() == "india":
        k = 200.0
    else:
        k = 2000.0
        
    score = MAX_SCORE * math.exp(-distance_km / k)
    
    # Round to nearest integer and clamp between 0 and 5000
    return max(0, min(MAX_SCORE, round(score)))


def _country_to_continent(country: str) -> str:
    """Very small heuristic mapping from common country names to continents.
    Falls back to 'Other' when unknown. This is intentionally lightweight to avoid
    large external dependencies; it's only used to prefer geographic diversity.
    """
    if not country:
        return 'Other'
    c = country.strip().lower()
    na = {'united states','usa','us','canada','mexico'}
    sa = {'brazil','argentina','chile','colombia','peru','venezuela'}
    eu = {'united kingdom','uk','france','germany','italy','spain','netherlands','poland','russia','sweden'}
    asia = {'china','japan','india','pakistan','bangladesh','south korea','korea','israel','singapore'}
    af = {'egypt','south africa','nigeria','kenya','morocco'}
    oc = {'australia','new zealand'}
    cn = c
    if any(x in cn for x in na):
        return 'North America'
    if any(x in cn for x in sa):
        return 'South America'
    if any(x in cn for x in eu):
        return 'Europe'
    if any(x in cn for x in asia):
        return 'Asia'
    if any(x in cn for x in af):
        return 'Africa'
    if any(x in cn for x in oc):
        return 'Oceania'
    return 'Other'


class GameService:
    @staticmethod
    async def create_game(db: AsyncSession, mode: str) -> Tuple[GameSession, Round]:
        """
        Create a new game session. Queries 5 random locations for the given mode,
        creates 5 rounds, and returns the session along with the first round details.
        """
        logger.debug("create_game: start - mode=%s", mode)
        try:
            # 1. Fetch candidate verified locations for the specified mode
            logger.debug("create_game: building select statement for verified locations")
            # Fetch a larger candidate pool and deduplicate in Python to ensure unique panoramas
            candidate_limit = 500
            # match mode case-insensitively in DB to avoid mismatches
            stmt = (
                select(Location)
                .where(func.lower(Location.mode) == mode.lower(), Location.verified == True)
                .order_by(func.random())
                .limit(candidate_limit)
            )
            logger.debug("create_game: executing select statement for candidates (limit=%d)", candidate_limit)
            result = await db.execute(stmt)
            candidates = result.scalars().all()
            logger.debug("create_game: fetched %d candidate locations from DB", len(candidates))

            # If we couldn't fetch any verified locations, try to opportunistically verify unverified candidates (world mode)
            if len(candidates) == 0:
                # For world mode, attempt to verify a small batch of unverified locations
                if mode.lower() == 'world':
                    logger.warning("create_game: no verified locations found initially for 'world'; attempting opportunistic verification of unverified candidates")
                    unv_stmt = (
                        select(Location)
                        .where(func.lower(Location.mode) == mode.lower(), Location.verified == False)
                        .order_by(func.random())
                        .limit(200)
                    )
                    res_unv = await db.execute(unv_stmt)
                    unverified_candidates = res_unv.scalars().all()
                    verified_added = 0
                    for loc in unverified_candidates:
                        pano = await _verify_panorama_api(loc.latitude, loc.longitude)
                        if pano:
                            loc.panorama_id = pano or loc.panorama_id
                            loc.verified = True
                            from datetime import datetime
                            loc.last_verified_at = datetime.utcnow()
                            db.add(loc)
                            try:
                                await db.commit()
                                verified_added += 1
                                candidates.append(loc)
                            except Exception:
                                await db.rollback()
                        if len(candidates) >= 20:
                            break

                    logger.info("create_game: opportunistic verification added %d candidates", verified_added)

            if len(candidates) == 0:
                # report how many verified entries actually exist for this mode
                cnt_stmt = select(func.count()).select_from(Location).where(func.lower(Location.mode) == mode.lower(), Location.verified == True)
                cnt = (await db.execute(cnt_stmt)).scalar_one()
                logger.error("create_game: no verified locations found for mode=%s (count=%d)", mode, cnt)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(f"Not enough verified locations available for mode '{mode}'. Found {cnt} verified locations. "
                            "Run the seeding script (scripts/seed_verified_locations.py) to populate more verified locations.")
                )

            # Helper: canonicalize category strings into our set
            def canonical_category(raw: Optional[str]) -> str:
                if not raw:
                    return 'urban'
                r = raw.lower()
                if any(x in r for x in ['motorway', 'trunk', 'highway', 'road']):
                    return 'highway'
                if any(x in r for x in ['tourism', 'attraction', 'viewpoint', 'landmark', 'museum']):
                    return 'landmark'
                if any(x in r for x in ['village', 'hamlet', 'rural']):
                    return 'rural'
                if any(x in r for x in ['suburb', 'residential', 'neighbourhood']):
                    return 'suburban'
                # default heuristics
                if any(x in r for x in ['city', 'town', 'urban', 'municipality']):
                    return 'urban'
                return 'urban'

            # Bucket candidates by category and enforce India-country when needed
            buckets: dict[str, list[Location]] = { 'urban': [], 'suburban': [], 'rural': [], 'highway': [], 'landmark': [] }
            for loc in candidates:
                if mode.lower() == 'india':
                    country = (loc.country or '').lower()
                    if 'india' not in country:
                        continue
                cat = canonical_category(getattr(loc, 'category', None))
                if cat not in buckets:
                    cat = 'urban'
                buckets[cat].append(loc)

            logger.debug("create_game: candidate buckets sizes: %s", {k: len(v) for k,v in buckets.items()})

            # Pre-define category slots for 5 rounds to meet exact distribution requirements
            if mode.lower() == 'india':
                # Enforce exactly the targeted ratio: 50% Urban (2 or 3 rounds), 20% Suburban (1 round), 20% Rural (1 round), 5% Highway / 5% Landmark (1 round combined).
                slots = ['urban', 'urban', 'suburban']
                # Decide if we want a 3rd urban round or rural/highway/landmark
                if random.random() < 0.5:
                    slots.append('urban')
                    slots.append(random.choices(['rural', 'highway', 'landmark'], weights=[0.60, 0.20, 0.20], k=1)[0])
                else:
                    slots.append('rural')
                    slots.append(random.choices(['highway', 'landmark'], weights=[0.50, 0.50], k=1)[0])
            else:
                slots = ['urban', 'urban', 'suburban', 'rural', random.choice(['highway', 'landmark'])]

            random.shuffle(slots)
            logger.debug("create_game: selected category slots: %s", slots)

            # Build a curated urban pool of major Indian cities to prioritize
            curated_cities = [
                'mumbai','pune','delhi','new delhi','bengaluru','bangalore','chennai','hyderabad','ahmedabad',
                'kolkata','jaipur','chandigarh','kochi','surat','indore','lucknow'
            ]
            curated_lower = [c.lower() for c in curated_cities]
            
            # Helper to check if a location is in the prioritized cities
            def is_in_prioritized_city(loc: Location) -> bool:
                city_name = (loc.city or '').lower()
                state_name = (loc.state or '').lower()
                return any(name in city_name or name in state_name for name in curated_lower)

            selected: list[Location] = []
            seen_panos = set()
            seen_coords = set()
            chosen_countries = set()
            chosen_continents = set()
            chosen_states = set()
            india_selected = 0

            # Select a location for each slot
            for slot_cat in slots:
                # Find candidates for this category
                pool = buckets.get(slot_cat, [])
                if not pool:
                    # Fallback to any category that has candidates
                    for fallback_cat in ['urban', 'suburban', 'rural', 'landmark', 'highway']:
                        if buckets.get(fallback_cat):
                            pool = buckets[fallback_cat]
                            break
                if not pool:
                    continue

                # Filter pool to prioritize target cities for urban/suburban in India mode
                preferred_pool = pool
                if mode.lower() == 'india' and slot_cat in ('urban', 'suburban'):
                    priority_candidates = [l for l in pool if is_in_prioritized_city(l)]
                    if priority_candidates and random.random() < 0.90:  # 90% preference
                        preferred_pool = priority_candidates

                # In World mode, prefer geographic diversity (different countries and continents)
                def get_best_candidate(candidates_list):
                    random.shuffle(candidates_list)
                    for c in candidates_list:
                        # Dedupe check
                        p_id = getattr(c, 'panorama_id', None)
                        c_key = (round(c.latitude, 4), round(c.longitude, 4))
                        if p_id and p_id in seen_panos:
                            continue
                        if c_key in seen_coords:
                            continue
                        
                        if mode.lower() == 'world':
                            country_name = (c.country or '').strip().lower()
                            # limit India occurrences to 1 per 5-round world game
                            if 'india' in country_name and india_selected >= 1:
                                continue
                            if country_name and country_name in chosen_countries:
                                continue
                        return c
                    # Fallback to first non-duplicate in the randomized list
                    for c in candidates_list:
                        p_id = getattr(c, 'panorama_id', None)
                        c_key = (round(c.latitude, 4), round(c.longitude, 4))
                        if (not p_id or p_id not in seen_panos) and c_key not in seen_coords:
                            return c
                    return candidates_list[0] if candidates_list else None

                loc = get_best_candidate(preferred_pool)
                if not loc:
                    continue

                # Record selected location
                selected.append(loc)
                p_id = getattr(loc, 'panorama_id', None)
                if p_id:
                    seen_panos.add(p_id)
                seen_coords.add((round(loc.latitude, 4), round(loc.longitude, 4)))

                if mode.lower() == 'world':
                    country_name = (loc.country or '').strip().lower()
                    if country_name:
                        chosen_countries.add(country_name)
                        if 'india' in country_name:
                            india_selected += 1
                        chosen_continents.add(_country_to_continent(loc.country))
                    state_name = (loc.state or '').strip().lower()
                    if state_name:
                        chosen_states.add(state_name)

            # If still short of 5, fill from any remaining candidates
            if len(selected) < 5:
                for loc in candidates:
                    if len(selected) >= 5:
                        break
                    p_id = getattr(loc, 'panorama_id', None)
                    c_key = (round(loc.latitude, 4), round(loc.longitude, 4))
                    if p_id and p_id in seen_panos:
                        continue
                    if c_key in seen_coords:
                        continue
                    selected.append(loc)
                    if p_id:
                        seen_panos.add(p_id)
                    seen_coords.add(c_key)

            locations = selected


            if len(locations) < 5:
                cnt_stmt = select(func.count()).select_from(Location).where(func.lower(Location.mode) == mode.lower(), Location.verified == True)
                cnt = (await db.execute(cnt_stmt)).scalar_one()
                logger.error("create_game: insufficient verified locations for mode=%s after selection (found=%d) total_verified=%d", mode, len(locations), cnt)
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(f"Not enough verified locations available for mode '{mode}'. Selected {len(locations)} locations from {cnt} verified entries. "
                            "Run the seeding script (scripts/seed_verified_locations.py) to populate more verified locations.")
                )

            # 2. Create the GameSession
            logger.debug("create_game: creating GameSession object")
            game_session = GameSession(
                id=str(uuid.uuid4()),
                mode=mode.lower(),
                status="active",
                total_score=0
            )
            db.add(game_session)

            # 3. Create the 5 Rounds
            rounds = []
            for i, loc in enumerate(locations, start=1):
                logger.debug("create_game: creating Round %d for location id=%s", i, getattr(loc, 'id', None))
                round_obj = Round(
                    id=str(uuid.uuid4()),
                    game_session_id=game_session.id,
                    round_number=i,
                    location_id=loc.id,
                    status="active"
                )
                db.add(round_obj)
                rounds.append(round_obj)

            logger.debug("create_game: committing session with %d rounds", len(rounds))
            await db.commit()
            logger.debug("create_game: commit complete, refreshing game_session")
            await db.refresh(game_session)

            # Eagerly load the first round with its Location to avoid async lazy-loading
            logger.debug("create_game: querying first round with joinedload(location) for game_session id=%s", game_session.id)
            stmt_fr = (
                select(Round)
                .options(joinedload(Round.location))
                .where(Round.game_session_id == game_session.id)
                .order_by(Round.round_number)
                .limit(1)
            )
            result_fr = await db.execute(stmt_fr)
            first_round = result_fr.scalar_one_or_none()
            if not first_round:
                logger.error("create_game: could not fetch first round after commit for game_session id=%s", game_session.id)
                raise Exception("Failed to fetch first round after commit")

            logger.debug("create_game: successfully created game_session id=%s and first_round id=%s (location id=%s)", game_session.id, getattr(first_round, 'id', None), getattr(first_round.location, 'id', None))
            return game_session, first_round
        except Exception:
            logger.exception("create_game: unexpected exception (mode=%s)", mode)
            raise

    @staticmethod
    async def submit_guess(
        db: AsyncSession, game_id: str, lat: float, lng: float
    ) -> Tuple[Round, bool]:
        """
        Submit a guess for the current active round. Calculates distance and score,
        updates the round stats, updates the session overall score if it was the last round,
        and returns the completed round details and whether the game is fully completed.
        """
        # Fetch the game session with its rounds and locations eagerly loaded
        stmt = select(GameSession).options(selectinload(GameSession.rounds).selectinload(Round.location)).where(GameSession.id == game_id)
        result = await db.execute(stmt)
        game_session = result.scalar_one_or_none()

        if not game_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game session with ID '{game_id}' not found."
            )

        if game_session.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This game has already been completed."
            )

        # Find the active round (first round that hasn't been guessed yet)
        active_round = None
        for r in game_session.rounds:
            if r.guessed_latitude is None:
                active_round = r
                break

        if not active_round:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active rounds left in this session. Fetch results instead."
            )

        # Calculate distance and score
        actual_lat = active_round.location.latitude
        actual_lng = active_round.location.longitude
        
        distance_km = calculate_haversine_distance(actual_lat, actual_lng, lat, lng)
        score = calculate_score(distance_km, game_session.mode)

        # Update round fields
        active_round.guessed_latitude = lat
        active_round.guessed_longitude = lng
        active_round.distance_km = distance_km
        active_round.score = score
        active_round.status = "completed"

        # Check if this was the final round (round number 5)
        is_game_completed = active_round.round_number == 5

        if is_game_completed:
            # Aggregate score and close game session
            game_session.total_score = sum(r.score for r in game_session.rounds)
            game_session.status = "completed"

        await db.commit()
        await db.refresh(active_round)

        return active_round, is_game_completed

    @staticmethod
    async def get_next_round(db: AsyncSession, game_id: str) -> Tuple[Round, str]:
        """
        Retrieve the next active (unguessed) round for a game session.
        """
        stmt = select(GameSession).options(selectinload(GameSession.rounds).selectinload(Round.location)).where(GameSession.id == game_id)
        result = await db.execute(stmt)
        game_session = result.scalar_one_or_none()

        if not game_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game session with ID '{game_id}' not found."
            )

        if game_session.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Game is already completed. No more rounds to load."
            )

        # Find first round where guessed_latitude is None
        next_round = None
        for r in game_session.rounds:
            if r.guessed_latitude is None:
                next_round = r
                break

        if not next_round:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All rounds have been guessed already."
            )

        return next_round, game_session.mode

    @staticmethod
    async def get_game_results(db: AsyncSession, game_id: str) -> GameSession:
        """
        Get the summary results for a completed game session.
        """
        stmt = select(GameSession).options(selectinload(GameSession.rounds).selectinload(Round.location)).where(GameSession.id == game_id)
        result = await db.execute(stmt)
        game_session = result.scalar_one_or_none()

        if not game_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game session with ID '{game_id}' not found."
            )

        return game_session

    @staticmethod
    async def update_active_round_location(
        db: AsyncSession, game_id: str, lat: float, lng: float
    ) -> Round:
        """
        Update the current active round's actual coordinates when the frontend
        automatically replacement-searches and finds a valid nearby panorama.
        Creates a new Location if it doesn't exist to prevent modifying shared records.
        """
        from datetime import datetime
        # Fetch the game session with its rounds and locations
        stmt = select(GameSession).options(selectinload(GameSession.rounds).selectinload(Round.location)).where(GameSession.id == game_id)
        result = await db.execute(stmt)
        game_session = result.scalar_one_or_none()

        if not game_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game session with ID '{game_id}' not found."
            )

        # Find the active round (first round that hasn't been guessed yet)
        active_round = None
        for r in game_session.rounds:
            if r.guessed_latitude is None:
                active_round = r
                break

        if not active_round:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active rounds left in this session to update location."
            )

        # Check if a location with these exact coordinates already exists
        loc_stmt = select(Location).where(
            func.abs(Location.latitude - lat) < 1e-6,
            func.abs(Location.longitude - lng) < 1e-6,
            func.lower(Location.mode) == game_session.mode.lower()
        ).limit(1)
        loc_res = await db.execute(loc_stmt)
        existing_loc = loc_res.scalar_one_or_none()

        if existing_loc:
            active_round.location_id = existing_loc.id
        else:
            # Create a new verified Location entry to preserve uniqueness
            # Use reverse geocode to fill in details if possible
            country, state, city = '', None, None
            try:
                from app.services.game_service import _reverse_geocode
                country, state, city = await _reverse_geocode(lat, lng)
            except Exception:
                pass
            
            new_loc = Location(
                latitude=lat,
                longitude=lng,
                country=country or (active_round.location.country if active_round.location else ""),
                state=state or (active_round.location.state if active_round.location else None),
                city=city or (active_round.location.city if active_round.location else None),
                mode=game_session.mode.lower(),
                category=active_round.location.category if active_round.location else "urban",
                verified=True,
                last_verified_at=datetime.utcnow()
            )
            db.add(new_loc)
            await db.flush() # get new ID
            active_round.location_id = new_loc.id

        await db.commit()

        stmt = (
            select(Round)
            .options(joinedload(Round.location), joinedload(Round.game_session))
            .where(Round.id == active_round.id)
        )
        result = await db.execute(stmt)
        refreshed_round = result.scalar_one()
        return refreshed_round

