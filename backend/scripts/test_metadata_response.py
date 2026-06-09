import asyncio
import httpx

API_KEY = ""

async def main():
    # Known point in Delhi
    url = f"https://maps.googleapis.com/maps/api/streetview/metadata?location=28.6139,77.2090&key={API_KEY}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        print("Status:", r.status_code)
        print("Response JSON:")
        import json
        print(json.dumps(r.json(), indent=2))

asyncio.run(main())
