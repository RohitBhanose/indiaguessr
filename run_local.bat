@echo off
echo ===================================================
echo Starting IndiaGuessr Developer Servers...
echo ===================================================

:: Start Backend in a new window
start "IndiaGuessr Backend" cmd /k "cd backend && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

:: Start Frontend in a new window
start "IndiaGuessr Frontend" cmd /k "cd frontend && npm run dev"

echo Done! Dev servers are launching:
echo - Backend: http://127.0.0.1:8000
echo - Frontend: http://localhost:5173
echo ===================================================
