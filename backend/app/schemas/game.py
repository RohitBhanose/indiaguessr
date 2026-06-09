from pydantic import BaseModel, Field
from typing import List, Optional

class GameCreate(BaseModel):
    mode: str = Field(..., description="Game mode: 'india' or 'world'")

class GameSessionResponse(BaseModel):
    game_id: str
    mode: str
    current_round: int
    streetview_lat: float
    streetview_lng: float
    panorama_id: Optional[str] = None

class GuessSubmit(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)

class RoundGuessResponse(BaseModel):
    round_number: int
    guessed_lat: float
    guessed_lng: float
    actual_lat: float
    actual_lng: float
    distance_km: float
    score: int
    is_game_completed: bool

class RoundResult(BaseModel):
    round_number: int
    guessed_lat: Optional[float] = None
    guessed_lng: Optional[float] = None
    actual_lat: float
    actual_lng: float
    distance_km: Optional[float] = None
    score: Optional[int] = None

class GameResultsResponse(BaseModel):
    game_id: str
    mode: str
    total_score: int
    average_distance_km: float
    rounds: List[RoundResult]
