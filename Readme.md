# Company Search Agent

A full-stack application that uses Google Agent Development Kit (ADK) with Gemini 2.5 Flash to search for companies. Features a ChatGPT-like interface with chat history and real-time search capabilities powered by Temporal.io workflows.

## Features

- **ChatGPT-like Interface**: Sidebar with chat history and main chat area
- **Multi-Company Search**: Enter multiple company names at once
- **Google ADK Integration**: Uses Gemini 2.5 Flash with Google Search tool
- **Temporal.io Workflows**: Orchestrates company search operations
- **Session-based Chat History**: Maintains conversation context
- **PEP8 Compliant**: Backend follows Python PEP8 standards

## Tech Stack

### Frontend
- **React** with Vite
- **Axios** for API calls
- **React Icons** for UI icons
- Modern CSS styling

### Backend
- **Python** with FastAPI
- **Google Agent Development Kit (ADK)**
- **Gemini 2.5 Flash** model
- **Temporal.io** for workflow orchestration
- **PEP8** compliant code

## Project Structure

```
ReqAgent/
├── frontend/                 # React + Vite application
│   ├── src/
│   │   ├── App.jsx          # Main application component
│   │   ├── App.css          # Application styles
│   │   ├── index.css        # Global styles
│   │   └── main.jsx         # Entry point
│   ├── package.json
│   └── vite.config.js
│
└── backend/                  # Python backend
    ├── config/              # Configuration
    │   ├── settings.py      # Application settings
    │   └── __init__.py
    ├── workflows/           # Temporal workflows
    │   ├── company_search_workflow.py
    │   └── __init__.py
    ├── activities/          # Temporal activities
    │   ├── company_search.py
    │   └── __init__.py
    ├── app.py              # FastAPI server
    ├── worker.py           # Temporal worker
    ├── requirements.txt    # Python dependencies
    ├── .env               # Environment variables
    └── pyproject.toml     # Python tooling config
```

## Setup Instructions

### Prerequisites

1. **Python 3.11+** installed
2. **Node.js 18+** and npm installed
3. **Temporal Server** (local development)
4. **Google AI API Key** (already configured in the project)

### Step 1: Install Temporal Server

You need to have Temporal server running locally. Choose ONE method:

**Option A - Docker Compose (RECOMMENDED):**
```bash
# From the ReqAgent directory
docker-compose up
```

**Option B - Temporal CLI:**
```bash
# Windows
choco install temporal
# macOS
brew install temporal
# or download from https://docs.temporal.io/cli

# Then start server
temporal server start-dev
```

**Option C - Docker (with SQLite):**
```bash
docker run -p 7233:7233 -e DB=sqlite -e SQLITE_PRAGMA_journal_mode=WAL temporalio/auto-setup:latest
```

### Step 2: Setup Backend

**Windows (Easy way):**
```powershell
cd backend
setup.bat
```

**Manual setup (All platforms):**
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows PowerShell:
venv\Scripts\Activate.ps1
# On Windows CMD:
venv\Scripts\activate.bat
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify .env file exists with API key
# (already created with your API key)
```

**Note for Windows PowerShell users:** If you get an execution policy error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 3: Setup Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

## Running the Application

You need to run **three separate processes**:

### Terminal 1: Start Temporal Worker

```bash
cd backend
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
python worker.py
```

You should see:
```
INFO:__main__:Connecting to Temporal server at localhost:7233
INFO:__main__:Starting worker for task queue: company-search-queue
INFO:__main__:Worker started successfully
```

### Terminal 2: Start FastAPI Backend

```bash
cd backend
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
python app.py
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Terminal 3: Start React Frontend

```bash
cd frontend
npm run dev
```

You should see:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

## Usage

1. Open your browser and navigate to `http://localhost:5173`
2. You'll see the Company Search Agent interface with:
   - **Left sidebar**: Chat history (initially empty)
   - **Right side**: Main chat area with input field
3. Enter one or more company names in the input field
   - Examples: "Apple", "Microsoft, Google, Tesla", "Amazon Inc"
4. Press Enter or click the send button
5. The agent will:
   - Use Google Search (via Gemini) to find matching companies
   - Display results including company name, description, industry, location, and website
   - Save the conversation in the sidebar for later reference
6. Click "New Chat" to start a new conversation

## API Endpoints

### Backend API (Port 8000)

- **POST** `/api/search` - Search for companies
  ```json
  {
    "query": "Apple, Microsoft",
    "session_id": "optional-uuid"
  }
  ```

- **GET** `/api/sessions/{session_id}` - Get chat session
- **GET** `/api/sessions` - List all sessions
- **DELETE** `/api/sessions/{session_id}` - Delete session
- **GET** `/health` - Health check

## Code Quality

The backend follows PEP8 standards. To check code quality:

```bash
cd backend

# Format code with black
black .

# Sort imports
isort .

# Check with flake8
flake8 .
```

## Troubleshooting

### "Failed to connect to Temporal"
- Make sure Temporal server is running on `localhost:7233`
- Check with: `docker ps` or `temporal server status`

### "Failed to search companies"
- Ensure the Temporal worker is running
- Ensure the FastAPI backend is running
- Check the backend logs for errors

### "CORS errors"
- Make sure the frontend is running on `http://localhost:5173`
- Check that the backend CORS settings in `config/settings.py` include your frontend URL

### Google API Errors
- The API key is already configured
- If you get quota errors, you may need to wait or use a different API key
- Check the Google AI Studio console for usage limits

## Environment Variables

Located in `backend/.env`:

```env
GOOGLE_API_KEY=AIzaSyCI09gbgsjwnnk67GAu5Ul4CCICU1iB2Js
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=default
HOST=0.0.0.0
PORT=8000
```

## Development Notes

- **Session Storage**: Currently session-based (in-memory). Sessions are lost when the backend restarts.
- **Search Tool**: Uses Google's built-in search via Gemini ADK
- **Workflow**: Minimal Temporal workflow for demonstration
- **Multiple Companies**: Processed as a single query with combined results

## Future Enhancements

- Persistent storage (database) for chat history
- User authentication
- Export search results
- Advanced filtering and sorting
- Real-time streaming responses
- Company comparison features

## License

MIT

## Support

For issues or questions, please check:
- Temporal documentation: https://docs.temporal.io/
- Google ADK documentation: https://ai.google.dev/
- FastAPI documentation: https://fastapi.tiangolo.com/
- React documentation: https://react.dev/
