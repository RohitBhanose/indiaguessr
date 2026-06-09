import asyncio
from app.services.geocode import reverse_geocode

async def t():
    lat=24.0656321319702
    lng=90.88285486464397
    country, state, city, meta = await reverse_geocode(lat, lng)
    print('rev:', country, state, city)
    print('meta provider:', meta.get('provider'))

asyncio.run(t())
