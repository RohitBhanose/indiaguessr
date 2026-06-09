import asyncio

from app.core.database import engine
from app.models.base import Base


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Created tables")


if __name__ == '__main__':
    asyncio.run(main())
