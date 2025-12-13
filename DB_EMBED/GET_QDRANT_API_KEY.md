# 🔑 How to Get Your Qdrant Cloud API Key

## Step-by-Step Instructions

### 1. Go to Qdrant Cloud Dashboard
- URL: https://cloud.qdrant.io/
- Login with your account

### 2. Find Your Cluster
- You should see your cluster listed
- Cluster ID: `93be95a1-3efd-42bf-93ab-f3ef0056a8a9`

### 3. Get the API Key

**Option A: From Cluster Page**
1. Click on your cluster name
2. Look for **"API Keys"** or **"Access"** section
3. Click **"Create API Key"** or use existing one
4. Copy the key (looks like: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`)

**Option B: From Settings**
1. Click on your cluster
2. Go to **"Data Access Control"** or **"API Keys"**
3. Create new key or copy existing
4. **Important:** Save it immediately (won't be shown again!)

### 4. Update Your Code

Replace `YOUR_API_KEY_HERE` in `embed_content_to_qdrant.py`:

```python
embedder = ContentEmbedder(
    qdrant_url="https://93be95a1-3efd-42bf-93ab-f3ef0056a8a9.eu-central-1-0.aws.cloud.qdrant.io:6333",
    collection_name="vietnamese_legal_content",
    embedding_model="keepitreal/vietnamese-sbert",
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",  # Your actual key here
)
```

---

## 🔒 Security Best Practice

**DON'T** hardcode API key in your script if you share it!

### Option 1: Use Environment Variable (Recommended)

**Step 1:** Set environment variable in PowerShell:
```powershell
$env:QDRANT_API_KEY = "your_actual_api_key_here"
```

**Step 2:** Update code to read from environment:
```python
import os

embedder = ContentEmbedder(
    qdrant_url="https://93be95a1-3efd-42bf-93ab-f3ef0056a8a9.eu-central-1-0.aws.cloud.qdrant.io:6333",
    collection_name="vietnamese_legal_content",
    embedding_model="keepitreal/vietnamese-sbert",
    api_key=os.getenv("QDRANT_API_KEY"),  # Reads from environment
)
```

### Option 2: Use Config File (Not committed to git)

**Step 1:** Create `config.py`:
```python
# config.py
QDRANT_URL = "https://93be95a1-3efd-42bf-93ab-f3ef0056a8a9.eu-central-1-0.aws.cloud.qdrant.io:6333"
QDRANT_API_KEY = "your_actual_api_key_here"
```

**Step 2:** Add `config.py` to `.gitignore`:
```
config.py
*.pyc
__pycache__/
```

**Step 3:** Import in your script:
```python
from config import QDRANT_URL, QDRANT_API_KEY

embedder = ContentEmbedder(
    qdrant_url=QDRANT_URL,
    collection_name="vietnamese_legal_content",
    embedding_model="keepitreal/vietnamese-sbert",
    api_key=QDRANT_API_KEY,
)
```

---

## 🧪 Test Connection

Create `test_qdrant_connection.py`:

```python
from qdrant_client import QdrantClient

# Replace with your actual values
QDRANT_URL = "https://93be95a1-3efd-42bf-93ab-f3ef0056a8a9.eu-central-1-0.aws.cloud.qdrant.io:6333"
QDRANT_API_KEY = "YOUR_API_KEY_HERE"

print("Testing Qdrant Cloud connection...")
print(f"URL: {QDRANT_URL}")

try:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    # Try to list collections
    collections = client.get_collections()
    
    print("✅ Connection successful!")
    print(f"Found {len(collections.collections)} collections")
    
    for collection in collections.collections:
        print(f"  - {collection.name}")
        
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\nPossible issues:")
    print("1. Wrong API key")
    print("2. Wrong URL (check if :6333 port is included)")
    print("3. Firewall blocking connection")
    print("4. API key doesn't have proper permissions")
```

Run it:
```powershell
python test_qdrant_connection.py
```

---

## 📋 Complete Connection Info

Your Qdrant Cloud cluster details:

| Property | Value |
|----------|-------|
| **Cluster ID** | `93be95a1-3efd-42bf-93ab-f3ef0056a8a9` |
| **Region** | `eu-central-1-0` (AWS Frankfurt) |
| **Full URL** | `https://93be95a1-3efd-42bf-93ab-f3ef0056a8a9.eu-central-1-0.aws.cloud.qdrant.io:6333` |
| **API Key** | Get from dashboard → API Keys section |

---

## ❓ Common Issues

### Issue 1: "Authentication failed"
**Solution:** Check API key is correct and not expired

### Issue 2: "Connection timeout"
**Solution:** 
- Check if URL includes `:6333` port
- Try without port: `https://...qdrant.io`
- Check internet connection

### Issue 3: "Collection not found"
**Normal!** This happens first time. The script will create it automatically.

### Issue 4: "Permission denied"
**Solution:** Make sure API key has "Write" permissions in Qdrant dashboard

---

## 🚀 After Getting API Key

1. ✅ Update `embed_content_to_qdrant.py` with your API key
2. ✅ Run: `python embed_content_to_qdrant.py`
3. ✅ Wait for documents to embed (may take 10-30 minutes depending on size)
4. ✅ Test search functionality
5. ✅ Deploy API server for multi-user access

---

## 💡 Free Tier Limits

Qdrant Cloud Free Tier includes:
- ✅ 1 GB storage (~50,000 documents)
- ✅ 1 cluster
- ✅ Unlimited queries
- ✅ 99.9% uptime SLA

If you need more:
- **Paid plan**: $25/month for 8GB
- Or self-host with Docker (free, unlimited)

---

Need help? Let me know! 🚀
