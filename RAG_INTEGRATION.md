# RAG Integration Guide

## 📌 Quick Overview

This RAG system runs as a **standalone API service** that provides document chunk retrieval. You can integrate it into ANY project (Python, JavaScript, React, Node.js, etc.) by making HTTP requests.

---

## 🚀 Getting Started

### Step 1: Start the RAG API Server

In this project directory, run:

```bash
python api.py
```

**API will start on**: `http://localhost:5000`

Keep this terminal running - this is your RAG server!

---

### Step 2: Open Your Other Project

Open a **new VS Code window/tab** for your other project. The RAG API will continue running in the background.

---

## 🌐 API Endpoint Details

### Base URL
```
http://localhost:5000
```

### Available Endpoints

#### 1. Health Check
**GET** `http://localhost:5000/api/health`

**Response:**
```json
{
  "status": "healthy",
  "message": "RAG API is running"
}
```

---

#### 2. Retrieve Chunks (Main Endpoint)
**POST** `http://localhost:5000/api/retrieve`

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "What are AWS IAM best practices?",
  "top_k": 6
}
```

**Parameters:**
- `query` (required): Your question/search query
- `top_k` (optional): Number of chunks to return (default: 6, max: 20)

**Response:**
```json
{
  "query": "What are AWS IAM best practices?",
  "chunks": [
    {
      "id": "c55b6de62f8e18bdcefd5f4343f76456",
      "content": "Full text content of the document chunk...",
      "similarity": 0.8523,
      "source": "iam-ug.pdf",
      "centroid_info": "aws/best_practices",
      "metadata": {
        "source": "iam-ug.pdf",
        "page": 42,
        "chunk_index": 5,
        "file_path": "data/AWS/best_practices/iam-ug.pdf"
      }
    },
    {
      "id": "another_chunk_id",
      "content": "Another relevant chunk...",
      "similarity": 0.7891,
      "source": "ec2-dg.pdf",
      "centroid_info": "aws/services",
      "metadata": {
        "source": "ec2-dg.pdf",
        "page": 156
      }
    }
  ],
  "total_chunks": 6,
  "routing_info": {
    "centroids_evaluated": 12,
    "centroids_selected": 2,
    "adaptive_window": 6
  },
  "performance": {
    "total_time": 1.523,
    "chunks_returned": 6
  }
}
```

---

#### 3. System Statistics
**GET** `http://localhost:5000/api/stats`

**Response:**
```json
{
  "collections": 4,
  "total_chunks": 30608,
  "collections_detail": {
    "aws_services": 11632,
    "best_practices": 17747,
    "aws_patterns": 702,
    "aws_compliance": 527
  }
}
```

---

## 🔗 CORS Configuration

**Current Settings**: ✅ CORS is ENABLED for ALL origins

The API is already configured to accept requests from:
- ✅ Any localhost port (3000, 3001, 8080, etc.)
- ✅ Any domain
- ✅ Different VS Code projects
- ✅ Browser-based apps
- ✅ Mobile apps

**No additional CORS configuration needed!**

If you need to restrict origins in production, edit `api.py`:

```python
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "https://yourdomain.com"],
        "methods": ["GET", "POST", "OPTIONS"]
    }
})
```

---

## 💻 Integration Examples

### Python Integration (Your Agentic AI Project)

```python
import requests
import google.generativeai as genai

# Configure your Gemini API
genai.configure(api_key="YOUR_GEMINI_API_KEY")
model = genai.GenerativeModel('gemini-pro')

def query_rag_and_generate_response(user_query):
    """
    Step 1: Get relevant chunks from RAG
    Step 2: Send to your Gemini AI
    Step 3: Return AI-generated response
    """

    # STEP 1: Call RAG API to get chunks
    rag_response = requests.post(
        'http://localhost:5000/api/retrieve',
        json={
            'query': user_query,
            'top_k': 6  # Get 6 most relevant chunks
        },
        headers={'Content-Type': 'application/json'}
    )

    if rag_response.status_code != 200:
        return f"Error: {rag_response.json().get('error')}"

    data = rag_response.json()
    chunks = data['chunks']

    # STEP 2: Format context from chunks
    context = "\n\n---\n\n".join([
        f"[Source: {chunk['source']}]\n{chunk['content']}"
        for chunk in chunks
    ])

    # STEP 3: Send to YOUR Gemini AI
    prompt = f"""Based on the following AWS documentation context, answer the question.

Context:
{context}

Question: {user_query}

Answer (be concise and cite sources):"""

    response = model.generate_content(prompt)

    return response.text

# Usage
if __name__ == "__main__":
    question = "What are the security best practices for AWS EC2?"
    answer = query_rag_and_generate_response(question)
    print(answer)
```

---

### JavaScript/Node.js Integration

```javascript
const fetch = require('node-fetch'); // npm install node-fetch
// Or use axios: npm install axios

async function queryRAG(question) {
    const response = await fetch('http://localhost:5000/api/retrieve', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            query: question,
            top_k: 6
        })
    });

    if (!response.ok) {
        throw new Error(`RAG API Error: ${response.statusText}`);
    }

    const data = await response.json();
    return data.chunks;
}

// Usage with your Gemini AI
async function getAIResponse(question) {
    // Step 1: Get chunks from RAG
    const chunks = await queryRAG(question);

    // Step 2: Format context
    const context = chunks
        .map(chunk => `[${chunk.source}]\n${chunk.content}`)
        .join('\n\n---\n\n');

    // Step 3: Send to YOUR Gemini API
    const geminiResponse = await fetch('https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer YOUR_GEMINI_API_KEY`
        },
        body: JSON.stringify({
            contents: [{
                parts: [{
                    text: `Context:\n${context}\n\nQuestion: ${question}\n\nAnswer:`
                }]
            }]
        })
    });

    const result = await geminiResponse.json();
    return result.candidates[0].content.parts[0].text;
}

// Example usage
getAIResponse("How do I configure IAM policies?")
    .then(answer => console.log(answer))
    .catch(error => console.error(error));
```

---

### React/Frontend Integration

```javascript
import { useState } from 'react';

function RAGChat() {
    const [query, setQuery] = useState('');
    const [response, setResponse] = useState('');
    const [loading, setLoading] = useState(false);

    const handleQuery = async () => {
        setLoading(true);

        try {
            // Call RAG API
            const ragResponse = await fetch('http://localhost:5000/api/retrieve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: query,
                    top_k: 5
                })
            });

            const data = await ragResponse.json();
            const chunks = data.chunks;

            // Format context
            const context = chunks
                .map(c => c.content)
                .join('\n\n');

            // Send to YOUR Gemini AI (or any LLM)
            const aiResponse = await callYourGeminiAPI(context, query);
            setResponse(aiResponse);

        } catch (error) {
            console.error('Error:', error);
            setResponse('Error: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask about AWS..."
            />
            <button onClick={handleQuery} disabled={loading}>
                {loading ? 'Processing...' : 'Ask'}
            </button>
            <div>{response}</div>
        </div>
    );
}
```

---

### cURL Testing

```bash
# Test if RAG API is running
curl http://localhost:5000/api/health

# Get chunks for a query
curl -X POST http://localhost:5000/api/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are EKS best practices?",
    "top_k": 5
  }'

# Get system stats
curl http://localhost:5000/api/stats
```

---

## 📊 What Data You Get

### Chunk Object Structure

Each chunk contains:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique chunk identifier |
| `content` | string | Full text content of the chunk |
| `similarity` | float | Relevance score (0-1, higher = more relevant) |
| `source` | string | Source PDF filename |
| `centroid_info` | string | Category (e.g., "aws/services") |
| `metadata.source` | string | Document name |
| `metadata.page` | int | Page number in original PDF |
| `metadata.chunk_index` | int | Chunk position in document |
| `metadata.file_path` | string | Full file path |

---

## 🔄 Typical Workflow in Your Other Project

```
1. Your App receives user query
       ↓
2. Call RAG API (localhost:5000/api/retrieve)
       ↓
3. Receive chunks (relevant document excerpts)
       ↓
4. Format chunks as context
       ↓
5. Send context + query to YOUR Gemini AI
       ↓
6. Receive AI-generated answer
       ↓
7. Display to user
```

---

## 🎯 Sample Use Case: Agentic AI Project

```python
# In your Agentic AI project

import requests
import google.generativeai as genai

class RAGAgent:
    def __init__(self, gemini_api_key):
        self.rag_url = "http://localhost:5000/api/retrieve"
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def get_context(self, query, num_chunks=6):
        """Retrieve relevant chunks from RAG"""
        response = requests.post(
            self.rag_url,
            json={'query': query, 'top_k': num_chunks}
        )
        return response.json()['chunks']

    def generate_answer(self, query, chunks):
        """Generate answer using Gemini with RAG context"""
        context = "\n\n".join([
            f"[{c['source']}] {c['content']}"
            for c in chunks
        ])

        prompt = f"""You are an AWS expert assistant. Answer based on the context below.

Context:
{context}

Question: {query}

Provide a detailed answer with sources:"""

        response = self.model.generate_content(prompt)
        return response.text

    def ask(self, query):
        """Complete RAG + LLM pipeline"""
        # Step 1: Get chunks from RAG
        chunks = self.get_context(query)

        # Step 2: Generate answer with your Gemini
        answer = self.generate_answer(query, chunks)

        return {
            'answer': answer,
            'sources': [c['source'] for c in chunks],
            'num_sources': len(chunks)
        }

# Usage
agent = RAGAgent(gemini_api_key="YOUR_KEY")
result = agent.ask("How do I implement AWS security best practices?")
print(result['answer'])
print(f"Sources: {result['sources']}")
```

---

## ⚠️ Important Notes

### 1. Keep RAG Server Running
- The RAG API must be running (`python api.py`) in one terminal
- Your other project runs in a separate terminal/VS Code window
- Both can run simultaneously on localhost

### 2. Port Configuration
- **RAG API**: Always runs on port `5000`
- **Your Project**: Can run on any other port (3000, 8080, etc.)
- No port conflicts!

### 3. Network Requirements
- Both projects must be on the same machine (localhost)
- Or configure RAG API to listen on network IP for remote access

### 4. Performance
- First query: ~2-5 seconds (model initialization)
- Subsequent queries: ~1-3 seconds (cached)
- Concurrent requests: Supported

---

## 🐛 Troubleshooting

### Issue: "Connection refused"
**Solution**: Make sure RAG API is running:
```bash
python api.py
```

### Issue: CORS errors
**Solution**: Already configured! If issues persist:
```python
# In api.py, line 19-28
CORS(app, resources={r"/api/*": {"origins": "*"}})
```

### Issue: "Module not found"
**Solution**: Install dependencies:
```bash
pip install Flask Flask-CORS
```

### Issue: Slow responses
**Solution**:
- Reduce `top_k` (fewer chunks = faster)
- First query is always slower
- Use caching (automatic)

---

## 📦 Complete Integration Template

Save this in your other project:

```python
"""
RAG Integration Module
Place this file in your agentic AI project
"""

import requests
from typing import List, Dict

class RAGClient:
    def __init__(self, rag_url="http://localhost:5000"):
        self.rag_url = rag_url
        self.retrieve_endpoint = f"{rag_url}/api/retrieve"
        self.health_endpoint = f"{rag_url}/api/health"

    def check_health(self) -> bool:
        """Check if RAG API is running"""
        try:
            response = requests.get(self.health_endpoint, timeout=5)
            return response.status_code == 200
        except:
            return False

    def retrieve_chunks(self, query: str, top_k: int = 6) -> List[Dict]:
        """
        Retrieve relevant document chunks

        Args:
            query: User's question
            top_k: Number of chunks to retrieve (1-20)

        Returns:
            List of chunk dictionaries with content, similarity, source, etc.
        """
        if not self.check_health():
            raise ConnectionError("RAG API is not running. Start it with: python api.py")

        response = requests.post(
            self.retrieve_endpoint,
            json={'query': query, 'top_k': top_k},
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        if response.status_code != 200:
            error_msg = response.json().get('error', 'Unknown error')
            raise Exception(f"RAG API Error: {error_msg}")

        data = response.json()
        return data['chunks']

    def format_context(self, chunks: List[Dict], include_sources: bool = True) -> str:
        """Format chunks into context string for LLM"""
        if include_sources:
            return "\n\n---\n\n".join([
                f"[Source: {chunk['source']} - Similarity: {chunk['similarity']:.2f}]\n{chunk['content']}"
                for chunk in chunks
            ])
        else:
            return "\n\n".join([chunk['content'] for chunk in chunks])

# Usage in your project
if __name__ == "__main__":
    rag = RAGClient()

    # Check connection
    if rag.check_health():
        print("✅ RAG API is running")
    else:
        print("❌ RAG API is not running. Start it with: python api.py")
        exit(1)

    # Get chunks
    chunks = rag.retrieve_chunks("What are IAM best practices?", top_k=5)
    context = rag.format_context(chunks)

    print(f"Retrieved {len(chunks)} chunks")
    print(f"\nContext length: {len(context)} characters")
    print(f"\nSources: {[c['source'] for c in chunks]}")

    # Now send 'context' to your Gemini AI
```

---

## ✅ Checklist for Integration

- [ ] RAG API is running (`python api.py`)
- [ ] Can access `http://localhost:5000/api/health`
- [ ] Installed requests library in your project (`pip install requests`)
- [ ] Copied integration code to your project
- [ ] Tested chunk retrieval
- [ ] Integrated with your Gemini AI
- [ ] Handling errors gracefully

---

## 🎉 You're Ready!

Your RAG system is now a **plug-and-play microservice** that any project can use. Just keep the API running and call it whenever you need document chunks!

**Questions?** Check the logs where `python api.py` is running for debugging information.
