"""Reclassify categories for existing locations using improved heuristics.

This script will iterate locations and update the `category` field using
`geocode.classify_category_from_meta` backed by reverse geocoding where needed.
"""
import asyncio
from app.core.database import AsyncSessionLocal
from app.models.location import Location
from app.services.geocode import reverse_geocode, classify_category_from_meta
from sqlalchemy import select


async def reclassify(batch: int = 100):
    async with AsyncSessionLocal() as db:
        stmt = select(Location)
        res = await db.execute(stmt)
        locs = res.scalars().all()
        updated = 0
        for l in locs:
            country = l.country or ''
            # Get fresh meta if necessary
            meta_needed = True
            meta = None
            if meta_needed:
                country_rev, state, city, meta = await reverse_geocode(l.latitude, l.longitude)
            new_cat = classify_category_from_meta(meta, l.city or city)
            if new_cat and new_cat != (l.category or '').lower():
                l.category = new_cat
                db.add(l)
                updated += 1
                if updated % 50 == 0:
                    await db.commit()
        if updated > 0:
            await db.commit()
        print(f"Reclassified {updated} locations.")


if __name__ == '__main__':
    asyncio.run(reclassify())
