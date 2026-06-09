import asyncio
from sqlalchemy import select, func

from app.core.database import AsyncSessionLocal
from app.models.location import Location


async def run_diag():
    async with AsyncSessionLocal() as db:
        total_india = (await db.execute(select(func.count()).select_from(Location).where(func.lower(Location.mode) == 'india'))).scalar_one()
        total_world = (await db.execute(select(func.count()).select_from(Location).where(func.lower(Location.mode) == 'world'))).scalar_one()
        verified_india = (await db.execute(select(func.count()).select_from(Location).where(func.lower(Location.mode) == 'india', Location.verified == True))).scalar_one()
        verified_world = (await db.execute(select(func.count()).select_from(Location).where(func.lower(Location.mode) == 'world', Location.verified == True))).scalar_one()

        rows_india = (await db.execute(select(Location.category, func.count()).where(func.lower(Location.mode) == 'india').group_by(Location.category))).all()
        rows_world = (await db.execute(select(Location.category, func.count()).where(func.lower(Location.mode) == 'world').group_by(Location.category))).all()

        print("total:", {'india': total_india, 'world': total_world})
        print("verified:", {'india': verified_india, 'world': verified_world})
        print('by_category_india:', {r[0] or 'unknown': r[1] for r in rows_india})
        print('by_category_world:', {r[0] or 'unknown': r[1] for r in rows_world})


if __name__ == '__main__':
    asyncio.run(run_diag())
