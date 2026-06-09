import asyncio
import json
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.services.game_service import GameService
from app.models.game import GameSession, Round


async def fetch_game_details(db, game_id):
    stmt = select(GameSession).options(selectinload(GameSession.rounds).selectinload(Round.location)).where(GameSession.id == game_id)
    res = await db.execute(stmt)
    gs = res.scalar_one()
    rounds = []
    for r in sorted(gs.rounds, key=lambda x: x.round_number):
        loc = r.location
        rounds.append({
            'round_number': r.round_number,
            'location_id': loc.id,
            'lat': loc.latitude,
            'lng': loc.longitude,
            'country': loc.country,
            'state': loc.state,
            'city': loc.city,
            'category': loc.category,
        })
    return rounds


async def run_samples():
    india_games = []
    world_games = []

    async with AsyncSessionLocal() as db:
        # Create 5 India games
        for i in range(5):
            gs, fr = await GameService.create_game(db, 'india')
            rounds = await fetch_game_details(db, gs.id)
            india_games.append({'game_id': gs.id, 'rounds': rounds})

    async with AsyncSessionLocal() as db:
        # Create 5 World games
        for i in range(5):
            gs, fr = await GameService.create_game(db, 'world')
            rounds = await fetch_game_details(db, gs.id)
            world_games.append({'game_id': gs.id, 'rounds': rounds})

    # Print samples
    out = {'india_games': india_games, 'world_games': world_games}
    print(json.dumps(out, indent=2, ensure_ascii=False))

    # Simple validation: India mode urban/suburban ratio
    u_s = 0
    total_india_rounds = 0
    for g in india_games:
        for r in g['rounds']:
            total_india_rounds += 1
            cat = (r.get('category') or '').lower()
            if cat in ('urban', 'suburban'):
                u_s += 1
    print('\nIndia games: urban+suburban {}/{} ({:.1f}%)'.format(u_s, total_india_rounds, (u_s/total_india_rounds*100) if total_india_rounds else 0))

    # Validate world games: max 1 India per 5-round game
    for g in world_games:
        india_count = sum(1 for r in g['rounds'] if r.get('country') and 'india' in (r.get('country') or '').lower())
        print(f"World game {g['game_id']} India rounds: {india_count}")


if __name__ == '__main__':
    asyncio.run(run_samples())
