# 🏠 Running Qdrant Locally for 1.27M Documents

## Why Run Locally?

✅ **No storage limits** - embed all 1.27M documents
✅ **No API key needed** - simpler setup  
✅ **Faster** - no internet latency
✅ **Free** - no monthly costs
✅ **Full control** - your data stays local

---

## 🐳 Option 1: Docker (Recommended)

### Install Docker Desktop

1. **Download**: https://www.docker.com/products/docker-desktop/
2. **Install** Docker Desktop for Windows
3. **Restart** your computer

### Start Qdrant

**Option A: Store on D:\traffic_law (Recommended for your use case):**

```powershell
# Create directory first
mkdir D:\traffic_law\qdrant_data

# Run Qdrant with custom storage location
docker run -d `
  -p 6333:6333 `
  -p 6334:6334 `
  -v D:\traffic_law\qdrant_data:/qdrant/storage `
  --name qdrant `
  qdrant/qdrant
```

**Option B: Default Docker volume:**

```powershell
docker run -d -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage --name qdrant qdrant/qdrant
```

**Explanation:**
- `-d` = runs in background
- `-p 6333:6333` = web interface
- `-v D:\traffic_law\qdrant_data:/qdrant/storage` = stores data on D: drive
- `--name qdrant` = names the container for easy management

### Verify It's Running

```powershell
docker ps
```

You should see:
```
CONTAINER ID   IMAGE             PORTS                    
abc123         qdrant/qdrant     0.0.0.0:6333->6333/tcp
```

### Access Web UI

Open browser: http://localhost:6333/dashboard

---

## 💻 Option 2: Standalone Binary (No Docker)

### Download Qdrant

1. Go to: https://github.com/qdrant/qdrant/releases
2. Download latest Windows version: `qdrant-x86_64-pc-windows-msvc.zip`
3. Extract to `C:\qdrant\`

### Run Qdrant

```powershell
cd C:\qdrant
.\qdrant.exe
```

Leave this terminal running!

---

## ✅ Test Connection

```powershell
python test_qdrant_connection.py
```

Should show: **✅ Connection successful!**

---

## 🚀 Embed Your Documents

### Step 1: Stop the Cloud Version (if running)

Press `Ctrl+C` on the `embed_content_to_qdrant.py` terminal

### Step 2: Run Local Embedder

```powershell
python embed_local.py
```

**What it does differently:**
- ✅ Connects to **localhost:6333** (no API key)
- ✅ **Skips documents with content_length = 0** automatically
- ✅ Shows better progress for large datasets
- ✅ Uploads in chunks (more stable for 1.27M docs)

### Step 3: Wait...

With **1,271,393 documents**, expect:
- ⏱️ **15-40 hours** embedding time (depends on CPU)
- 💾 **~25GB** storage space needed
- 🔄 Uploads in batches (won't lose progress)

---

## 📊 Performance Tips

### 1. **Increase Batch Size** (if you have good CPU/RAM)

Edit `embed_local.py` line 301:
```python
embedder.embed_documents(documents, batch_size=64)  # Default: 32
```

### 2. **Use GPU** (if you have NVIDIA GPU)

Install GPU version of PyTorch:
```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

This can be **10x faster**!

### 3. **Filter Documents** (recommended)

Only embed important documents:

```python
documents = embedder.load_content_files(
    folder_pattern="traffic_laws_WITH_CONTENT_*",
    min_content_length=500  # Only docs with 500+ chars
)
```

Or run analysis first:
```powershell
python analyze_documents.py
```

---

## 💾 Storage Requirements

| Documents | Storage | Free Option | Paid Option |
|-----------|---------|-------------|-------------|
| 50,000 | ~1 GB | ✅ Qdrant Cloud Free | Local Docker |
| 500,000 | ~10 GB | ❌ Need paid | ✅ Local Docker |
| 1,271,393 | ~25 GB | ❌ Need paid | ✅ Local Docker |

**Recommendation:** Use local Docker for your 1.27M documents

---

## 🛠️ Docker Commands

### Check if Qdrant is running
```powershell
docker ps
```

### Stop Qdrant
```powershell
docker stop qdrant
```

### Start Qdrant
```powershell
docker start qdrant
```

### View Qdrant logs
```powershell
docker logs qdrant
```

### Remove Qdrant (⚠️ deletes all data)
```powershell
docker rm -f qdrant
docker volume rm qdrant_storage
```

### Backup Qdrant data
```powershell
docker cp qdrant:/qdrant/storage ./qdrant_backup
```

---

## 🔍 Monitor Progress

While embedding is running, open another PowerShell:

```powershell
# Check collection stats
python -c "from qdrant_client import QdrantClient; c = QdrantClient('http://localhost:6333'); print(c.get_collection('vietnamese_legal_content').points_count)"
```

Or open web UI: http://localhost:6333/dashboard

---

## 📈 Expected Timeline

For **1,271,393 documents**:

| Stage | Time | What Happens |
|-------|------|--------------|
| Model Download | 5-10 min | First time only (~400MB) |
| Loading JSONs | 10-20 min | Reading all files |
| Embedding | 15-40 hours | Depends on CPU |
| Upload | 2-4 hours | Batched uploads |
| **Total** | **~20-45 hours** | Can run overnight |

**Tip:** Let it run overnight or over the weekend!

---

## ⚠️ Troubleshooting

### "Cannot connect to Qdrant"
**Solution:** Make sure Docker container is running
```powershell
docker ps
docker start qdrant
```

### "Out of memory"
**Solution:** Reduce batch size in `embed_local.py`:
```python
batch_size=16  # or even 8
```

### "Process killed"
**Solution:** Your system ran out of RAM. Filter documents:
```python
min_content_length=1000  # Only docs with 1000+ chars
```

### Docker not working?
**Solution:** Use standalone binary (Option 2 above)

---

## 🎯 After Embedding Completes

Your 1.27M documents are now searchable!

### Search from Python:
```python
from embed_local import LocalContentEmbedder

embedder = LocalContentEmbedder()
results = embedder.search("Giấy phép lái xe", limit=10)

for r in results:
    print(f"{r['score']:.4f} - {r['document']['title']}")
```

### Create API Server:
See `DEPLOYMENT_GUIDE.md` for multi-user setup

---

## 📞 Need Help?

1. **Check Docker status**: `docker ps`
2. **Check Qdrant logs**: `docker logs qdrant`
3. **Test connection**: `python test_qdrant_connection.py`
4. **Web UI**: http://localhost:6333/dashboard

---

## 💡 Smart Filtering Suggestion

Instead of embedding ALL 1.27M docs, consider:

### Option A: Top 100,000 longest documents
```python
min_content_length=2000  # Adjust based on analysis
```

### Option B: Run analysis first
```powershell
python analyze_documents.py
```

This shows you content distribution and recommends optimal filtering!

---

Good luck with your local embedding! 🚀
