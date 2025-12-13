"""Embed ONLY traffic law documents (filtered by URL) - Using working pattern"""

import os
import json
import glob
import time
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
PROCESSED_FILES_LOG = "processed_traffic_files.txt"
BACKUP_LOG = "traffic_laws_backup.jsonl"
EMBEDDING_LOG = "traffic_laws_embedding.log"

# Load already processed files
processed_files = set()
if os.path.exists(PROCESSED_FILES_LOG):
    with open(PROCESSED_FILES_LOG, "r", encoding="utf-8") as f:
        processed_files = set(line.strip() for line in f if line.strip())
    print(f"📋 Already processed: {len(processed_files)} files")

# Initialize client
client = QdrantClient(url="http://localhost:6333", timeout=60)

# Load model
print("Loading model...")
model = SentenceTransformer("keepitreal/vietnamese-sbert")
if torch.cuda.is_available():
    model = model.to("cuda")
    print(f"✅ Using GPU: {torch.cuda.get_device_name(0)}")
    print(
        f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
    )
else:
    print("⚠️ GPU not detected, using CPU")

# Create collection
print(f"\nCreating collection: {COLLECTION_NAME}")
try:
    client.get_collection(collection_name=COLLECTION_NAME)
    print(f"✅ Using existing collection: {COLLECTION_NAME}")
except:
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )
    print(f"✅ Created new collection: {COLLECTION_NAME}")

# Find all folders
folders = glob.glob("traffic_laws_WITH_CONTENT_*")
print(f"\n📁 Found {len(folders)} total folders")

# Filter out already processed
folders_to_process = [f for f in folders if f not in processed_files]
print(f"📁 {len(folders_to_process)} folders remaining to process")

if not folders_to_process:
    print("✅ All files already processed!")
    info = client.get_collection(COLLECTION_NAME)
    print(f"📊 Collection has {info.points_count:,} documents")
    exit(0)

# Get starting point ID
try:
    current_count = client.get_collection(COLLECTION_NAME).points_count
    next_point_id = current_count
    print(
        f"📊 Collection has {current_count:,} documents. Continuing from ID {next_point_id}"
    )
except:
    next_point_id = 0
    print("📊 Starting fresh collection...")

# Statistics
total_embedded = 0
total_traffic_laws = 0
start_time = time.time()

# GLOBAL deduplication: Track ALL URLs across ALL files
global_seen_urls = set()

# Load already embedded URLs from backup
if os.path.exists(BACKUP_LOG):
    print(f"📋 Loading already embedded URLs from backup...")
    with open(BACKUP_LOG, "r", encoding="utf-8") as bf:
        for line in bf:
            try:
                entry = json.loads(line)
                global_seen_urls.add(entry.get("url", ""))
            except:
                continue
    print(f"📋 Already embedded: {len(global_seen_urls):,} unique URLs")

# Open logs
with open(EMBEDDING_LOG, "a", encoding="utf-8") as log:
    log.write(f"\n{'='*70}\n")
    log.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    log.write(f"Folders to process: {len(folders_to_process)}\n")
    log.write(f"Global URLs already embedded: {len(global_seen_urls):,}\n")
    log.write(f"{'='*70}\n")

# Process each folder ONE at a time (EXACT pattern from working script)
for idx, folder in enumerate(folders_to_process, 1):
    json_file = os.path.join(folder, "scraped_data_with_content.json")

    if not os.path.exists(json_file):
        continue

    print(f"\n{'='*70}")
    print(f"📂 [{idx}/{len(folders_to_process)}] {folder}")
    print(f"{'='*70}")

    try:
        # Load THIS file only
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data if isinstance(data, list) else [data]

        # Filter for traffic laws and prepare documents
        # Use dict to deduplicate by URL (keeps first occurrence)
        url_to_doc = {}
        skipped_duplicates = 0
        for item in items:
            url = item.get("url", "")

            # FILTER: Only traffic law URLs
            if not url.startswith(URL_PREFIX):
                continue

            # GLOBAL deduplication: Skip if already embedded in previous files
            if url in global_seen_urls:
                skipped_duplicates += 1
                continue

            # Skip if URL already seen in this file
            if url in url_to_doc:
                continue

            content = item.get("content", "").strip()
            if not content or len(content) < 100:
                continue

            title = item.get("title", "").strip()

            # Extract year from URL or title for date-based ranking
            import re

            year_match = re.search(r"20\d{2}", url + title)
            year = int(year_match.group()) if year_match else 2000

            # Prepare text for embedding (title + content)
            text_to_embed = f"{title}\n\n{content}"
            if len(text_to_embed) > 8000:
                text_to_embed = text_to_embed[:8000]

            doc = {
                "url": url,
                "title": title,
                "text": text_to_embed,
                "content_length": len(content),
                "document_type": item.get("document_type", ""),
                "status": item.get("status", ""),
                "year": year,  # Store year for ranking
            }
            url_to_doc[url] = doc

        documents = list(url_to_doc.values())

        if not documents:
            if skipped_duplicates > 0:
                print(f"   ⏭️ No new docs ({skipped_duplicates} duplicates skipped)")
            else:
                print(f"   ⏭️ No traffic law docs in this file")
            # Still mark as processed
            with open(PROCESSED_FILES_LOG, "a", encoding="utf-8") as pf:
                pf.write(f"{folder}\n")
            with open(EMBEDDING_LOG, "a", encoding="utf-8") as log:
                log.write(
                    f"[{datetime.now().strftime('%H:%M:%S')}] SKIPPED: {folder} (no traffic laws)\n"
                )
            continue

        print(f"   ✅ Found {len(documents)} traffic law documents")
        total_traffic_laws += len(documents)

        # Prepare texts for embedding
        texts = [doc["text"] for doc in documents]

        print(f"   🔄 Embedding {len(documents)} documents...")

        # Embed in batches (EXACT pattern from working script)
        points = []
        batch_size = 64  # Same as working script

        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_texts = texts[i : i + batch_size]

            try:
                embeddings = model.encode(
                    batch_texts,
                    show_progress_bar=False,
                    batch_size=batch_size,
                    convert_to_numpy=True,
                )

                for doc, embedding in zip(batch_docs, embeddings):
                    # Store metadata + content excerpt for RAG
                    # Truncate content to 2000 chars for payload size
                    content_excerpt = (
                        doc["text"][:2000] if len(doc["text"]) > 2000 else doc["text"]
                    )

                    payload = {
                        "url": doc["url"],
                        "title": doc["title"],
                        "content": content_excerpt,
                        "content_length": doc["content_length"],
                        "document_type": doc["document_type"],
                        "status": doc["status"],
                        "year": doc["year"],  # Store year for ranking
                    }

                    points.append(
                        PointStruct(
                            id=next_point_id, vector=embedding.tolist(), payload=payload
                        )
                    )
                    next_point_id += 1

            except Exception as e:
                print(f"   ❌ Embedding error: {e}")
                with open(EMBEDDING_LOG, "a", encoding="utf-8") as log:
                    log.write(
                        f"[{datetime.now().strftime('%H:%M:%S')}] EMBED ERROR: {folder} - {str(e)}\n"
                    )

        # Upload to Qdrant (EXACT pattern - chunks of 100)
        if points:
            try:
                max_chunk_size = 100
                uploaded_count = 0
                total_chunks = (len(points) + max_chunk_size - 1) // max_chunk_size

                for chunk_idx in range(0, len(points), max_chunk_size):
                    chunk = points[chunk_idx : chunk_idx + max_chunk_size]
                    client.upsert(
                        collection_name=COLLECTION_NAME,
                        points=chunk,
                        wait=True,  # Wait for confirmation
                    )
                    uploaded_count += len(chunk)

                total_embedded += uploaded_count
                if total_chunks > 1:
                    print(
                        f"   ✅ Uploaded {uploaded_count} documents in {total_chunks} chunks"
                    )
                else:
                    print(f"   ✅ Uploaded {uploaded_count} documents")

                # ADD URLs to global tracking
                for point in points:
                    global_seen_urls.add(point.payload["url"])

                # Mark as successfully processed
                with open(PROCESSED_FILES_LOG, "a", encoding="utf-8") as pf:
                    pf.write(f"{folder}\n")

                with open(EMBEDDING_LOG, "a", encoding="utf-8") as log:
                    log.write(
                        f"[{datetime.now().strftime('%H:%M:%S')}] SUCCESS: {folder} - {len(points)} docs\n"
                    )

                # Backup entries
                with open(BACKUP_LOG, "a", encoding="utf-8") as bf:
                    for point in points:
                        backup_entry = {
                            "url": point.payload["url"],
                            "title": point.payload["title"],
                            "content_length": point.payload["content_length"],
                            "processed_at": datetime.now().isoformat(),
                        }
                        bf.write(json.dumps(backup_entry, ensure_ascii=False) + "\n")

                # Show progress
                elapsed = time.time() - start_time
                files_per_hour = idx / (elapsed / 3600) if elapsed > 0 else 0
                remaining_files = len(folders_to_process) - idx
                eta_hours = (
                    remaining_files / files_per_hour if files_per_hour > 0 else 0
                )

                print(
                    f"   📊 Progress: {idx/len(folders_to_process)*100:.1f}% | Total: {total_embedded:,} docs"
                )
                print(
                    f"   ⏱️ Speed: {files_per_hour:.1f} files/hr | ETA: {eta_hours:.1f} hours"
                )

            except Exception as e:
                print(f"   ❌ Upload error: {e}")
                with open(EMBEDDING_LOG, "a", encoding="utf-8") as log:
                    log.write(
                        f"[{datetime.now().strftime('%H:%M:%S')}] UPLOAD ERROR: {folder} - {str(e)}\n"
                    )

    except json.JSONDecodeError as e:
        print(f"   ❌ JSON parse error: {e}")
        with open(EMBEDDING_LOG, "a", encoding="utf-8") as log:
            log.write(f"[{datetime.now().strftime('%H:%M:%S')}] JSON ERROR: {folder}\n")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        with open(EMBEDDING_LOG, "a", encoding="utf-8") as log:
            log.write(
                f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {folder} - {str(e)}\n"
            )

# Final statistics
print(f"\n{'='*70}")
print(f"✅ COMPLETED!")
print(f"{'='*70}")
print(f"📊 Files processed: {idx}/{len(folders_to_process)}")
print(f"📊 Traffic law documents found: {total_traffic_laws:,}")
print(f"📊 Documents embedded: {total_embedded:,}")
print(f"⏱️ Total time: {(time.time() - start_time)/3600:.2f} hours")

with open(EMBEDDING_LOG, "a", encoding="utf-8") as log:
    log.write(f"\n{'='*70}\n")
    log.write(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    log.write(f"Files processed: {idx}/{len(folders_to_process)}\n")
    log.write(f"Traffic law documents: {total_traffic_laws:,}\n")
    log.write(f"Documents embedded: {total_embedded:,}\n")
    log.write(f"Total time: {(time.time() - start_time)/3600:.2f} hours\n")
    log.write(f"{'='*70}\n")

# Final collection stats
try:
    info = client.get_collection(COLLECTION_NAME)
    print(f"\n📊 Collection Statistics:")
    print(f"  - Collection name: {COLLECTION_NAME}")
    print(f"  - Total documents: {info.points_count:,}")
    print(f"  - Vector size: {info.config.params.vectors.size}")
except Exception as e:
    print(f"❌ Error getting stats: {e}")

print(f"\n📁 Files created:")
print(f"  - {PROCESSED_FILES_LOG}")
print(f"  - {BACKUP_LOG}")
print(f"  - {EMBEDDING_LOG}")
print("\nTest with: python test_traffic_laws.py")
