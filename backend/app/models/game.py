import uuid
from sqlalchemy import Column, String, Integer, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.models.base import Base

class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mode = Column(String(50), nullable=False)  # 'india' or 'world'
    status = Column(String(50), nullable=False, default="active")  # 'active' or 'completed'
    total_score = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationship to rounds with selectin loading to prevent lazy-load errors in async sessions
    rounds = relationship(
        "Round", 
        back_populates="game_session", 
        cascade="all, delete-orphan", 
        lazy="selectin",
        order_by="Round.round_number"
    )

    def __repr__(self) -> str:
        return f"<GameSession id={self.id} mode={self.mode} status={self.status} score={self.total_score}>"


class Round(Base):
    __tablename__ = "rounds"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    game_session_id = Column(String(36), ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False)
    round_number = Column(Integer, nullable=False)  # 1 to 5
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    guessed_latitude = Column(Float, nullable=True)
    guessed_longitude = Column(Float, nullable=True)
    distance_km = Column(Float, nullable=True)
    score = Column(Integer, nullable=True)
    status = Column(String(50), nullable=False, default="active")  # 'active' or 'completed'

    game_session = relationship("GameSession", back_populates="rounds")
    
    # Eagerly load location for easy retrieval of coordinates on round complete
    location = relationship("Location", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Round id={self.id} game_id={self.game_session_id} num={self.round_number} score={self.score}>"
