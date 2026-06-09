import asyncio
import httpx

API_KEY = ""

# First 3 coordinates from our DB
coords = [
    (30.20840180445937, 74.77318448452111),
    (12.923113751128643, 78.16878332429545),
    (23.955741837485366, 73.79557882158505)
]

async def main():
    async with httpx.AsyncClient() as client:
        for i, (lat, lng) in enumerate(coords, 1):
            url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location={lat},{lng}&key={API_KEY}"
            r = await client.get(url)
            print(f"Row {i} ({lat}, {lng}): Status Code: {r.status_code}")
            import json
            print(json.dumps(r.json(), indent=2))
            print("-" * 50)

asyncio.run(main())
