import asyncio, os
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from sqlalchemy import text

async def run():
    print('PWD:', os.getcwd())
    print('DATABASE_URL:', settings.DATABASE_URL)
    async with AsyncSessionLocal() as db:
        res = await db.execute(text('SELECT COUNT(*) FROM locations'))
        print('SQLAlchemy count:', res.scalar())

if __name__ == '__main__':
    asyncio.run(run())
