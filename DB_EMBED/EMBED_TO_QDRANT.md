# 🚀 Embedding Vietnamese Legal Documents to Qdrant

This guide shows you how to embed all your scraped Vietnamese legal documents (traffic laws, Q&A, etc.) into Qdrant vector database for semantic search.

---

## 📋 What You Have

Your workspace contains:

### 1. **Traffic Laws** (17 folders)
- `traffic_laws_20251101_*/scraped_data.jsonl`
- Contains: Vietnamese traffic law documents with titles, document numbers, URLs, etc.

### 2. **Q&A Data** (if you've scraped it)
- `tvpl_qa_ver3_testing/*.jsonl`
- Contains: Questions and answers about Vietnamese law

---

## 🎯 What This Will Do

The `embed_to_qdrant.py` script will:

1. ✅ Load all your scraped documents (traffic laws + Q&A)
2. ✅ Convert text to vector embeddings using Vietnamese language model
3. ✅ Store vectors in Qdrant for semantic search
4. ✅ Enable you to search by meaning, not just keywords

---

## 📦 Installation

### Step 1: Install Qdrant

**Option A: Run Qdrant with Docker** (Recommended)
```powershell
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

**Option B: Use Qdrant Cloud** (Free tier available)
- Go to https://cloud.qdrant.io/
- Create free account
- Get your cluster URL and API key

**Option C: Install Qdrant locally**
```powershell
# Download from https://github.com/qdrant/qdrant/releases
# Run the executable
```

### Step 2: Install Python Dependencies

```powershell
# Activate your virtual environment first
& "C:/VSCODE/Simple Crawl TVPL/venv/Scripts/Activate.ps1"

# Install required packages
pip install qdrant-client sentence-transformers torch
```

---

## 🚀 Usage

### Basic Usage (Local Qdrant)

```powershell
# Make sure Qdrant is running on localhost:6333
python embed_to_qdrant.py
```

### Using Qdrant Cloud

Edit `embed_to_qdrant.py` line 274:

```python
embedder = QdrantEmbedder(
    qdrant_url="https://your-cluster-url.qdrant.io",  # Your Qdrant Cloud URL
    collection_name="vietnamese_legal_docs",
    embedding_model="keepitreal/vietnamese-sbert"
)
```

---

## 🔧 Configuration Options

### Choose Different Embedding Models

The script uses `keepitreal/vietnamese-sbert` by default. Other options:

```python
# Option 1: Vietnamese SBERT (Default - Best for Vietnamese)
embedding_model="keepitreal/vietnamese-sbert"

# Option 2: Multilingual E5 (Good for mixed languages)
embedding_model="intfloat/multilingual-e5-base"

# Option 3: mT5 (Larger, more accurate)
embedding_model="VoVanPhuc/sup-SimCSE-VietNamese-phobert-base"
```

### Change Collection Name

```python
collection_name="my_legal_database"  # Your custom name
```

### Adjust Batch Size

```python
embedder.embed_documents(all_documents, batch_size=16)  # Smaller if low memory
```

---

## 📊 What Gets Embedded

### Traffic Laws
For each traffic law document:
- ✅ Title (Tiêu đề)
- ✅ Document number (Số hiệu)
- ✅ Document type (Loại văn bản)
- ✅ URL
- ✅ Date
- ✅ Related links count

### Q&A Documents
For each Q&A:
- ✅ Question
- ✅ Answer (first 500 chars)
- ✅ Domain
- ✅ Date
- ✅ URL

---

## 🔍 Searching Your Data

### Python Code

```python
from embed_to_qdrant import QdrantEmbedder

# Initialize
embedder = QdrantEmbedder(
    qdrant_url="http://localhost:6333",
    collection_name="vietnamese_legal_docs"
)

# Search all documents
results = embedder.search("Giấy phép lái xe", limit=5)

# Search only traffic laws
results = embedder.search("Giấy phép lái xe", limit=5, doc_type="traffic_law")

# Search only Q&A
results = embedder.search("Cách đăng ký xe", limit=5, doc_type="qa")

# Print results
for i, result in enumerate(results, 1):
    print(f"{i}. Score: {result['score']:.4f}")
    print(f"   Title: {result['document'].get('title', 'N/A')}")
    print()
```

### Example Queries

```python
# Vietnamese queries
embedder.search("Giấy phép lái xe mới nhất", limit=5)
embedder.search("Vi phạm giao thông đường bộ", limit=5)
embedder.search("Đăng ký xe cơ giới", limit=5)
embedder.search("Biển số xe", limit=5)
embedder.search("Luật giao thông 2025", limit=5)
```

---

## 📈 Performance Tips

### 1. Memory Management
- If you have limited RAM, reduce batch_size:
  ```python
  embedder.embed_documents(all_documents, batch_size=8)
  ```

### 2. Speed Up Embedding
- Use GPU if available (PyTorch will detect automatically)
- The Vietnamese SBERT model is ~400MB, downloads on first use

### 3. Qdrant Performance
- Use Docker for best local performance
- Use Qdrant Cloud for production (scales automatically)

---

## 🛠️ Advanced: Building a Search API

Create `search_api.py`:

```python
from fastapi import FastAPI
from embed_to_qdrant import QdrantEmbedder

app = FastAPI()
embedder = QdrantEmbedder()

@app.get("/search")
def search(query: str, limit: int = 5, doc_type: str = None):
    """Search Vietnamese legal documents"""
    results = embedder.search(query, limit=limit, doc_type=doc_type)
    return {
        "query": query,
        "count": len(results),
        "results": results
    }

# Run with: uvicorn search_api:app --reload
```

Install and run:
```powershell
pip install fastapi uvicorn
uvicorn search_api:app --reload
```

Access at: http://localhost:8000/docs

---

## 🎨 Building a Web Interface

Create `web_search.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Vietnamese Legal Search</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        input[type="text"] { width: 100%; padding: 12px; font-size: 16px; border: 2px solid #ddd; border-radius: 5px; }
        button { padding: 12px 30px; font-size: 16px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px; }
        .result { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }
        .score { color: #28a745; font-weight: bold; }
    </style>
</head>
<body>
    <h1>🔍 Tìm kiếm văn bản pháp luật Việt Nam</h1>
    <input type="text" id="query" placeholder="Nhập câu hỏi hoặc từ khóa..." />
    <button onclick="search()">Tìm kiếm</button>
    <div id="results"></div>

    <script>
        async function search() {
            const query = document.getElementById('query').value;
            const response = await fetch(`http://localhost:8000/search?query=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = '';
            
            data.results.forEach((result, i) => {
                const doc = result.document;
                const div = document.createElement('div');
                div.className = 'result';
                div.innerHTML = `
                    <div class="score">Độ phù hợp: ${(result.score * 100).toFixed(1)}%</div>
                    <h3>${doc.title || doc.question || 'Untitled'}</h3>
                    <p><a href="${doc.url}" target="_blank">Xem chi tiết</a></p>
                `;
                resultsDiv.appendChild(div);
            });
        }
    </script>
</body>
</html>
```

---

## 📊 Monitoring & Stats

Check collection statistics:

```python
embedder.get_collection_stats()
```

Output:
```
📊 Collection Statistics:
  - Total points: 1234
  - Vector size: 768
  - Distance metric: Cosine
```

---

## 🐛 Troubleshooting

### Error: "Connection refused"
- ✅ Make sure Qdrant is running: `docker ps`
- ✅ Check URL: Should be `http://localhost:6333` for local Docker

### Error: "No documents found"
- ✅ Check folder structure: `ls traffic_laws_*`
- ✅ Verify JSONL files exist: `ls traffic_laws_*/scraped_data.jsonl`

### Error: "Out of memory"
- ✅ Reduce batch size: `batch_size=8` or `batch_size=4`
- ✅ Process documents in chunks

### Slow embedding
- ✅ Install PyTorch with CUDA if you have GPU
- ✅ Use smaller model: `embedding_model="intfloat/multilingual-e5-small"`

---

## 🎯 Next Steps

1. **Add more data sources**
   - Modify `load_traffic_laws()` to include more folders
   - Add custom loaders for other data types

2. **Improve search**
   - Add filters (by date, document type, etc.)
   - Implement hybrid search (keyword + semantic)
   - Add reranking for better results

3. **Build chatbot**
   - Use OpenAI/Anthropic API
   - Retrieve relevant docs from Qdrant
   - Generate answers based on context

4. **Deploy to production**
   - Use Qdrant Cloud
   - Deploy API with Docker
   - Add authentication and rate limiting

---

## 📚 Resources

- **Qdrant Docs**: https://qdrant.tech/documentation/
- **Sentence Transformers**: https://www.sbert.net/
- **Vietnamese Models**: https://huggingface.co/models?language=vi

---

## ❓ Questions?

Feel free to ask if you need help with:
- ✅ Custom embedding strategies
- ✅ Different vector databases
- ✅ Building RAG (Retrieval Augmented Generation) systems
- ✅ Optimizing search performance

Good luck! 🚀
