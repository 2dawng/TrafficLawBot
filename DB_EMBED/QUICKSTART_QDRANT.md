# ⚡ Quick Start: Embed to Qdrant in 5 Minutes

Follow these steps to get your Vietnamese legal documents searchable!

---

## Step 1: Install Qdrant (Choose One)

### Option A: Docker (Easiest) ⭐
```powershell
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```
Leave this running in the terminal.

### Option B: Download Qdrant
Download from: https://github.com/qdrant/qdrant/releases
Run the executable.

---

## Step 2: Install Python Packages

```powershell
# Activate virtual environment
& "C:/VSCODE/Simple Crawl TVPL/venv/Scripts/Activate.ps1"

# Install packages (this will take a few minutes)
pip install qdrant-client sentence-transformers torch
```

---

## Step 3: Run the Embedder

```powershell
# This will:
# 1. Load all your scraped documents
# 2. Convert them to vectors
# 3. Upload to Qdrant
# 4. Run a test search

python embed_to_qdrant.py
```

**Expected output:**
```
============================================================
🚀 Vietnamese Legal Documents - Qdrant Embedder
============================================================
Loading embedding model: keepitreal/vietnamese-sbert
Created collection: vietnamese_legal_docs (vector size: 768)

Found 17 traffic law folders
Loading: traffic_laws_20251101_162641\scraped_data.jsonl
...
Loaded 150 traffic law documents

Embedding 150 documents...
Processing batch 1/5
[████████████████████████████████] 100%
...
✅ Successfully uploaded 150 documents to Qdrant!

📊 Collection Statistics:
  - Total points: 150
  - Vector size: 768
  - Distance metric: Cosine
```

---

## Step 4: Search Your Documents

```powershell
# Run the example search
python search_example.py
```

---

## Step 5: Use in Your Code

```python
from embed_to_qdrant import QdrantEmbedder

# Initialize
embedder = QdrantEmbedder()

# Search
results = embedder.search("Giấy phép lái xe", limit=5)

# Print
for result in results:
    print(f"Score: {result['score']:.2f}")
    print(f"Title: {result['document']['title']}")
    print()
```

---

## ✅ Done!

Your documents are now searchable! Check out `EMBED_TO_QDRANT.md` for:
- Building a search API
- Creating a web interface
- Advanced configurations
- Troubleshooting

---

## 🆘 Common Issues

### "Connection refused"
→ Make sure Qdrant is running: `docker ps`

### "No documents found"
→ Check your folders: `ls traffic_laws_*`

### "Out of memory"
→ Edit `embed_to_qdrant.py` line 288:
```python
embedder.embed_documents(all_documents, batch_size=8)
```

---

## 🎉 What's Next?

1. Try different search queries
2. Build a web interface (see `EMBED_TO_QDRANT.md`)
3. Create a chatbot with RAG
4. Deploy to production

Need help? Ask me! 🚀
