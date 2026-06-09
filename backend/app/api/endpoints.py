from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.api.deps import get_db
from app.schemas.game import (
    GameCreate,
    GameSessionResponse,
    GuessSubmit,
    RoundGuessResponse,
    GameResultsResponse,
    RoundResult
)
from app.services.game_service import GameService
from app.models.location import Location

router = APIRouter()


@router.get('/admin/locations/diagnostics')
async def locations_diagnostics(db: AsyncSession = Depends(get_db)):
    """Return counts and sample locations for India and World modes."""
    # total counts
    total_india = (await db.execute(select(func.count()).select_from(Location).where(func.lower(Location.mode) == 'india'))).scalar_one()
    total_world = (await db.execute(select(func.count()).select_from(Location).where(func.lower(Location.mode) == 'world'))).scalar_one()
    verified_india = (await db.execute(select(func.count()).select_from(Location).where(func.lower(Location.mode) == 'india', Location.verified == True))).scalar_one()
    verified_world = (await db.execute(select(func.count()).select_from(Location).where(func.lower(Location.mode) == 'world', Location.verified == True))).scalar_one()

    # category breakdown for India
    rows_india = (await db.execute(select(Location.category, func.count()).where(func.lower(Location.mode) == 'india').group_by(Location.category))).all()
    cat_india = {r[0] or 'unknown': r[1] for r in rows_india}

    rows_world = (await db.execute(select(Location.category, func.count()).where(func.lower(Location.mode) == 'world').group_by(Location.category))).all()
    cat_world = {r[0] or 'unknown': r[1] for r in rows_world}

    # sample locations
    samp_india = (await db.execute(select(Location).where(func.lower(Location.mode) == 'india').limit(10))).scalars().all()
    samp_world = (await db.execute(select(Location).where(func.lower(Location.mode) == 'world').limit(10))).scalars().all()

    def loc_to_dict(l: Location):
        return {
            'id': getattr(l, 'id', None),
            'lat': l.latitude,
            'lng': l.longitude,
            'country': l.country,
            'state': l.state,
            'city': l.city,
            'category': l.category,
            'panorama_id': l.panorama_id,
            'verified': bool(l.verified)
        }

    return {
        'total': {'india': total_india, 'world': total_world},
        'verified': {'india': verified_india, 'world': verified_world},
        'by_category': {'india': cat_india, 'world': cat_world},
        'samples': {'india': [loc_to_dict(l) for l in samp_india], 'world': [loc_to_dict(l) for l in samp_world]}
    }

@router.post("/games", response_model=GameSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_game(payload: GameCreate, db: AsyncSession = Depends(get_db)):
    """
    Start a new game session of 5 rounds in the specified mode ('india' or 'world').
    """
    if payload.mode.lower() not in ["india", "world"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid game mode. Must be 'india' or 'world'."
        )
    
    game_session, first_round = await GameService.create_game(db, payload.mode)
    
    return GameSessionResponse(
        game_id=game_session.id,
        mode=game_session.mode,
        current_round=first_round.round_number,
        streetview_lat=first_round.location.latitude,
        streetview_lng=first_round.location.longitude,
        panorama_id=first_round.location.panorama_id,
    )

@router.post("/games/{game_id}/guess", response_model=RoundGuessResponse)
async def submit_guess(game_id: str, payload: GuessSubmit, db: AsyncSession = Depends(get_db)):
    """
    Submit coordinates representing the user's guess for the current active round.
    Computes distance, score, and updates database records.
    """
    completed_round, is_game_completed = await GameService.submit_guess(
        db, game_id, payload.latitude, payload.longitude
    )
    
    return RoundGuessResponse(
        round_number=completed_round.round_number,
        guessed_lat=completed_round.guessed_latitude,
        guessed_lng=completed_round.guessed_longitude,
        actual_lat=completed_round.location.latitude,
        actual_lng=completed_round.location.longitude,
        distance_km=completed_round.distance_km,
        score=completed_round.score,
        is_game_completed=is_game_completed
    )

@router.post("/games/{game_id}/next", response_model=GameSessionResponse)
async def next_round(game_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve the next round for the specified game session.
    """
    next_round_obj, mode = await GameService.get_next_round(db, game_id)
    
    return GameSessionResponse(
        game_id=game_id,
        mode=mode,
        current_round=next_round_obj.round_number,
        streetview_lat=next_round_obj.location.latitude,
        streetview_lng=next_round_obj.location.longitude,
        panorama_id=next_round_obj.location.panorama_id,
    )

@router.post("/games/{game_id}/round/location", response_model=GameSessionResponse)
async def update_round_location(
    game_id: str, payload: GuessSubmit, db: AsyncSession = Depends(get_db)
):
    """
    Update the active round's actual coordinates if the frontend finds a valid nearby panorama replacement.
    """
    updated_round = await GameService.update_active_round_location(
        db, game_id, payload.latitude, payload.longitude
    )
    return GameSessionResponse(
        game_id=game_id,
        mode=updated_round.game_session.mode,
        current_round=updated_round.round_number,
        streetview_lat=updated_round.location.latitude,
        streetview_lng=updated_round.location.longitude,
        panorama_id=updated_round.location.panorama_id,
    )

@router.get("/games/{game_id}/results", response_model=GameResultsResponse)
async def get_results(game_id: str, db: AsyncSession = Depends(get_db)):
    """
    Fetch the final game session summary and round breakdown.
    """
    game_session = await GameService.get_game_results(db, game_id)
    
    rounds_data = []
    total_distance = 0.0
    completed_count = 0
    
    for r in game_session.rounds:
        rounds_data.append(
            RoundResult(
                round_number=r.round_number,
                guessed_lat=r.guessed_latitude,
                guessed_lng=r.guessed_longitude,
                actual_lat=r.location.latitude,
                actual_lng=r.location.longitude,
                distance_km=r.distance_km,
                score=r.score
            )
        )
        if r.distance_km is not None:
            total_distance += r.distance_km
            completed_count += 1
            
    avg_distance = total_distance / completed_count if completed_count > 0 else 0.0
    
    return GameResultsResponse(
        game_id=game_session.id,
        mode=game_session.mode,
        total_score=game_session.total_score,
        average_distance_km=avg_distance,
        rounds=rounds_data
    )
