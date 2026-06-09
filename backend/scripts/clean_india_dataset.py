"""Clean India-mode locations that are not in India according to reverse-geocode.

Usage:
  python clean_india_dataset.py --dry-run
  python clean_india_dataset.py --apply

By default runs a dry-run and prints candidates; use --apply to delete them.
"""
import argparse
import asyncio
from app.core.database import AsyncSessionLocal
from app.models.location import Location
from app.services.geocode import reverse_geocode
from sqlalchemy import select, func
from typing import List
from sqlalchemy import delete
from app.core.config import settings


async def find_non_india(apply_changes: bool):
    print('Using DATABASE_URL=', settings.DATABASE_URL)
    async with AsyncSessionLocal() as db:
        # First, check DB-stored country field for quick candidates
        quick_stmt = select(Location).where(Location.mode.ilike('india'), (Location.country == None) | (~func.lower(Location.country).like('%india%')))
        quick_res = await db.execute(quick_stmt)
        quick_locs = quick_res.scalars().all()

        to_delete: List[Location] = []
        # Add DB-candidates immediately
        for l in quick_locs:
            to_delete.append((l, l.country, l.state, l.city, 'db_country_mismatch'))

        # For remaining India-mode rows, double-check via reverse-geocoding
        check_stmt = select(Location).where(Location.mode.ilike('india'))
        res = await db.execute(check_stmt)
        locs = res.scalars().all()
        for l in locs:
            # skip if already in quick list
            if any(x[0].id == l.id for x in to_delete):
                continue
            country, state, city, meta = await reverse_geocode(l.latitude, l.longitude)
            if not country or 'india' not in country.lower():
                to_delete.append((l, country, state, city, 'reverse_geocode'))

        print(f"Found {len(to_delete)} India-mode rows that appear to be outside India (candidates).")
        for l, country, state, city, reason in to_delete:
            print(f"ID={l.id} lat={l.latitude} lng={l.longitude} country_db={l.country} country_rev={country} city={city} state={state} reason={reason}")

        if apply_changes and to_delete:
            ids = [l.id for (l, *_ ) in to_delete]
            # Batch delete using SQLAlchemy delete
            delete_stmt = delete(Location).where(Location.id.in_(ids))
            print('Executing delete:', delete_stmt)
            await db.execute(delete_stmt)
            await db.commit()
            print(f'Deleted {len(ids)} non-India entries.')


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true', help='Actually delete entries (otherwise dry-run)')
    return p.parse_args()


if __name__ == '__main__':
    args = parse_args()
    asyncio.run(find_non_india(args.apply))
