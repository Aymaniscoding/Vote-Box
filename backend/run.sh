#!/bin/bash

# ── Colors for output ──
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE} Starting VoteBox Setup & Run...${NC}"

# 1. Check for Python dependencies (errors are shown, not hidden)
echo -e "${YELLOW} Checking dependencies...${NC}"
pip install -r requirements.txt

# 2. Check if database exists
if [ ! -f "voting.db" ]; then
    echo -e "${YELLOW} Database not found. Initializing...${NC}"
    python3 setup_db.py
else
    echo -e "${GREEN} Database found.${NC}"
fi

# 3. Start the application
echo -e "${GREEN} Application starting at http://127.0.0.1:5001${NC}"
echo -e "${BLUE}Press Ctrl+C to stop the server.${NC}"

python3 app.py
