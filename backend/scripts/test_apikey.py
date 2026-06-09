import asyncio
import httpx
from app.core.config import settings

async def main():
    api_key = settings.GOOGLE_MAPS_API_KEY
    print("API Key:", api_key)
    # Test reverse geocoding for a known point in Delhi (28.6139, 77.2090)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng=28.6139,77.2090&key={api_key}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        print("Status Code:", r.status_code)
        data = r.json()
        print("API Status:", data.get("status"))
        if data.get("status") == "OK":
            print("Formatted address:", data["results"][0]["formatted_address"])
            print("Success!")
        else:
            print("Error message:", data.get("error_message"))

asyncio.run(main())
