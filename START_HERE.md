# 🚀 START HERE - Quick Fix Guide

## You encountered these errors:

1. ❌ `ModuleNotFoundError: No module named 'pydantic_settings'`
2. ❌ `CASSANDRA_SEEDS env must be set if DB is cassandra`

## ✅ Here's how to fix them:

---

## Fix #1: Install Python Dependencies

Run this in PowerShell:

```powershell
cd backend
setup.bat
```

This will:
- Create a virtual environment
- Install all required Python packages
- Fix the `ModuleNotFoundError`

---

## Fix #2: Run Temporal with Proper Config

**Stop the current Docker container** (Ctrl+C if it's running)

Then use **Docker Compose** (easiest):

```powershell
# From the ReqAgent directory (not backend!)
cd ..
docker-compose up
```

This starts Temporal with SQLite (no Cassandra needed).

---

## Complete Startup Steps (After Fixes)

### Terminal 1: Temporal Server
```powershell
docker-compose up
```
✅ Wait until you see "Started" messages

### Terminal 2: Temporal Worker
```powershell
cd backend
venv\Scripts\Activate.ps1
python worker.py
```
✅ Wait for "Worker started successfully"

### Terminal 3: Backend API
```powershell
cd backend
venv\Scripts\Activate.ps1
python app.py
```
✅ Wait for "Uvicorn running on http://0.0.0.0:8000"

### Terminal 4: Frontend
```powershell
cd frontend
npm install
npm run dev
```
✅ Wait for "Local: http://localhost:5173"

### Browser
Open: **http://localhost:5173**

---

## If You Get PowerShell Execution Policy Error

Run this once:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try activating venv again:
```powershell
venv\Scripts\Activate.ps1
```

---

## Alternative: Use CMD instead of PowerShell

If PowerShell gives you trouble, use Command Prompt (cmd.exe):

```cmd
cd backend
setup.bat
venv\Scripts\activate.bat
python worker.py
```

---

## Still Having Issues?

Read the detailed guide: [SETUP_GUIDE.md](SETUP_GUIDE.md)

Or check: [README.md](README.md)

---

## Quick Test After Setup

1. Open browser to http://localhost:5173
2. Type "Apple" in the search box
3. Press Enter
4. Wait 5-10 seconds
5. You should see company results!

---

**That's it! 🎉**
