import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.models.base import Base
from app.models.location import Location

INDIA_LOCATIONS = [
    {"latitude": 27.1751, "longitude": 78.0421, "country": "India", "state": "Uttar Pradesh", "city": "Agra", "mode": "india", "category": "landmark"}, # Taj Mahal
    {"latitude": 18.9220, "longitude": 72.8347, "country": "India", "state": "Maharashtra", "city": "Mumbai", "mode": "india", "category": "landmark"}, # Gateway of India
    {"latitude": 28.5244, "longitude": 77.1855, "country": "India", "state": "Delhi", "city": "New Delhi", "mode": "india", "category": "landmark"}, # Qutub Minar
    {"latitude": 12.9756, "longitude": 77.6067, "country": "India", "state": "Karnataka", "city": "Bengaluru", "mode": "india", "category": "city"}, # MG Road
    {"latitude": 18.9415, "longitude": 72.8237, "country": "India", "state": "Maharashtra", "city": "Mumbai", "mode": "india", "category": "city"}, # Marine Drive
    {"latitude": 26.9124, "longitude": 75.8272, "country": "India", "state": "Rajasthan", "city": "Jaipur", "mode": "india", "category": "landmark"}, # Hawa Mahal
    {"latitude": 17.3616, "longitude": 78.4747, "country": "India", "state": "Telangana", "city": "Hyderabad", "mode": "india", "category": "landmark"}, # Charminar
    {"latitude": 31.6200, "longitude": 74.8765, "country": "India", "state": "Punjab", "city": "Amritsar", "mode": "india", "category": "landmark"}, # Golden Temple
    {"latitude": 22.5851, "longitude": 88.3468, "country": "India", "state": "West Bengal", "city": "Kolkata", "mode": "india", "category": "landmark"}, # Howrah Bridge
    {"latitude": 10.0889, "longitude": 77.0595, "country": "India", "state": "Kerala", "city": "Munnar", "mode": "india", "category": "village"}, # Munnar Tea Gardens
    {"latitude": 34.0268, "longitude": 78.3735, "country": "India", "state": "Ladakh", "city": "Pangong", "mode": "india", "category": "rural"}, # Pangong Tso
    {"latitude": 34.0150, "longitude": 74.8872, "country": "India", "state": "Jammu and Kashmir", "city": "Srinagar", "mode": "india", "category": "highway"}, # NH-44 Srinagar
    {"latitude": 19.8876, "longitude": 86.0945, "country": "India", "state": "Odisha", "city": "Konark", "mode": "india", "category": "landmark"}, # Konark Sun Temple
    {"latitude": 31.1044, "longitude": 77.1742, "country": "India", "state": "Himachal Pradesh", "city": "Shimla", "mode": "india", "category": "city"}, # Shimla Mall Road
    {"latitude": 24.8517, "longitude": 79.9213, "country": "India", "state": "Madhya Pradesh", "city": "Khajuraho", "mode": "india", "category": "landmark"}, # Khajuraho Temples
    {"latitude": 15.3350, "longitude": 76.4620, "country": "India", "state": "Karnataka", "city": "Hampi", "mode": "india", "category": "landmark"}, # Hampi Ruins
    {"latitude": 22.5448, "longitude": 88.3426, "country": "India", "state": "West Bengal", "city": "Kolkata", "mode": "india", "category": "landmark"}, # Victoria Memorial
    {"latitude": 15.5494, "longitude": 73.7536, "country": "India", "state": "Goa", "city": "Calangute", "mode": "india", "category": "city"}, # Calangute Beach Road
    {"latitude": 25.3076, "longitude": 83.0108, "country": "India", "state": "Uttar Pradesh", "city": "Varanasi", "mode": "india", "category": "landmark"}, # Varanasi Ghats
    {"latitude": 11.4082, "longitude": 76.6901, "country": "India", "state": "Tamil Nadu", "city": "Ooty", "mode": "india", "category": "village"}, # Ooty Lake Road
]

WORLD_LOCATIONS = [
    {"latitude": 48.8584, "longitude": 2.2945, "country": "France", "state": "Île-de-France", "city": "Paris", "mode": "world", "category": "landmark"}, # Eiffel Tower
    {"latitude": 40.7580, "longitude": -73.9855, "country": "United States", "state": "New York", "city": "New York", "mode": "world", "category": "urban"}, # Times Square
    {"latitude": 41.8902, "longitude": 12.4922, "country": "Italy", "state": "Lazio", "city": "Rome", "mode": "world", "category": "landmark"}, # Colosseum
    {"latitude": 35.6595, "longitude": 139.7006, "country": "Japan", "state": "Tokyo", "city": "Tokyo", "mode": "world", "category": "urban"}, # Shibuya Crossing
    {"latitude": -33.8568, "longitude": 151.2153, "country": "Australia", "state": "New South Wales", "city": "Sydney", "mode": "world", "category": "landmark"}, # Sydney Opera House
    {"latitude": 51.5007, "longitude": -0.1246, "country": "United Kingdom", "state": "England", "city": "London", "mode": "world", "category": "landmark"}, # Big Ben
    {"latitude": 29.9792, "longitude": 31.1342, "country": "Egypt", "state": "Giza", "city": "Cairo", "mode": "world", "category": "landmark"}, # Pyramids of Giza
    {"latitude": 37.8199, "longitude": -122.4783, "country": "United States", "state": "California", "city": "San Francisco", "mode": "world", "category": "landmark"}, # Golden Gate Bridge
    {"latitude": -22.9519, "longitude": -43.2105, "country": "Brazil", "state": "Rio de Janeiro", "city": "Rio de Janeiro", "mode": "world", "category": "landmark"}, # Christ the Redeemer
    {"latitude": -33.9628, "longitude": 18.4098, "country": "South Africa", "state": "Western Cape", "city": "Cape Town", "mode": "world", "category": "rural"}, # Table Mountain
    {"latitude": 43.0799, "longitude": -79.0747, "country": "Canada", "state": "Ontario", "city": "Niagara Falls", "mode": "world", "category": "landmark"}, # Niagara Falls
    {"latitude": 1.2828, "longitude": 103.8609, "country": "Singapore", "state": None, "city": "Singapore", "mode": "world", "category": "urban"}, # Marina Bay Sands
    {"latitude": 55.7539, "longitude": 37.6208, "country": "Russia", "state": "Moscow", "city": "Moscow", "mode": "world", "category": "landmark"}, # Red Square
    {"latitude": 36.0544, "longitude": -112.1376, "country": "United States", "state": "Arizona", "city": "Grand Canyon", "mode": "world", "category": "rural"}, # Grand Canyon
    {"latitude": 35.3606, "longitude": 138.7274, "country": "Japan", "state": "Shizuoka", "city": "Mount Fuji", "mode": "world", "category": "rural"}, # Mount Fuji
    {"latitude": -13.1631, "longitude": -72.5450, "country": "Peru", "state": "Cusco", "city": "Machu Picchu", "mode": "world", "category": "landmark"}, # Machu Picchu
    {"latitude": 30.3285, "longitude": 35.4444, "country": "Jordan", "state": "Ma'an", "city": "Petra", "mode": "world", "category": "landmark"}, # Petra
    {"latitude": 45.4372, "longitude": 12.3346, "country": "Italy", "state": "Veneto", "city": "Venice", "mode": "world", "category": "urban"}, # Venice Canals
    {"latitude": 51.1789, "longitude": -1.8262, "country": "United Kingdom", "state": "England", "city": "Salisbury", "mode": "world", "category": "landmark"}, # Stonehenge
    {"latitude": 25.1972, "longitude": 55.2744, "country": "United Arab Emirates", "state": "Dubai", "city": "Dubai", "mode": "world", "category": "urban"}, # Burj Khalifa
]

async def seed_database():
    print("Connecting to database...")
    is_sqlite = settings.DATABASE_URL.startswith("sqlite")
    
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if is_sqlite else {},
    )
    
    async_session = async_sessionmaker(
        bind=engine,
        expire_on_commit=False
    )
    
    async with engine.begin() as conn:
        # Re-create tables on seed script execution
        print("Ensuring tables exist...")
        await conn.run_sync(Base.metadata.create_all)
        
    async with async_session() as session:
        # Check if locations are already seeded
        result = await session.execute(select(Location).limit(1))
        existing = result.scalars().first()
        
        if existing:
            print("Database already contains location data. Skipping seeding.")
            await engine.dispose()
            return
            
        print("Seeding locations...")
        all_locations = []
        for loc in INDIA_LOCATIONS + WORLD_LOCATIONS:
            all_locations.append(Location(**loc))
            
        session.add_all(all_locations)
        await session.commit()
        print(f"Successfully seeded {len(all_locations)} locations!")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_database())
