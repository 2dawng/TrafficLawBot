# 🚀 Quick Start: Embed Your Documents to Qdrant Cloud

## ✅ What You Need

1. **Qdrant Cloud Account** ✅ (You have this)
   - Cluster URL: `https://93be95a1-3efd-42bf-93ab-f3ef0056a8a9.eu-central-1-0.aws.cloud.qdrant.io:6333`
   
2. **API Key** ⚠️ (You need to get this)
   - Go to: https://cloud.qdrant.io/
   - Click your cluster → **API Keys** section
   - Create or copy your API key

3. **Python Packages** ✅ (Already installed)
   - qdrant-client
   - sentence-transformers
   - torch

---

## 📋 Step-by-Step Process

### Step 1: Get Your API Key (5 minutes)

1. Open https://cloud.qdrant.io/ in browser
2. Login to your account
3. Click on your cluster
4. Go to **"API Keys"** or **"Data Access Control"**
5. Copy the API key (save it somewhere safe!)

### Step 2: Test Connection (1 minute)

Edit `test_qdrant_connection.py` and replace:
```python
QDRANT_API_KEY = "YOUR_API_KEY_HERE"  # Put your actual key here
```

Then run:
```powershell
python test_qdrant_connection.py
```

You should see: **✅ Connection test PASSED!**

### Step 3: Update Embedding Script (1 minute)

Edit `embed_content_to_qdrant.py` line 322 and replace:
```python
api_key="YOUR_API_KEY_HERE",  # Put your actual key here
```

### Step 4: Embed Your Documents (10-30 minutes)

Run the embedding script:
```powershell
python embed_content_to_qdrant.py
```

**What happens:**
- ✅ Loads all JSON files from `traffic_laws_WITH_CONTENT_*` folders
- ✅ Downloads Vietnamese language model (first time only, ~400MB)
- ✅ Generates embeddings for each document
- ✅ Uploads to Qdrant Cloud
- ✅ Tests search with sample queries

**Expected output:**
```
======================================================================
🚀 Vietnamese Legal Documents Content Embedder
======================================================================
Loading embedding model: keepitreal/vietnamese-sbert
✅ Created collection: vietnamese_legal_content (vector size: 768)

📁 Found 50 folders matching pattern: traffic_laws_WITH_CONTENT_*
📄 Loading: traffic_laws_WITH_CONTENT_20251106_221541\scraped_data_with_content.json

📊 Loading Statistics:
  - Total documents: 1500
  - With content: 1200
  - Empty content (skipped): 300

🔄 Embedding 1200 documents...
Processing batch 1/75...
Processing batch 2/75...
...

✅ Successfully uploaded 1200 documents to Qdrant!

📊 Collection Statistics:
  - Total documents: 1200
  - Vector size: 768
  - Distance metric: Cosine

🔍 Testing search functionality...
✅ Embedding process completed!
```

### Step 5: Verify It Works

After embedding, the script automatically tests search. You should see results like:

```
🔎 Query: 'Chạy xe máy buông tay múa quạt xử phạt thế nào'

  1. Score: 0.8534
     Title: Chạy xe máy buông hai tay để múa quạt thì bị xử phạt như thế nào?...
     URL: https://thuvienphapluat.vn/...
     Content preview: Beginning of dialog window...
```

---

## 🎯 What's Next?

After successful embedding, you have options:

### Option A: Use Python to Search

```python
from embed_content_to_qdrant import ContentEmbedder
import os

embedder = ContentEmbedder(
    qdrant_url="https://93be95a1-3efd-42bf-93ab-f3ef0056a8a9.eu-central-1-0.aws.cloud.qdrant.io:6333",
    collection_name="vietnamese_legal_content",
    embedding_model="keepitreal/vietnamese-sbert",
    api_key=os.getenv("QDRANT_API_KEY")
)

results = embedder.search("Vi phạm giao thông", limit=5)
for r in results:
    print(f"Score: {r['score']:.4f} - {r['document']['title']}")
```

### Option B: Create API Server (Recommended for Multi-User)

See `DEPLOYMENT_GUIDE.md` for:
- Creating FastAPI server
- Building web interface
- Deploying for multiple users

---

## 🔒 Security Tips

**DON'T** commit your API key to Git!

**Best practice:** Use environment variable
```powershell
# Set it once
$env:QDRANT_API_KEY = "your_actual_key"

# Then in Python code
import os
api_key = os.getenv("QDRANT_API_KEY")
```

Or create `config.py` (add to `.gitignore`):
```python
# config.py
QDRANT_API_KEY = "your_actual_key"
```

---

## 📊 Expected Performance

| Metric | Value |
|--------|-------|
| **Embedding time** | 10-30 minutes (for 1000-5000 docs) |
| **Upload time** | 1-5 minutes |
| **Search latency** | 50-100ms per query |
| **Accuracy** | High (Vietnamese SBERT model) |

---

## ⚠️ Troubleshooting

### "Authentication failed"
→ Wrong API key. Get new one from dashboard.

### "Connection timeout"
→ Check internet connection and URL format.

### "Model download stuck"
→ First time downloads ~400MB. Be patient or check internet.

### "Out of memory"
→ Reduce `batch_size=8` in embed_documents() call.

### "No documents found"
→ Check you have `traffic_laws_WITH_CONTENT_*` folders with JSON files.

---

## 📞 Need Help?

1. Check `GET_QDRANT_API_KEY.md` for API key instructions
2. Check `DEPLOYMENT_GUIDE.md` for multi-user setup
3. Check `EMBED_CONTENT_GUIDE.md` for detailed explanations

---

## ✅ Checklist

- [ ] Got API key from Qdrant Cloud
- [ ] Tested connection (run `test_qdrant_connection.py`)
- [ ] Updated `embed_content_to_qdrant.py` with API key
- [ ] Ran embedding script successfully
- [ ] Verified search works
- [ ] (Optional) Created API server for multi-user access

Good luck! 🚀
