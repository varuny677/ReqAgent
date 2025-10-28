# RAG API & Chatbot Documentation

## Overview

This project now includes a REST API for retrieving document chunks and a web-based chatbot interface for testing the RAG system.

## What's New

### 1. Chunk-Only Retrieval
- **New Method**: `retrieve_chunks_only()` in `RAG.py`
- Returns relevant document chunks WITHOUT LLM generation
- Perfect for integrating RAG into your own applications

### 2. Flask REST API (`api.py`)
- RESTful API with CORS support
- Endpoints for chunk retrieval and system statistics
- Easy integration with any frontend or application

### 3. Web Chatbot Interface (`chatbot.html`)
- Beautiful, responsive chat interface
- Real-time chunk retrieval and display
- Shows similarity scores and source information

---

## Quick Start

### Start the API Server

```bash
python api.py
```

The API will start on: **http://localhost:5000**

### Open the Chatbot

Simply open `chatbot.html` in your web browser:

```bash
# Windows
start chatbot.html

# Mac/Linux
open chatbot.html
```

---

## API Endpoints

### 1. Health Check
**Endpoint**: `GET /api/health`

**Response**:
```json
{
  "status": "healthy",
  "message": "RAG API is running"
}
```

### 2. Retrieve Chunks
**Endpoint**: `POST /api/retrieve`

**Request Body**:
```json
{
  "query": "What are AWS EKS best practices?",
  "top_k": 6
}
```

**Response**:
```json
{
  "query": "What are AWS EKS best practices?",
  "chunks": [
    {
      "id": "chunk_123",
      "content": "Document chunk content...",
      "metadata": {
        "source": "eks-bpg.pdf",
        "page": 42
      },
      "similarity": 0.8523,
      "source": "eks-bpg.pdf",
      "centroid_info": "aws/services"
    }
  ],
  "total_chunks": 6,
  "routing_info": {
    "centroids_evaluated": 12,
    "centroids_selected": 1,
    "adaptive_window": 6
  },
  "performance": {
    "total_time": 2.145,
    "chunks_returned": 6
  }
}
```

### 3. System Statistics
**Endpoint**: `GET /api/stats`

**Response**: Database statistics including collection counts and chunk totals

---

## Integration Examples

### JavaScript/Fetch API

```javascript
async function queryRAG(question) {
    const response = await fetch('http://localhost:5000/api/retrieve', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            query: question,
            top_k: 6
        })
    });

    const data = await response.json();
    return data.chunks;
}

// Usage
const chunks = await queryRAG("How do I secure EC2 instances?");
console.log(chunks);
```

### Python/Requests

```python
import requests

def query_rag(question, top_k=6):
    response = requests.post(
        'http://localhost:5000/api/retrieve',
        json={
            'query': question,
            'top_k': top_k
        }
    )
    return response.json()

# Usage
result = query_rag("What are IAM best practices?")
for chunk in result['chunks']:
    print(f"Source: {chunk['source']}")
    print(f"Similarity: {chunk['similarity']:.2f}")
    print(f"Content: {chunk['content'][:200]}...")
    print("---")
```

### cURL

```bash
curl -X POST http://localhost:5000/api/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are AWS compliance requirements?",
    "top_k": 5
  }'
```

---

## CORS Configuration

The API is configured with CORS to allow:
- **Origins**: All origins (for development)
- **Methods**: GET, POST, OPTIONS
- **Headers**: Content-Type, Authorization

For production, modify the CORS settings in `api.py`:

```python
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://yourdomain.com"],  # Restrict to your domain
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})
```

---

## Chatbot Features

### Visual Features
- 🎨 Modern gradient design
- 💬 Real-time message streaming
- 📊 Chunk similarity scores
- 📁 Source document indicators
- ⚡ Typing indicators
- 📱 Responsive design

### Functionality
- Retrieves relevant document chunks
- Displays similarity scores
- Shows source documents
- Performance metrics
- Error handling

### Customization

Edit `chatbot.html` to customize:
- **Colors**: Modify CSS gradient values
- **API URL**: Change `API_URL` constant
- **Chunks displayed**: Modify `top_k` parameter
- **UI text**: Update HTML content

---

## Use Cases

### 1. Build Your Own Frontend
Use the API to build custom interfaces:
- React/Vue/Angular applications
- Mobile apps
- Desktop applications
- Slack/Discord bots

### 2. Integrate with Existing Systems
Add RAG capabilities to:
- Customer support systems
- Documentation portals
- Internal knowledge bases
- Chatbots and virtual assistants

### 3. Process Retrieved Chunks
Use chunks for:
- Custom LLM prompts (send to OpenAI, Anthropic, etc.)
- Document summarization
- Citation generation
- Semantic search results

---

## Example: Custom LLM Integration

```python
import requests
import openai

def rag_with_custom_llm(question):
    # Step 1: Retrieve chunks from RAG
    chunks_response = requests.post(
        'http://localhost:5000/api/retrieve',
        json={'query': question, 'top_k': 6}
    )
    chunks = chunks_response.json()['chunks']

    # Step 2: Format context
    context = "\n\n".join([
        f"[Source: {c['source']}]\n{c['content']}"
        for c in chunks
    ])

    # Step 3: Send to your preferred LLM
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Answer based on the provided context."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ]
    )

    return response.choices[0].message.content

# Usage
answer = rag_with_custom_llm("What are AWS EKS scaling best practices?")
print(answer)
```

---

## Performance Notes

- **Average Response Time**: 2-7 seconds (including embedding generation)
- **Chunk Retrieval**: Uses centroid-based routing for fast retrieval
- **Caching**: Query results are cached for 5 minutes
- **Concurrent Requests**: Supports multiple simultaneous requests

---

## Troubleshooting

### API Won't Start
```bash
# Check if port 5000 is in use
netstat -ano | findstr :5000

# Kill the process using port 5000 (Windows)
taskkill /PID <PID> /F
```

### CORS Errors in Browser
- Make sure the API is running on `http://localhost:5000`
- Check browser console for specific CORS errors
- Verify CORS configuration in `api.py`

### Chatbot Not Connecting
1. Verify API is running: `curl http://localhost:5000/api/health`
2. Check browser console for errors
3. Ensure `chatbot.html` has correct `API_URL`

### Slow Response Times
- First query is slower (model initialization)
- Subsequent queries use caching
- Consider reducing `top_k` for faster responses

---

## File Structure

```
demorag-main/
├── api.py                 # Flask REST API
├── chatbot.html          # Web chatbot interface
├── RAG.py                # RAG system (with retrieve_chunks_only method)
├── main.py               # CLI interface
├── config.py             # Configuration
├── requirements.txt      # Dependencies (now includes Flask)
└── .env                  # API keys
```

---

## Next Steps

1. **Deploy the API**: Use Gunicorn/uWSGI for production
2. **Add Authentication**: Implement API keys or OAuth
3. **Rate Limiting**: Prevent abuse with rate limits
4. **Monitoring**: Add logging and monitoring
5. **Scale**: Deploy on cloud platforms (AWS, GCP, Azure)

---

## Support

For questions or issues:
1. Check the logs in the terminal where `api.py` is running
2. Inspect browser console for frontend errors
3. Test API directly with cURL/Postman
4. Review CORS configuration

Enjoy your RAG-powered chatbot! 🚀
