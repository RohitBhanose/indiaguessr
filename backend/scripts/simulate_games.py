import asyncio
import json
import argparse
from collections import Counter, defaultdict

from app.core.database import AsyncSessionLocal
from app.services.game_service import GameService
from app.models.game import GameSession, Round
from sqlalchemy import select
from sqlalchemy.orm import selectinload


async def fetch_game_rounds(db, game_id):
    stmt = select(GameSession).options(selectinload(GameSession.rounds).selectinload(Round.location)).where(GameSession.id == game_id)
    res = await db.execute(stmt)
    gs = res.scalar_one()
    rounds = []
    for r in sorted(gs.rounds, key=lambda x: x.round_number):
        loc = r.location
        rounds.append({
            'round_number': r.round_number,
            'country': (loc.country or '').strip(),
            'state': (loc.state or '').strip(),
            'city': (loc.city or '').strip(),
            'category': (loc.category or '').strip().lower(),
        })
    return rounds


async def simulate(n: int = 100):
    india_cat_counter = Counter()
    world_country_counter = Counter()
    world_continent_counter = Counter()
    world_india_counts = []

    async with AsyncSessionLocal() as db:
        for i in range(n):
            gs, fr = await GameService.create_game(db, 'india')
            rounds = await fetch_game_rounds(db, gs.id)
            for r in rounds:
                india_cat_counter[r['category']] += 1

    async with AsyncSessionLocal() as db:
        for i in range(n):
            gs, fr = await GameService.create_game(db, 'world')
            rounds = await fetch_game_rounds(db, gs.id)
            india_count = 0
            for r in rounds:
                country = (r['country'] or '').strip()
                world_country_counter[country or 'unknown'] += 1
                # simple continent mapping reused from game_service logic
                def _country_to_continent(country: str) -> str:
                    c = (country or '').strip().lower()
                    if any(x in c for x in ['united states','usa','us','canada','mexico']):
                        return 'North America'
                    if any(x in c for x in ['brazil','argentina','chile','colombia','peru','venezuela']):
                        return 'South America'
                    if any(x in c for x in ['united kingdom','uk','france','germany','italy','spain','netherlands','poland','russia','sweden']):
                        return 'Europe'
                    if any(x in c for x in ['china','japan','india','pakistan','bangladesh','south korea','korea','israel','singapore']):
                        return 'Asia'
                    if any(x in c for x in ['egypt','south africa','nigeria','kenya','morocco']):
                        return 'Africa'
                    if any(x in c for x in ['australia','new zealand']):
                        return 'Oceania'
                    return 'Other'

                world_continent_counter[_country_to_continent(country)] += 1
                if 'india' in (country or '').lower():
                    india_count += 1
            world_india_counts.append(india_count)

    # Print results
    print('India category distribution (total rounds =', sum(india_cat_counter.values()), ')')
    for k, v in india_cat_counter.items():
        print(f'  {k}: {v} ({v / max(1, sum(india_cat_counter.values())) * 100:.1f}%)')

    print('\nWorld country distribution (top 20):')
    for country, cnt in world_country_counter.most_common(20):
        print(f'  {country}: {cnt}')

    print('\nWorld continent distribution:')
    for cont, cnt in world_continent_counter.items():
        print(f'  {cont}: {cnt}')

    avg_india = sum(world_india_counts) / len(world_india_counts) if world_india_counts else 0
    print(f'\nWorld games: average India rounds per game: {avg_india:.2f}')
    print(f'Max India rounds observed in a single World game: {max(world_india_counts) if world_india_counts else 0}')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--games', type=int, default=100)
    args = p.parse_args()
    asyncio.run(simulate(args.games))
