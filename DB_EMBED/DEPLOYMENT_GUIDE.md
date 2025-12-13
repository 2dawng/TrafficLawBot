# 🚀 Deployment Guide: Best Options for Multi-User Vietnamese Legal Search

## 🏆 Recommended: Qdrant Cloud + API Server

This is the **best option for other computers to use** your system.

### Architecture:
```
[User Computer 1] ──┐
[User Computer 2] ──┼─→ [Your API Server] ──→ [Qdrant Cloud]
[User Computer 3] ──┘    (FastAPI/Flask)      (Free Tier)
```

### Why This is Best:
1. ✅ **Other computers** can access via HTTP API
2. ✅ **No installation** needed on client computers (just web browser)
3. ✅ **Scalable** - handles multiple users
4. ✅ **Fast** - Qdrant Cloud is optimized
5. ✅ **Free** - up to 1GB (50,000+ documents)
6. ✅ **Always online** - no need to keep your computer running

---

## 📊 Performance Comparison

| Solution | Latency | Multi-User | Setup | Cost | Best For |
|----------|---------|------------|-------|------|----------|
| **Qdrant Cloud + API** | 50-100ms | ✅ Excellent | Easy | Free | **Production** |
| Docker (Local) | 5-20ms | ⚠️ Limited | Medium | Free | Internal team |
| Docker (VPS) | 20-50ms | ✅ Good | Hard | $5-20/mo | Self-hosted |
| Local files only | N/A | ❌ None | Easy | Free | Testing only |

---

## 🚀 Step-by-Step: Deploy for Multi-User

### Phase 1: Set Up Qdrant Cloud (5 minutes)

1. **Sign up**: https://cloud.qdrant.io/
2. **Create cluster** (free tier)
3. **Copy your URL**: `https://xyz-abc.aws.cloud.qdrant.io:6333`
4. **Copy API key** (if required)

### Phase 2: Embed Your Documents (10 minutes)

Update `embed_content_to_qdrant.py`:

```python
# Line 316 - Update with your Qdrant Cloud URL
embedder = ContentEmbedder(
    qdrant_url="https://YOUR-CLUSTER-URL.aws.cloud.qdrant.io:6333",  # Your URL here
    collection_name="vietnamese_legal_content",
    embedding_model="keepitreal/vietnamese-sbert",
)
```

Run once to embed all documents:
```powershell
python embed_content_to_qdrant.py
```

This uploads all your documents to Qdrant Cloud (one-time process).

### Phase 3: Create API Server (15 minutes)

This lets other computers search your data via HTTP.

**File: `api_server.py`**
```python
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import uvicorn

app = FastAPI(
    title="Vietnamese Legal Search API",
    description="Semantic search for Vietnamese legal documents",
    version="1.0.0"
)

# Enable CORS (allows access from other computers/websites)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
QDRANT_URL = "https://YOUR-CLUSTER-URL.aws.cloud.qdrant.io:6333"
COLLECTION_NAME = "vietnamese_legal_content"

client = QdrantClient(url=QDRANT_URL)
encoder = SentenceTransformer("keepitreal/vietnamese-sbert")

@app.get("/")
def home():
    """API home page"""
    return {
        "name": "Vietnamese Legal Search API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/search?query=YOUR_QUERY",
            "stats": "/stats",
            "health": "/health"
        }
    }

@app.get("/health")
def health_check():
    """Check if API is working"""
    try:
        info = client.get_collection(collection_name=COLLECTION_NAME)
        return {
            "status": "healthy",
            "qdrant": "connected",
            "total_documents": info.points_count
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.get("/stats")
def get_statistics():
    """Get collection statistics"""
    try:
        info = client.get_collection(collection_name=COLLECTION_NAME)
        return {
            "total_documents": info.points_count,
            "vector_size": info.config.params.vectors.size,
            "collection_name": COLLECTION_NAME
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
def search_documents(
    query: str = Query(..., description="Search query in Vietnamese", min_length=2),
    limit: int = Query(5, ge=1, le=50, description="Number of results"),
    min_content_length: int = Query(100, ge=0, description="Minimum content length")
):
    """
    Search Vietnamese legal documents
    
    Example: /search?query=Chạy xe máy buông tay múa quạt&limit=5
    """
    try:
        # Generate query embedding
        query_vector = encoder.encode(query).tolist()
        
        # Build filter for content length
        from qdrant_client.models import Filter, FieldCondition, Range
        
        query_filter = None
        if min_content_length > 0:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="content_length",
                        range=Range(gte=min_content_length),
                    )
                ]
            )
        
        # Search
        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter,
        )
        
        # Format results
        formatted_results = []
        for result in results:
            doc = result.payload
            formatted_results.append({
                "score": float(result.score),
                "title": doc.get("title", ""),
                "url": doc.get("url", ""),
                "content_preview": doc.get("content", "")[:300] + "...",
                "content_length": doc.get("content_length", 0),
                "document_type": doc.get("document_type", ""),
            })
        
        return {
            "query": query,
            "total_results": len(formatted_results),
            "results": formatted_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Starting Vietnamese Legal Search API Server")
    print("=" * 70)
    print(f"\n📍 API will be available at:")
    print(f"   - Local: http://localhost:8000")
    print(f"   - Network: http://YOUR-IP-ADDRESS:8000")
    print(f"\n📚 Documentation: http://localhost:8000/docs")
    print(f"\n🔍 Example: http://localhost:8000/search?query=Giấy phép lái xe")
    print("\n" + "=" * 70)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Install FastAPI:
```powershell
pip install fastapi uvicorn
```

Run the API server:
```powershell
python api_server.py
```

Now your API is accessible at:
- **Your computer**: `http://localhost:8000`
- **Other computers on network**: `http://YOUR-LOCAL-IP:8000`
- **Internet** (if you deploy to cloud): `http://YOUR-SERVER-IP:8000`

### Phase 4: Create Web Interface for Users

**File: `search_web_app.html`**
```html
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tìm kiếm Văn bản Pháp luật Việt Nam</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            text-align: center;
            font-size: 2.2em;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        input[type="text"] {
            flex: 1;
            padding: 15px 20px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 10px;
            outline: none;
            transition: all 0.3s;
        }
        input[type="text"]:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        button {
            padding: 15px 35px;
            font-size: 16px;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        button:active {
            transform: translateY(0);
        }
        .stats {
            text-align: center;
            color: #666;
            margin-bottom: 20px;
            font-size: 0.95em;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #667eea;
            display: none;
            font-size: 1.1em;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .result {
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            padding: 25px;
            margin: 20px 0;
            border-radius: 12px;
            border-left: 5px solid #667eea;
            transition: all 0.3s;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .result:hover {
            transform: translateX(5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .result-number {
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }
        .score {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }
        .title {
            font-size: 1.25em;
            font-weight: bold;
            color: #333;
            margin-bottom: 12px;
            line-height: 1.4;
        }
        .content {
            color: #555;
            line-height: 1.8;
            margin-bottom: 15px;
            text-align: justify;
        }
        .meta {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }
        .meta-item {
            background: #e9ecef;
            padding: 5px 12px;
            border-radius: 5px;
            font-size: 0.85em;
            color: #666;
        }
        .url-link {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s;
        }
        .url-link:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        .no-results {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }
        .no-results-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
        .error {
            background: #fff3cd;
            border-left: 5px solid #ffc107;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
        .examples {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        .examples h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.1em;
        }
        .example-tag {
            display: inline-block;
            background: white;
            padding: 8px 15px;
            margin: 5px;
            border-radius: 20px;
            cursor: pointer;
            border: 2px solid #ddd;
            transition: all 0.3s;
        }
        .example-tag:hover {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Tìm kiếm Văn bản Pháp luật</h1>
        <p class="subtitle">Hệ thống tìm kiếm thông minh văn bản pháp luật Việt Nam</p>
        
        <div class="examples">
            <h3>💡 Ví dụ tìm kiếm:</h3>
            <span class="example-tag" onclick="searchExample('Chạy xe máy buông tay múa quạt xử phạt thế nào')">
                Chạy xe máy buông tay múa quạt
            </span>
            <span class="example-tag" onclick="searchExample('Giấy phép lái xe bị tước')">
                Tước bằng lái xe
            </span>
            <span class="example-tag" onclick="searchExample('Vi phạm giao thông đường bộ')">
                Vi phạm giao thông
            </span>
            <span class="example-tag" onclick="searchExample('Đăng ký xe cơ giới')">
                Đăng ký xe
            </span>
            <span class="example-tag" onclick="searchExample('Luật giao thông 2025')">
                Luật mới 2025
            </span>
        </div>
        
        <div class="search-box">
            <input 
                type="text" 
                id="query" 
                placeholder="Nhập câu hỏi hoặc từ khóa tìm kiếm..."
                onkeypress="if(event.key === 'Enter') search()"
                autocomplete="off"
            />
            <button onclick="search()">🔍 Tìm kiếm</button>
        </div>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Đang tìm kiếm...</p>
        </div>

        <div class="stats" id="stats"></div>
        <div id="results"></div>
    </div>

    <script>
        // ⚠️ CHANGE THIS to your API server URL
        const API_URL = "http://localhost:8000";  // Change if API is on different computer
        
        function searchExample(query) {
            document.getElementById('query').value = query;
            search();
        }
        
        async function search() {
            const query = document.getElementById('query').value.trim();
            if (!query) {
                alert('⚠️ Vui lòng nhập từ khóa tìm kiếm');
                return;
            }

            const loading = document.getElementById('loading');
            const results = document.getElementById('results');
            const stats = document.getElementById('stats');
            
            loading.style.display = 'block';
            results.innerHTML = '';
            stats.innerHTML = '';

            try {
                const response = await fetch(
                    `${API_URL}/search?query=${encodeURIComponent(query)}&limit=10&min_content_length=100`
                );
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const data = await response.json();
                loading.style.display = 'none';
                
                if (data.results && data.results.length > 0) {
                    stats.innerHTML = `✅ Tìm thấy <strong>${data.total_results}</strong> kết quả phù hợp cho "<strong>${escapeHtml(query)}</strong>"`;
                    
                    data.results.forEach((result, i) => {
                        const div = document.createElement('div');
                        div.className = 'result';
                        
                        const score = (result.score * 100).toFixed(1);
                        const title = result.title || 'Không có tiêu đề';
                        const content = result.content_preview || 'Không có nội dung';
                        const url = result.url || '#';
                        const contentLength = result.content_length || 0;
                        const docType = result.document_type || 'N/A';
                        
                        div.innerHTML = `
                            <div class="result-header">
                                <span class="result-number">#${i + 1}</span>
                                <span class="score">Độ phù hợp: ${score}%</span>
                            </div>
                            <div class="title">${escapeHtml(title)}</div>
                            <div class="meta">
                                <span class="meta-item">📄 ${escapeHtml(docType)}</span>
                                <span class="meta-item">📝 ${contentLength.toLocaleString()} ký tự</span>
                            </div>
                            <div class="content">${escapeHtml(content)}</div>
                            <a href="${escapeHtml(url)}" target="_blank" class="url-link">
                                📖 Xem chi tiết đầy đủ →
                            </a>
                        `;
                        
                        results.appendChild(div);
                    });
                } else {
                    results.innerHTML = `
                        <div class="no-results">
                            <div class="no-results-icon">🔍</div>
                            <h3>Không tìm thấy kết quả</h3>
                            <p>Vui lòng thử với từ khóa khác</p>
                        </div>
                    `;
                }
            } catch (error) {
                loading.style.display = 'none';
                results.innerHTML = `
                    <div class="error">
                        <h3>⚠️ Lỗi kết nối</h3>
                        <p><strong>Chi tiết:</strong> ${escapeHtml(error.message)}</p>
                        <p><strong>Giải pháp:</strong></p>
                        <ul>
                            <li>Đảm bảo API server đang chạy tại: ${API_URL}</li>
                            <li>Kiểm tra kết nối mạng</li>
                            <li>Cập nhật API_URL trong code nếu server ở máy khác</li>
                        </ul>
                    </div>
                `;
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Auto-focus search box
        document.getElementById('query').focus();
    </script>
</body>
</html>
```

**Users can open this HTML file in any browser** (Chrome, Edge, Firefox).

---

## 🌐 Deployment Options

### Option A: Local Network (Free)

Best for: Office/home network

1. Run API server on your computer
2. Share your local IP: `http://192.168.1.XXX:8000`
3. Others on same network can access

**Pros:** Free, fast, simple
**Cons:** Your computer must stay on

### Option B: Cloud Server ($5-10/month)

Best for: Internet access, always online

**Services:**
- **DigitalOcean** ($6/mo) - Easiest
- **AWS EC2** (Free tier 1 year)
- **Google Cloud** (Free tier)
- **Heroku** (Has free tier)

**Steps:**
1. Create a server (Ubuntu 22.04)
2. Install Python + your code
3. Run API server
4. Access from anywhere: `http://YOUR-SERVER-IP:8000`

### Option C: ngrok (Free - Quick Test)

Best for: Temporary sharing, testing

```powershell
# Install ngrok
choco install ngrok

# Run your API server first
python api_server.py

# In another terminal, expose to internet
ngrok http 8000
```

You get a public URL like: `https://abc123.ngrok.io`

**Pros:** Instant public access
**Cons:** URL changes each time (unless paid plan)

---

## 📈 Performance Optimization Tips

### 1. **Caching** (for faster repeated searches)

Add to `api_server.py`:
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def search_cached(query: str, limit: int):
    # Your search code
    pass
```

### 2. **Batch API requests**

If multiple users search simultaneously, Qdrant handles it well (no changes needed).

### 3. **CDN for Web UI**

Host `search_web_app.html` on:
- GitHub Pages (free)
- Netlify (free)
- Vercel (free)

### 4. **Load Balancing** (for very high traffic)

Use multiple API servers behind nginx.

---

## 💰 Cost Breakdown

| Component | Free Option | Paid Option |
|-----------|-------------|-------------|
| Qdrant | Qdrant Cloud (1GB) | Qdrant Cloud ($25/mo for 8GB) |
| API Server | Your computer | DigitalOcean ($6/mo) |
| Web UI | GitHub Pages | Netlify Pro ($19/mo) |
| **Total** | **$0** | **$31/mo** |

**Recommendation:** Start with 100% free (Qdrant Cloud + local API server)

---

## 🎯 Quick Start Commands

```powershell
# 1. Update embed_content_to_qdrant.py with Qdrant Cloud URL

# 2. Embed documents (one-time)
python embed_content_to_qdrant.py

# 3. Install API requirements
pip install fastapi uvicorn

# 4. Start API server
python api_server.py

# 5. Open search_web_app.html in browser
# Or visit: http://localhost:8000/docs
```

---

## ✅ Final Recommendation

For **best performance + multi-user access**:

1. ✅ **Qdrant Cloud** (free) - for vector storage
2. ✅ **FastAPI server** - on your computer initially
3. ✅ **Web HTML interface** - users access via browser
4. ✅ Upgrade to **cloud server** ($6/mo) when ready for 24/7 access

This gives you:
- **Fast search**: 50-100ms
- **Multiple users**: Concurrent access
- **No installation**: Users just need browser
- **Free to start**: Only pay if you need 24/7 uptime

---

Need help setting up? Let me know which option you prefer! 🚀
