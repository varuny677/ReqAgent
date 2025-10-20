# Setup Guide - Step by Step

This guide will help you fix the errors and get everything running.

## Problem 1: Python Dependencies Not Installed

### Solution: Run the setup script

```powershell
cd backend
setup.bat
```

This will:
1. Create a virtual environment
2. Activate it
3. Install all required dependencies

**OR manually:**

```powershell
cd backend

# Create virtual environment
python -m venv venv

# Activate it (Windows PowerShell)
venv\Scripts\Activate.ps1

# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate again
venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## Problem 2: Temporal Docker Error

The simple docker run command has issues. Here are **3 solutions** (pick one):

### Option A: Use Docker Compose (RECOMMENDED)

```powershell
# From the ReqAgent directory
docker-compose up
```

This starts Temporal with proper configuration using SQLite.

### Option B: Use Temporal CLI (Easiest)

Download and install Temporal CLI:

**Windows:**
```powershell
# Using Chocolatey
choco install temporal

# OR download from https://github.com/temporalio/cli/releases
```

Then start the dev server:
```powershell
temporal server start-dev
```

### Option C: Fixed Docker Command

```powershell
docker run -p 7233:7233 -e DB=sqlite -e SQLITE_PRAGMA_journal_mode=WAL temporalio/auto-setup:latest
```

---

## Complete Startup Sequence

### Step 1: Start Temporal Server

**Choose ONE method:**

**Method A - Docker Compose:**
```powershell
docker-compose up
```

**Method B - Temporal CLI:**
```powershell
temporal server start-dev
```

**Method C - Docker (fixed):**
```powershell
docker run -p 7233:7233 -e DB=sqlite -e SQLITE_PRAGMA_journal_mode=WAL temporalio/auto-setup:latest
```

**Keep this terminal running!**

---

### Step 2: Setup Backend (One-time)

Open a **NEW** PowerShell terminal:

```powershell
cd backend
setup.bat
```

This installs all Python dependencies.

---

### Step 3: Start Temporal Worker

In the same terminal (or a new one with venv activated):

```powershell
cd backend

# If not already activated
venv\Scripts\Activate.ps1

# Start worker
python worker.py
```

You should see:
```
INFO:__main__:Connecting to Temporal server at localhost:7233
INFO:__main__:Worker started successfully
```

**Keep this terminal running!**

---

### Step 4: Start Backend API

Open a **NEW** PowerShell terminal:

```powershell
cd backend

# Activate virtual environment
venv\Scripts\Activate.ps1

# Start API server
python app.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Keep this terminal running!**

---

### Step 5: Start Frontend

Open a **NEW** PowerShell terminal:

```powershell
cd frontend

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev
```

You should see:
```
➜  Local:   http://localhost:5173/
```

**Keep this terminal running!**

---

### Step 6: Open Browser

Navigate to: **http://localhost:5173**

---

## Quick Verification Checklist

- [ ] Temporal server running (Terminal 1)
- [ ] Worker running without errors (Terminal 2)
- [ ] API server running on port 8000 (Terminal 3)
- [ ] Frontend running on port 5173 (Terminal 4)
- [ ] Browser opened to http://localhost:5173

---

## Troubleshooting

### "Execution policy" error in PowerShell

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### "venv\Scripts\Activate.ps1 cannot be loaded"

Use Command Prompt instead:
```cmd
venv\Scripts\activate.bat
```

### "ModuleNotFoundError: No module named 'pydantic_settings'"

The virtual environment wasn't activated or dependencies weren't installed:
```powershell
cd backend
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### "Cannot connect to Temporal"

Make sure Temporal is running:
```powershell
# Test if Temporal is running
curl http://localhost:7233
```

If it fails, restart Temporal using one of the methods above.

### Port already in use

Check what's using the port:
```powershell
# Check port 8000 (backend)
netstat -ano | findstr :8000

# Check port 5173 (frontend)
netstat -ano | findstr :5173

# Check port 7233 (Temporal)
netstat -ano | findstr :7233
```

Kill the process or use different ports.

---

## All-in-One Startup (After Initial Setup)

Once everything is installed, you need 4 terminals:

**Terminal 1:**
```powershell
docker-compose up
# OR
temporal server start-dev
```

**Terminal 2:**
```powershell
cd backend
venv\Scripts\Activate.ps1
python worker.py
```

**Terminal 3:**
```powershell
cd backend
venv\Scripts\Activate.ps1
python app.py
```

**Terminal 4:**
```powershell
cd frontend
npm run dev
```

**Browser:**
Open http://localhost:5173

---

## Testing the Application

1. Type "Apple" in the search box
2. Press Enter
3. Wait 5-10 seconds for results
4. You should see company information cards

---

## If Everything Fails

1. **Stop all processes** (Ctrl+C in each terminal)
2. **Clean start:**

```powershell
# Remove and recreate venv
cd backend
rmdir /s venv
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Frontend
cd ../frontend
rmdir /s node_modules
npm install

# Temporal
docker-compose down -v
docker-compose up
```

3. Follow the startup sequence again

---

## Need More Help?

Check the error messages in each terminal and refer to:
- [README.md](README.md) for detailed documentation
- [QUICKSTART.md](QUICKSTART.md) for quick reference
- Logs in each terminal for specific error messages
