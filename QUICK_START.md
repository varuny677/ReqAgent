# ⚡ Quick Start Guide

## 🎯 What You Have

A **RAG API service** that retrieves relevant AWS document chunks. Use it from ANY project!

---

## 🚀 Start the API (Do This First!)

```bash
cd c:\Users\varun\Pictures\Agent1\demorag-main
python api.py
```

**API runs on**: `http://localhost:5000`

✅ Keep this terminal running!

---

## 📡 Use in Your Other Project

### 1️⃣ Open a NEW VS Code window for your other project

### 2️⃣ Copy this code to your project:

```python
import requests

# Get chunks from RAG
response = requests.post(
    'http://localhost:5000/api/retrieve',
    json={'query': 'What are IAM best practices?', 'top_k': 5}
)

chunks = response.json()['chunks']

# Use chunks however you want!
for chunk in chunks:
    print(f"📄 {chunk['source']}: {chunk['content'][:100]}...")
```

### 3️⃣ Send chunks to YOUR Gemini AI:

```python
import google.generativeai as genai

# Format context from chunks
context = "\n\n".join([c['content'] for c in chunks])

# Send to YOUR Gemini
genai.configure(api_key="YOUR_KEY")
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content(f"Context:\n{context}\n\nQuestion: your question")
print(response.text)
```

---

## 📋 API Endpoint

```
POST http://localhost:5000/api/retrieve
Content-Type: application/json

{
  "query": "your question",
  "top_k": 6
}
```

**Returns**: Array of document chunks with content, similarity scores, and metadata

---

## 📚 Files to Read

1. **RAG_INTEGRATION.md** - Complete integration guide with examples
2. **API_README.md** - Full API documentation
3. **SUMMARY.md** - System overview

---

## ✅ Quick Test

```bash
curl http://localhost:5000/api/health
```

Should return: `{"status": "healthy", "message": "RAG API is running"}`

---

## 🎯 Remember

- ✅ **RAG API**: Runs on port 5000 (this project)
- ✅ **Your Project**: Runs on any other port
- ✅ **CORS**: Already enabled for all origins
- ✅ **Data**: 30,608 AWS document chunks ready
- ✅ **LLM**: Use YOUR Gemini AI in your project
- ✅ **Chunks**: Sent from RAG → Your project → Your Gemini

---

## 🔗 Integration Flow

```
Your Project → http://localhost:5000/api/retrieve → Get Chunks → Send to Your Gemini → Get Answer
```

That's it! 🎉
