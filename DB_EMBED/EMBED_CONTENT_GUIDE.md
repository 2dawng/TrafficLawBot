# 🚀 Embedding Documents WITH CONTENT to Qdrant

## What This Does

This guide shows you how to embed your **scraped Vietnamese legal documents with full content** into Qdrant vector database for semantic search.

Your documents look like this:
```json
{
  "url": "https://thuvienphapluat.vn/...",
  "title": "Chạy xe máy buông hai tay để múa quạt...",
  "type": "",
  "number": "điện thoại liên hệ: 028 3930 3279",
  "date": "09/05/2019",
  "status": "",
  "content": "Beginning of dialog window...",
  "content_length": 1029,
  "document_type": "Văn bản PL"
}
```

The script will:
- ✅ Load JSON files from `traffic_laws_WITH_CONTENT_*` folders
- ✅ Skip documents with empty content
- ✅ **Ignore** `date` and `number` fields (as requested)
- ✅ Embed `title` + `content` for better search
- ✅ Store in Qdrant for semantic search

---

## 📦 Installation

### Step 1: Start Qdrant Server

**Option A: Docker (Recommended)**
```powershell
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

**Option B: Qdrant Cloud (Free)**
- Go to https://cloud.qdrant.io/
- Create free account
- Get cluster URL
- Update script with your URL

### Step 2: Install Python Packages

```powershell
# Activate virtual environment
& "C:/VSCODE/Simple Crawl TVPL/venv/Scripts/Activate.ps1"

# Install dependencies
pip install qdrant-client sentence-transformers torch
```

---

## 🚀 Quick Start

### Run the Embedder

```powershell
python embed_content_to_qdrant.py
```

This will:
1. Load all JSON files from `traffic_laws_WITH_CONTENT_*` folders
2. Filter out documents without content
3. Embed documents using Vietnamese language model
4. Upload to Qdrant
5. Run test searches

---

## 📊 What You'll See

```
======================================================================
🚀 Vietnamese Legal Documents Content Embedder
======================================================================
Loading embedding model: keepitreal/vietnamese-sbert
✅ Created collection: vietnamese_legal_content (vector size: 768)

📚 Loading documents from JSON files...

📁 Found 50 folders matching pattern: traffic_laws_WITH_CONTENT_*

📄 Loading: traffic_laws_WITH_CONTENT_20251106_221541\scraped_data_with_content.json

📊 Loading Statistics:
  - Total documents: 1500
  - With content: 1200
  - Empty content (skipped): 300
  - Loaded for embedding: 1200

🔄 Embedding 1200 documents...
Valid documents (non-empty): 1200
Processing batch 1/75...
Processing batch 2/75...
...

⬆️ Uploading 1200 points to Qdrant...
✅ Successfully uploaded 1200 documents to Qdrant!

📊 Collection Statistics:
  - Collection name: vietnamese_legal_content
  - Total documents: 1200
  - Vector size: 768
  - Distance metric: Cosine

🔍 Testing search functionality...
🔎 Query: 'Chạy xe máy buông tay múa quạt xử phạt thế nào'

  1. Score: 0.8534
     Title: Chạy xe máy buông hai tay để múa quạt...
     URL: https://thuvienphapluat.vn/...
     Content preview: Beginning of dialog window...
```

---

## 🔍 Using the Search

### Python Code

```python
from embed_content_to_qdrant import ContentEmbedder

# Initialize
embedder = ContentEmbedder(
    qdrant_url="http://localhost:6333",
    collection_name="vietnamese_legal_content"
)

# Search with natural language
results = embedder.search("Chạy xe máy buông tay múa quạt", limit=5)

# Search with minimum content length filter
results = embedder.search(
    "Giấy phép lái xe", 
    limit=10, 
    min_content_length=500  # Only docs with 500+ chars
)

# Print results
for i, result in enumerate(results, 1):
    doc = result["document"]
    print(f"{i}. Score: {result['score']:.4f}")
    print(f"   Title: {doc['title']}")
    print(f"   URL: {doc['url']}")
    print(f"   Content: {doc['content'][:200]}...")
    print()
```

### Example Queries

```python
# Vietnamese natural language queries
embedder.search("Xử phạt khi chạy xe múa quạt", limit=5)
embedder.search("Vi phạm giao thông bị tước bằng lái", limit=5)
embedder.search("Đăng ký xe cơ giới", limit=5)
embedder.search("Luật giao thông mới 2025", limit=5)
embedder.search("Giấy phép lái xe quốc tế", limit=5)
```

---

## ⚙️ Configuration

### Change Qdrant URL (for Cloud)

Edit `embed_content_to_qdrant.py`:

```python
embedder = ContentEmbedder(
    qdrant_url="https://xyz-123.qdrant.io",  # Your Qdrant Cloud URL
    collection_name="vietnamese_legal_content",
    embedding_model="keepitreal/vietnamese-sbert"
)
```

### Change Collection Name

```python
collection_name="my_legal_docs"  # Your custom name
```

### Adjust Batch Size (if low memory)

```python
embedder.embed_documents(documents, batch_size=8)  # Lower = less memory
```

### Change Embedding Model

```python
# Option 1: Vietnamese SBERT (Default - Best for Vietnamese)
embedding_model="keepitreal/vietnamese-sbert"

# Option 2: Multilingual E5
embedding_model="intfloat/multilingual-e5-base"

# Option 3: Vietnamese SimCSE
embedding_model="VoVanPhuc/sup-SimCSE-VietNamese-phobert-base"
```

### Adjust Content Truncation

In the `prepare_text_for_embedding` method:

```python
max_content_length = 8000  # Change this (default 8000 chars)
```

---

## 📂 Folder Structure Expected

```
traffic_laws_WITH_CONTENT_20251106_221541/
  ├── scraped_data_with_content.json  ✅ Will be loaded

traffic_laws_WITH_CONTENT_20251102_113715/
  ├── scraped_data_with_content.json  ✅ Will be loaded

traffic_laws_WITH_CONTENT_20251102_114005/
  ├── scraped_data_with_content.json  ✅ Will be loaded
```

The script looks for:
- Pattern: `traffic_laws_WITH_CONTENT_*`
- Files: `*.json` in those folders

---

## 🛠️ Advanced: Search API

Create a simple API to search your documents:

```python
# search_content_api.py
from fastapi import FastAPI, Query
from embed_content_to_qdrant import ContentEmbedder
import uvicorn

app = FastAPI(title="Vietnamese Legal Search API")

# Initialize embedder
embedder = ContentEmbedder(
    qdrant_url="http://localhost:6333",
    collection_name="vietnamese_legal_content"
)

@app.get("/search")
def search_documents(
    query: str = Query(..., description="Search query in Vietnamese"),
    limit: int = Query(5, ge=1, le=50, description="Number of results"),
    min_content: int = Query(0, ge=0, description="Minimum content length")
):
    """Search Vietnamese legal documents by content"""
    results = embedder.search(query, limit=limit, min_content_length=min_content)
    
    return {
        "query": query,
        "total_results": len(results),
        "results": [
            {
                "score": r["score"],
                "title": r["document"].get("title", ""),
                "url": r["document"].get("url", ""),
                "content_preview": r["document"].get("content", "")[:300] + "...",
                "content_length": r["document"].get("content_length", 0),
                "document_type": r["document"].get("document_type", "")
            }
            for r in results
        ]
    }

@app.get("/stats")
def get_stats():
    """Get collection statistics"""
    count = embedder.get_collection_stats()
    return {"total_documents": count}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Install and run:
```powershell
pip install fastapi uvicorn
python search_content_api.py
```

Access API at: http://localhost:8000/docs

Example requests:
```
http://localhost:8000/search?query=Chạy xe máy buông tay múa quạt&limit=5
http://localhost:8000/search?query=Giấy phép lái xe&limit=10&min_content=500
http://localhost:8000/stats
```

---

## 🎨 Web Interface

Create `search_web.html`:

```html
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tìm kiếm Văn bản Pháp luật</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
            text-align: center;
            font-size: 2em;
        }
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
        }
        input[type="text"] {
            flex: 1;
            padding: 15px;
            font-size: 16px;
            border: 2px solid #ddd;
            border-radius: 10px;
            outline: none;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus {
            border-color: #667eea;
        }
        button {
            padding: 15px 30px;
            font-size: 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        button:active {
            transform: translateY(0);
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: #667eea;
            display: none;
        }
        .result {
            background: #f8f9fa;
            padding: 20px;
            margin: 15px 0;
            border-radius: 10px;
            border-left: 5px solid #667eea;
            transition: transform 0.2s;
        }
        .result:hover {
            transform: translateX(5px);
        }
        .score {
            display: inline-block;
            background: #28a745;
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 0.9em;
            margin-bottom: 10px;
        }
        .title {
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        }
        .content {
            color: #666;
            line-height: 1.6;
            margin-bottom: 10px;
        }
        .url {
            color: #667eea;
            text-decoration: none;
            font-size: 0.9em;
        }
        .url:hover {
            text-decoration: underline;
        }
        .no-results {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        .stats {
            text-align: center;
            color: #666;
            margin-bottom: 20px;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Tìm kiếm Văn bản Pháp luật Việt Nam</h1>
        
        <div class="search-box">
            <input 
                type="text" 
                id="query" 
                placeholder="Nhập câu hỏi hoặc từ khóa (VD: Chạy xe máy buông tay múa quạt xử phạt thế nào?)"
                onkeypress="if(event.key === 'Enter') search()"
            />
            <button onclick="search()">Tìm kiếm</button>
        </div>

        <div class="loading" id="loading">
            <p>⏳ Đang tìm kiếm...</p>
        </div>

        <div class="stats" id="stats"></div>
        
        <div id="results"></div>
    </div>

    <script>
        async function search() {
            const query = document.getElementById('query').value;
            if (!query.trim()) {
                alert('Vui lòng nhập từ khóa tìm kiếm');
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
                    `http://localhost:8000/search?query=${encodeURIComponent(query)}&limit=10&min_content=100`
                );
                
                if (!response.ok) {
                    throw new Error('Lỗi kết nối API');
                }

                const data = await response.json();
                
                loading.style.display = 'none';
                
                if (data.results && data.results.length > 0) {
                    stats.innerHTML = `Tìm thấy ${data.total_results} kết quả phù hợp`;
                    
                    data.results.forEach((result, i) => {
                        const div = document.createElement('div');
                        div.className = 'result';
                        
                        const score = (result.score * 100).toFixed(1);
                        const title = result.title || 'Không có tiêu đề';
                        const content = result.content_preview || 'Không có nội dung';
                        const url = result.url || '#';
                        
                        div.innerHTML = `
                            <div class="score">Độ phù hợp: ${score}%</div>
                            <div class="title">${i + 1}. ${escapeHtml(title)}</div>
                            <div class="content">${escapeHtml(content)}</div>
                            <a href="${escapeHtml(url)}" target="_blank" class="url">
                                📄 Xem chi tiết →
                            </a>
                        `;
                        
                        results.appendChild(div);
                    });
                } else {
                    results.innerHTML = `
                        <div class="no-results">
                            ❌ Không tìm thấy kết quả phù hợp
                        </div>
                    `;
                }
            } catch (error) {
                loading.style.display = 'none';
                results.innerHTML = `
                    <div class="no-results">
                        ⚠️ Lỗi: ${error.message}
                        <br><br>
                        Vui lòng đảm bảo API đang chạy tại http://localhost:8000
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

Open `search_web.html` in your browser (make sure API is running first).

---

## 🐛 Troubleshooting

### ❌ "Connection refused"
**Solution:** Make sure Qdrant is running
```powershell
docker ps  # Check if Qdrant container is running
```

### ❌ "No documents found"
**Solution:** Check folder structure
```powershell
ls traffic_laws_WITH_CONTENT_*
ls traffic_laws_WITH_CONTENT_*/*.json
```

### ❌ "Out of memory"
**Solution:** Reduce batch size
```python
embedder.embed_documents(documents, batch_size=4)  # Smaller batches
```

### ❌ "Model download slow"
The first time you run, it downloads ~400MB Vietnamese model. This is normal.

### ❌ "Empty content skipped"
This is expected! The script filters out documents without content automatically.

---

## 📈 Performance Tips

1. **Memory:** Reduce `batch_size` if you have limited RAM
2. **Speed:** Use GPU if available (PyTorch auto-detects)
3. **Content length:** Adjust `max_content_length` based on your needs
4. **Search quality:** Longer content = better context but slower indexing

---

## 🎯 Next Steps

1. **✅ Run the embedder** - `python embed_content_to_qdrant.py`
2. **✅ Test searches** - Try different Vietnamese queries
3. **✅ Build API** - Create REST API for your app
4. **✅ Add web UI** - Use the HTML template above
5. **✅ Deploy** - Use Qdrant Cloud for production

---

## ❓ Questions?

Feel free to ask if you need help with:
- Custom filtering by document_type
- Hybrid search (keyword + semantic)
- Building a chatbot with RAG
- Optimizing search performance
- Deploying to production

Good luck! 🚀
