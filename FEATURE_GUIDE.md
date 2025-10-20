# Two-Stage Company Search Feature Guide

## Overview

This application now supports a **two-stage company search workflow**:

1. **Stage 1**: Search for companies by name → Get a numbered list of matching companies
2. **Stage 2**: Select a company by number → Get detailed JSON information about that company

---

## How It Works

### Stage 1: Company Search

**Input**: Company name (e.g., "metlife")

**Output**: Numbered list of matching companies

```json
{
  "mode": "company_list",
  "count": 4,
  "companies": [
    {
      "number": 1,
      "name": "MetLife, Inc.",
      "description": "Leading global provider of insurance...",
      "industry": "Insurance, Financial Services",
      "location": "New York, NY, USA",
      "website": "https://www.metlife.com/"
    },
    {
      "number": 2,
      "name": "MetLife Services and Solutions, LLC",
      "description": "Provides various services...",
      "industry": "Insurance, Financial Services",
      "location": null,
      "website": null
    },
    ...
  ],
  "message": "Found 4 companies. Please enter a number to get detailed information."
}
```

### Stage 2: Detailed Company Information

**Input**: Number from the list (e.g., "1")

**Output**: Detailed JSON with comprehensive company information

```json
{
  "mode": "detailed_info",
  "company_number": 1,
  "data": {
    "Company name": "MetLife, Inc.",
    "Sector": "Financial Services",
    "Sub Sector": "Insurance",
    "Networth": "$44.52 billion USD (Market Cap)",
    "No of Employees": "42,000+",
    "Country of origin": "United States",
    "Global presence": "Yes - Operates in over 40 countries",
    "List of countries they operate in": [
      "United States",
      "Japan",
      "Latin America",
      "Asia Pacific",
      "Europe",
      "Middle East"
    ],
    "brief about company": "MetLife is one of the world's leading financial services companies, providing insurance, annuities, and employee benefit programs to millions of customers. The company serves individual and institutional customers through a broad range of life insurance, annuities, retirement plans, and investment management services.",
    "Compliance Requirements": [
      "SOX (Sarbanes-Oxley)",
      "GLBA (Gramm-Leach-Bliley Act)",
      "NAIC (National Association of Insurance Commissioners)",
      "GDPR (General Data Protection Regulation)",
      "State Insurance Regulations",
      "SEC Regulations",
      "FINRA Compliance"
    ]
  }
}
```

---

## Implementation Details

### Key Components

#### 1. **Activities** (`backend/activities/company_search.py`)

- `search_companies()` - Searches for companies using Gemini AI with web grounding
- `get_detailed_company_info()` - Fetches comprehensive company details using Gemini AI
- `parse_company_input()` - Parses company names from user input

#### 2. **Workflows**

- `CompanySearchWorkflow` (`backend/workflows/company_search_workflow.py`) - Orchestrates company list search
- `CompanyDetailWorkflow` (`backend/workflows/company_detail_workflow.py`) - Orchestrates detailed info retrieval

#### 3. **API Endpoint** (`backend/app.py`)

- **POST** `/api/search` - Intelligent endpoint that:
  - Detects if input is a number → Returns detailed info
  - Detects if input is text → Returns company list
  - Maintains session state to track company lists

#### 4. **Session Management**

- `chat_sessions` - Stores conversation history
- `session_company_lists` - Stores company lists per session for selection

---

## Usage Flow

### Example Interaction

```bash
# Request 1: Search for companies
POST /api/search
{
  "query": "metlife",
  "session_id": "abc-123"
}

# Response 1: Numbered list
{
  "mode": "company_list",
  "count": 4,
  "companies": [
    { "number": 1, "name": "MetLife, Inc.", ... },
    { "number": 2, "name": "MetLife Services and Solutions, LLC", ... },
    ...
  ]
}

# Request 2: Select company
POST /api/search
{
  "query": "1",
  "session_id": "abc-123"  # Same session!
}

# Response 2: Detailed JSON
{
  "mode": "detailed_info",
  "company_number": 1,
  "data": {
    "Company name": "MetLife, Inc.",
    "Sector": "Financial Services",
    "Networth": "$44.52 billion USD",
    ...
  }
}
```

---

## Compliance Requirements Logic

The system intelligently infers compliance requirements based on the company's industry:

| Industry | Compliance Frameworks |
|----------|----------------------|
| Healthcare | HIPAA, HITRUST |
| Financial Services | PCI-DSS, SOX, GLBA |
| Technology/SaaS | SOC2, ISO27001, GDPR |
| Government Contractors | FedRAMP, NIST |
| General (EU operations) | GDPR |
| General (California) | CCPA |

If insufficient data is available, the system returns `"Insufficient data"` for that field.

---

## Error Handling

### Invalid Selection
```json
{
  "status_code": 400,
  "detail": "Invalid selection. Please choose a number between 1 and 4."
}
```

### No Company List
```json
{
  "status_code": 400,
  "detail": "No company list found. Please search for companies first."
}
```

---

## Testing

### Prerequisites
1. Temporal server running (`temporal server start-dev`)
2. Backend worker running (`cd backend && python worker.py`)
3. Backend API running (`cd backend && python app.py`)

### Test Commands

```bash
# Test 1: Search for companies
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "metlife",
    "session_id": "test-session-1"
  }'

# Test 2: Select company #1
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "1",
    "session_id": "test-session-1"
  }'
```

---

## Architecture

```
User Input "metlife"
    ↓
API Endpoint (/api/search)
    ↓
CompanySearchWorkflow
    ↓
search_companies Activity
    ↓
Gemini AI (with web grounding)
    ↓
Numbered Company List
    ↓
User Input "1"
    ↓
API Endpoint (/api/search)
    ↓
CompanyDetailWorkflow
    ↓
get_detailed_company_info Activity
    ↓
Gemini AI (with web grounding)
    ↓
Detailed JSON Response
```

---

## Key Features

✅ **Session-based**: Maintains context across multiple requests
✅ **Intelligent Detection**: Automatically detects search vs. selection mode
✅ **Numbered Lists**: Easy selection with numbered companies
✅ **Comprehensive Data**: 10+ fields including compliance requirements
✅ **Error Validation**: Validates selections and provides helpful errors
✅ **Web Grounding**: Uses Gemini's built-in search for up-to-date information
✅ **Scalable**: Built on Temporal for reliable workflow orchestration

---

## Future Enhancements

- [ ] Export to PDF/CSV
- [ ] Compare multiple companies
- [ ] Historical data tracking
- [ ] Custom compliance framework queries
- [ ] Multi-language support
- [ ] Company relationship mapping

---

## Notes

- The system uses **Gemini 2.0 Flash** which has built-in web search capabilities
- Session state is stored **in-memory** (use Redis/Database for production)
- Compliance requirements are **inferred** based on industry best practices
- All responses are structured JSON for easy integration

---

## Support

For issues or questions, please refer to:
- [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)
- [SETUP_GUIDE.md](./SETUP_GUIDE.md)
- [Readme.md](./Readme.md)
