import asyncio
from app.core.database import AsyncSessionLocal
from app.models.location import Location
from app.services.geocode import reverse_geocode
from sqlalchemy import select

async def run():
    async with AsyncSessionLocal() as db:
        stmt = select(Location).where(Location.mode.ilike('india'))
        res = await db.execute(stmt)
        locs = res.scalars().all()
        for l in locs[:20]:
            country, state, city, meta = await reverse_geocode(l.latitude, l.longitude)
            print(f"ID={l.id} lat={l.latitude} lng={l.longitude} db_country={l.country} rev_country={country}")

if __name__ == '__main__':
    asyncio.run(run())
