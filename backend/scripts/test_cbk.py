import asyncio
import httpx

async def main():
    # Test using coordinate
    url_ll = "https://cbk0.google.com/cbk?output=json&ll=30.208402,74.773184"
    # Test using pano_id
    url_pano = "https://cbk0.google.com/cbk?output=json&panoid=rhAuykTgSBMX1l0_fiYWVg"
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    async with httpx.AsyncClient(headers=headers) as client:
        r1 = await client.get(url_ll)
        print("LL Status:", r1.status_code)
        if r1.status_code == 200:
            try:
                print("LL JSON keys:", r1.json().keys())
                # print some links if present
                data = r1.json()
                if 'Annotation' in data:
                    print("Annotation links:", data['Annotation'].get('Link'))
            except Exception as e:
                print("Error parsing LL:", e)
                print("Response starts with:", r1.text[:200])
                
        r2 = await client.get(url_pano)
        print("\nPano Status:", r2.status_code)
        if r2.status_code == 200:
            try:
                print("Pano JSON keys:", r2.json().keys())
                data = r2.json()
                if 'Annotation' in data:
                    print("Annotation links:", data['Annotation'].get('Link'))
            except Exception as e:
                print("Error parsing Pano:", e)
                print("Response starts with:", r2.text[:200])

asyncio.run(main())
