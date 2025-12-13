"""Embed ONLY traffic law documents (filtered by URL)"""

import os
import json
import glob
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import torch

print("=" * 70)
print("🚗 Embedding Traffic Laws Only")
print("=" * 70)

# Configuration
URL_PREFIX = "https://thuvienphapluat.vn/van-ban/Giao-thong-Van-tai/"
COLLECTION_NAME = "traffic_laws_only"
PROCESSED_LOG = "processed_traffic_urls.txt"
BACKUP_LOG = "traffic_laws_backup.jsonl"

# Initialize
client = QdrantClient(url="http://localhost:6333", timeout=60)
print("Loading model...")
model = SentenceTransformer("keepitreal/vietnamese-sbert")
if torch.cuda.is_available():
    model = model.to("cuda")
    print(f"✅ Using GPU: {torch.cuda.get_device_name(0)}")
    print(
        f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
    )
else:
    print("⚠️ GPU not detected, using CPU (will be slower)")

# Create collection
print(f"\nCreating collection: {COLLECTION_NAME}")
try:
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )
    print("✅ Collection created")
except Exception as e:
    print(f"⚠️ Collection exists or error: {e}")

# Load processed URLs
processed_urls = set()
if os.path.exists(PROCESSED_LOG):
    with open(PROCESSED_LOG, "r", encoding="utf-8") as f:
        processed_urls = set(line.strip() for line in f)
    print(f"📋 Already processed: {len(processed_urls)} URLs")

# Find all JSON files
folders = glob.glob("traffic_laws_WITH_CONTENT_*")
print(f"\n📁 Found {len(folders)} folders to scan")

# Load processed files
PROCESSED_FILES_LOG = "processed_traffic_files.txt"
processed_files = set()
if os.path.exists(PROCESSED_FILES_LOG):
    with open(PROCESSED_FILES_LOG, "r", encoding="utf-8") as f:
        processed_files = set(line.strip() for line in f)
    print(f"📋 Already processed: {len(processed_files)} files")

# Statistics
stats = {
    "total_files": len(folders),
    "processed_files": 0,
    "total_scanned": 0,
    "traffic_laws": 0,
    "already_processed": 0,
    "embedded": 0,
    "errors": 0,
}

# Get next point_id
try:
    info = client.get_collection(COLLECTION_NAME)
    point_id = info.points_count
    print(f"📊 Collection has {point_id:,} documents, continuing from ID {point_id}")
except:
    point_id = 0

start_time = datetime.now()

# Process ONE file at a time
for folder_idx, folder in enumerate(folders, 1):
    json_file = os.path.join(folder, "scraped_data_with_content.json")

    # Skip if file doesn't exist
    if not os.path.exists(json_file):
        continue

    # Skip if already processed
    if json_file in processed_files:
        stats["processed_files"] += 1
        continue

    print(f"\n[{folder_idx}/{len(folders)}] Processing: {folder}")

    try:
        # Load THIS file only
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data if isinstance(data, list) else [data]

        # Filter and collect texts to embed
        to_embed = []  # [(text, payload, url)]

        for item in items:
            stats["total_scanned"] += 1

            url = item.get("url", "")

            # Filter: Only traffic law URLs
            if not url.startswith(URL_PREFIX):
                continue

            stats["traffic_laws"] += 1

            # Skip if already processed
            if url in processed_urls:
                stats["already_processed"] += 1
                continue

            # Get content
            title = item.get("title", "").strip()
            content = item.get("content", "").strip()
            content_length = len(content)

            if not content or content_length < 100:
                continue

            # Prepare text for embedding: title + content
            text_to_embed = f"{title}\n\n{content}"
            if len(text_to_embed) > 8000:
                text_to_embed = text_to_embed[:8000]

            # Create payload (store URL and length, don't store full content)
            payload = {
                "url": url,
                "title": title,
                "content_length": content_length,
                "document_type": item.get("document_type", ""),
                "status": item.get("status", ""),
            }

            to_embed.append((text_to_embed, payload, url))

        # Batch encode with GPU (use 5-6GB of VRAM)
        batch = []
        backup_entries = []

        if to_embed:
            print(f"   🔄 Encoding {len(to_embed)} documents with GPU...")

            # Encode in large batches to max out GPU
            texts = [x[0] for x in to_embed]
            payloads = [x[1] for x in to_embed]
            urls = [x[2] for x in to_embed]

            try:
                # Batch size 128 to use more GPU memory (5-6GB)
                embeddings = model.encode(
                    texts, batch_size=128, show_progress_bar=True, convert_to_numpy=True
                )

                # Create points
                for embedding, payload, url in zip(embeddings, payloads, urls):
                    batch.append(
                        PointStruct(
                            id=point_id,
                            vector=embedding.tolist(),
                            payload=payload,
                        )
                    )

                    backup_entries.append(
                        {
                            "url": url,
                            "title": payload["title"],
                            "content_length": payload["content_length"],
                            "processed_at": datetime.now().isoformat(),
                        }
                    )

                    processed_urls.add(url)
                    point_id += 1

            except Exception as e:
                stats["errors"] += len(to_embed)
                print(f"   ❌ Encoding error: {e}")
                batch = []
                backup_entries = []

        # Upload THIS file's batch (split into chunks of 100)
        if batch:
            chunk_size = 100
            for i in range(0, len(batch), chunk_size):
                chunk = batch[i : i + chunk_size]
                try:
                    client.upsert(
                        collection_name=COLLECTION_NAME, points=chunk, wait=True
                    )
                    stats["embedded"] += len(chunk)
                except Exception as e:
                    print(f"   ❌ Upload error: {e}")
                    stats["errors"] += len(chunk)

            # Log processed URLs
            with open(PROCESSED_LOG, "a", encoding="utf-8") as pf:
                for entry in backup_entries:
                    pf.write(f"{entry['url']}\n")

            # Save backup
            with open(BACKUP_LOG, "a", encoding="utf-8") as bf:
                for entry in backup_entries:
                    bf.write(json.dumps(entry, ensure_ascii=False) + "\n")

            print(
                f"   ✅ Embedded {len(batch)} traffic law docs | Total: {stats['embedded']:,}"
            )
        else:
            print(f"   ⏭️ No traffic law docs in this file")

        # Mark file as processed
        with open(PROCESSED_FILES_LOG, "a", encoding="utf-8") as pf:
            pf.write(f"{json_file}\n")

        stats["processed_files"] += 1

        # Show progress
        elapsed = (datetime.now() - start_time).total_seconds() / 60
        files_per_hr = (stats["processed_files"] / elapsed) * 60 if elapsed > 0 else 0
        print(
            f"   📊 Files: {stats['processed_files']}/{stats['total_files']} | "
            f"Speed: {files_per_hr:.1f} files/hr | Elapsed: {elapsed:.1f}m"
        )

    except Exception as e:
        print(f"   ❌ Error processing file: {e}")
        continue

# Final statistics
print("\n" + "=" * 70)
print("✅ EMBEDDING COMPLETE!")
print("=" * 70)
elapsed_total = (datetime.now() - start_time).total_seconds() / 60
print(f"⏱️ Total time: {elapsed_total:.1f} minutes ({elapsed_total/60:.2f} hours)")
print(f"\n📊 Statistics:")
print(f"   Files processed: {stats['processed_files']}/{stats['total_files']}")
print(f"   Total documents scanned: {stats['total_scanned']:,}")
print(f"   Traffic law docs found: {stats['traffic_laws']:,}")
print(f"   Already processed: {stats['already_processed']:,}")
print(f"   Newly embedded: {stats['embedded']:,}")
print(f"   Errors: {stats['errors']}")
print(f"\n📁 Files created:")
print(f"   Processed files log: {PROCESSED_FILES_LOG}")
print(f"   Processed URLs log: {PROCESSED_LOG}")
print(f"   Backup file: {BACKUP_LOG}")
print(f"   Qdrant storage: D:\\qdrant_traffic_laws")
print("=" * 70)

# Get collection info
try:
    info = client.get_collection(COLLECTION_NAME)
    print(f"\n📊 Collection: {info.points_count:,} documents")
except:
    pass

print("\nTest with: python test_traffic_laws.py")
