# Quick Start Guide

This guide will help you get the Company Search Agent running quickly.

## Prerequisites Check

Before starting, ensure you have:

- [ ] Python 3.11+ installed (`python --version`)
- [ ] Node.js 18+ installed (`node --version`)
- [ ] Docker installed (for Temporal) OR Temporal CLI
- [ ] 3 terminal windows/tabs ready

## Quick Setup (5 minutes)

### 1. Start Temporal Server (Terminal 1)

```bash
# Using Docker (easiest)
docker run -p 7233:7233 temporalio/auto-setup:latest
```

**Keep this terminal running!**

### 2. Setup & Start Backend (Terminal 2)

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the worker
python worker.py
```

**Keep this terminal running!**

### 3. Start Backend API (Terminal 3)

```bash
# Navigate to backend (new terminal)
cd backend

# Activate virtual environment (Windows)
venv\Scripts\activate

# Start the API server
python app.py
```

**Keep this terminal running!**

### 4. Setup & Start Frontend (Terminal 4)

```bash
# Navigate to frontend (new terminal)
cd frontend

# Install dependencies (first time only)
npm install

# Start the dev server
npm run dev
```

**Keep this terminal running!**

## Access the Application

Open your browser and go to: **http://localhost:5173**

## Test It Out

1. Type a company name in the input field (e.g., "Apple")
2. Press Enter
3. Wait for the results to appear
4. Try multiple companies: "Microsoft, Google, Tesla"

## Common Issues

### Issue: "Cannot connect to Temporal"
**Solution**: Make sure Terminal 1 (Temporal server) is running

### Issue: "Failed to search companies"
**Solution**: Make sure Terminal 2 (worker.py) is running

### Issue: "Network Error"
**Solution**: Make sure Terminal 3 (app.py) is running on port 8000

### Issue: Frontend not loading
**Solution**: Make sure Terminal 4 (npm run dev) is running

## Stopping the Application

Press `Ctrl+C` in each terminal to stop:
1. Terminal 4 (Frontend)
2. Terminal 3 (Backend API)
3. Terminal 2 (Worker)
4. Terminal 1 (Temporal)

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check the API endpoints at http://localhost:8000/docs
- Explore the code in the `backend/` and `frontend/` directories

## Architecture Overview

```
Browser (localhost:5173)
    ↓
Frontend (React + Vite)
    ↓
Backend API (FastAPI on port 8000)
    ↓
Temporal Worker
    ↓
Google Gemini API (with Search Tool)
```

## Support

If you encounter issues:
1. Check that all 4 terminals are running
2. Look for error messages in each terminal
3. Verify the prerequisites are installed
4. Review the Troubleshooting section in README.md
