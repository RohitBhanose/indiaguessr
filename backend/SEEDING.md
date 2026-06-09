# Seeding verified Street View locations

This document explains how to run the seeder and validate counts.

Prerequisites:
- Activate your Python virtual environment and install requirements from `requirements.txt`.
- (Recommended) Provide a Google Maps API key with Street View & Geocoding enabled.

Run the seeder (example for world mode):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1   # PowerShell
pip install -r requirements.txt
# Run seeder for world mode (adjust --target as needed)
python scripts/seed_verified_locations.py --mode world --target 500 --apikey YOUR_GOOGLE_API_KEY
```

If you prefer environment variables instead of `--apikey`:

```powershell
$env:GOOGLE_MAPS_API_KEY = 'YOUR_GOOGLE_API_KEY'
python scripts/seed_verified_locations.py --mode world --target 500
```

Diagnostics endpoint (after starting backend):

- Start the backend: `uvicorn app.main:app --reload`
- Fetch diagnostics: `GET /api/v1/admin/locations/diagnostics`

This will return JSON with:
- `total`: total stored locations per mode
- `verified`: counts of verified locations per mode
- `by_category`: counts grouped by category per mode
- `samples`: up to 10 sample locations for each mode

If the seeder fails, inspect the error printed by the script. Common issues:
- Invalid or missing Google API key
- Network rate limits from external APIs
- Database file locked by another process

If you want me to run the seeder here using your API key, say so and provide the key (or confirm which environment variable to use).