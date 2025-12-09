# TrafficLawBot - Complete Setup Guide

## Quick Start

### 1. Start Services
```powershell
# Start Docker Desktop (if not running)
# Wait for Docker to be ready

# Start Qdrant
docker start qdrant
# OR create new: docker run -d --name qdrant -p 6333:6333 -v D:/qdrant_traffic_laws:/qdrant/storage qdrant/qdrant

# Start MySQL (if using)
Start-Service MySQL80
```

### 2. Start Backend
```powershell
cd "D:\Simple Crawl TVPL\TrafficLawBot\BE"
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend API: http://localhost:8000

### 3. Start Frontend (optional)
```powershell
cd "D:\Simple Crawl TVPL\TrafficLawBot\FE"
npm run dev
```

Frontend: http://localhost:5173

---

## Vector Database Management

### Test Qdrant Collection
```powershell
cd "D:\Simple Crawl TVPL"
.\venv\Scripts\python.exe test_traffic_laws.py
```

### Re-embed Data (if needed)
```powershell
cd "D:\Simple Crawl TVPL"

# Delete old collection
.\venv\Scripts\python.exe -c "from qdrant_client import QdrantClient; c = QdrantClient(host='localhost', port=6333); c.delete_collection('traffic_laws_only')"

# Clear tracking files
Remove-Item processed_traffic_files.txt, traffic_laws_backup.jsonl, traffic_laws_embedding.log -ErrorAction SilentlyContinue

# Re-embed (takes ~3-5 minutes for 483 unique documents)
.\venv\Scripts\python.exe embed_traffic_laws_v2.py
```

### Check Collection Stats
```powershell
.\venv\Scripts\python.exe -c "from qdrant_client import QdrantClient; c = QdrantClient(host='localhost', port=6333); info = c.get_collection('traffic_laws_only'); print(f'Documents: {info.points_count}')"
```

---

## Key Features

### Deduplication
- ✅ **Global deduplication** across all 2,293 scraped folders
- ✅ Tracks already-embedded URLs in `traffic_laws_backup.jsonl`
- ✅ Result: **483 unique traffic law documents** (no duplicates)

### RAG Integration
- Backend automatically searches Qdrant for relevant documents
- Top 3 most relevant docs added as context to LLM
- Content truncated to 2000 chars per document in vector DB
- Fast searches (< 0.3 seconds)

### Data Sources
- URL Filter: `https://thuvienphapluat.vn/van-ban/Giao-thong-Van-tai/`
- 2,293 scraped folders in `traffic_laws_WITH_CONTENT_*`
- Embedded using Vietnamese SBERT model (keepitreal/vietnamese-sbert)
- GPU-accelerated (RTX 3060 Laptop)

---

## File Structure

```
D:\Simple Crawl TVPL\
├── venv/                           # Shared Python environment
├── embed_traffic_laws_v2.py        # Embedding script with global deduplication
├── test_traffic_laws.py            # Test vector search
├── processed_traffic_files.txt     # Tracking: which folders processed
├── traffic_laws_backup.jsonl       # Backup: all embedded URLs
├── traffic_laws_embedding.log      # Embedding logs
├── traffic_laws_WITH_CONTENT_*/    # 2,293 scraped data folders
│
└── TrafficLawBot/
    ├── BE/
    │   ├── venv/                   # Backend environment
    │   ├── main.py                 # FastAPI entry point
    │   ├── chat.py                 # Chat endpoints (RAG-enabled)
    │   ├── qdrant_search.py        # Qdrant integration
    │   ├── test_qdrant_integration.py  # Test backend search
    │   ├── .env                    # Config (MySQL, Groq API, etc.)
    │   └── requirements.txt
    │
    └── FE/                         # Frontend (React/Vue)
```

---

## Troubleshooting

### Qdrant Crashes / 500 Errors
```powershell
# Restart Qdrant
docker restart qdrant

# If still broken, delete and re-embed
docker stop qdrant
Remove-Item -Recurse D:\qdrant_traffic_laws\*
docker start qdrant
cd "D:\Simple Crawl TVPL"
.\venv\Scripts\python.exe embed_traffic_laws_v2.py
```

### Backend venv Issues
```powershell
cd "D:\Simple Crawl TVPL\TrafficLawBot\BE"
Remove-Item -Recurse venv
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### GPU Not Detected
```powershell
# Check CUDA
.\venv\Scripts\python.exe -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}')"
```

---

## API Endpoints

### Chat (RAG-enabled)
```bash
POST http://localhost:8000/chat/
Headers:
  Authorization: Bearer <JWT_TOKEN>
Body:
  {
    "message": "Phạt nồng độ cồn bao nhiêu?",
    "session_id": 123
  }
```

### Test Direct Search
```powershell
cd "D:\Simple Crawl TVPL\TrafficLawBot\BE"
.\venv\Scripts\python.exe test_qdrant_integration.py
```

---

## Performance

- **Embedding**: 483 docs in ~3-5 minutes (GPU-accelerated)
- **Search**: < 0.3 seconds per query
- **Deduplication**: Automatic (global URL tracking)
- **Storage**: ~50MB for 483 documents with 2000-char content excerpts
- **Memory**: ~2-3GB RAM, 2-3GB VRAM during search

---

## Configuration

### Backend (.env)
```env
# Qdrant (default)
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=traffic_laws_only

# Database
DATABASE_URL=mysql+aiomysql://root:password@localhost:3306/trafficlawbot

# Groq AI
GROQ_API_KEY=your_key_here
```

### Embedding (embed_traffic_laws_v2.py)
```python
URL_PREFIX = "https://thuvienphapluat.vn/van-ban/Giao-thong-Van-tai/"
COLLECTION_NAME = "traffic_laws_only"
BATCH_SIZE = 64  # GPU batch size
CONTENT_EXCERPT_LENGTH = 2000  # Chars stored per doc
```

---

## Next Steps

1. ✅ Start all services (Docker, Qdrant, MySQL, Backend)
2. ✅ Verify vector search works (`test_traffic_laws.py`)
3. ✅ Test backend integration (`test_qdrant_integration.py`)
4. 🔄 Start backend server (`uvicorn main:app --reload`)
5. 🔄 Test chat endpoint with RAG
6. 🔄 Start frontend
7. ✅ Enjoy your traffic law chatbot!
