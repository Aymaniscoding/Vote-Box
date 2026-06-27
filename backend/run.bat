@echo off
echo ========================================
echo   VoteBox Setup and Run (Windows)
echo ========================================
echo.

REM 1. Install dependencies
echo [*] Installing dependencies...
pip install -r requirements.txt
echo.

REM 2. Setup database (MySQL must be running)
echo [*] Setting up MySQL database...
python setup_db.py
echo.

REM 3. Start the app
echo [*] Starting VoteBox at http://127.0.0.1:5001
echo     Press Ctrl+C to stop the server.
echo.
python app.py
