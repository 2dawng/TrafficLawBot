"""Recreate collection from backup (without duplicates)"""

import json
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import torch
from collections import defaultdict

print("=" * 70)
print("🔄 Recreating Collection from Backup")
print("=" * 70)

client = QdrantClient(url="http://localhost:6333", timeout=60)
OLD_COLLECTION = "traffic_laws_only"
NEW_COLLECTION = "traffic_laws_clean"

# Load model
print("\nLoading model...")
model = SentenceTransformer("keepitreal/vietnamese-sbert")
if torch.cuda.is_available():
    model = model.to("cuda")
    print(f"✅ Using GPU: {torch.cuda.get_device_name(0)}")

# Delete old collection if exists
print(f"\n🗑️ Removing old collection: {OLD_COLLECTION}")
try:
    client.delete_collection(OLD_COLLECTION)
    print("   ✅ Deleted")
except:
    print("   ⚠️ Collection doesn't exist")

# Create new clean collection
print(f"\n✨ Creating new collection: {NEW_COLLECTION}")
client.create_collection(
    collection_name=NEW_COLLECTION,
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
)
print("   ✅ Created")

# Read backup and find unique URLs
print("\n📖 Reading backup file...")
backup_file = "traffic_laws_backup.jsonl"
url_to_data = {}  # Keep only first occurrence

with open(backup_file, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        entry = json.loads(line)
        url = entry.get("url", "")
        if url and url not in url_to_data:
            url_to_data[url] = entry

unique_count = len(url_to_data)
print(f"   ✅ Found {unique_count:,} unique URLs")

# Re-embed from scratch (this ensures no duplicates)
print(f"\n🔄 Re-embedding {unique_count:,} unique documents...")
print("   (This will take a few minutes)")

# Load original data to get content
import glob
import os

url_to_content = {}
folders = glob.glob("traffic_laws_WITH_CONTENT_*")

print(f"\n📁 Scanning {len(folders)} folders for content...")
scanned_files = 0

for folder in folders:
    json_file = os.path.join(folder, "scraped_data_with_content.json")
    if not os.path.exists(json_file):
        continue

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        items = data if isinstance(data, list) else [data]

        for item in items:
            url = item.get("url", "")
            if url in url_to_data:  # Only keep URLs we want
                title = item.get("title", "").strip()
                content = item.get("content", "").strip()
                text = f"{title}\n\n{content}"
                if len(text) > 8000:
                    text = text[:8000]

                url_to_content[url] = {
                    "text": text,
                    "title": title,
                    "content_length": len(content),
                    "document_type": item.get("document_type", ""),
                    "status": item.get("status", ""),
                }

        scanned_files += 1
        if scanned_files % 100 == 0:
            print(
                f"   Scanned: {scanned_files}/{len(folders)} files ({len(url_to_content):,} URLs found)",
                end="\r",
            )

    except:
        continue

print(f"\n   ✅ Found content for {len(url_to_content):,} URLs")

# Embed and upload
print(f"\n🚀 Embedding and uploading...")
points = []
point_id = 0
batch_size = 64

urls = list(url_to_content.keys())
texts = [url_to_content[url]["text"] for url in urls]

embedded = 0
for i in range(0, len(urls), batch_size):
    batch_urls = urls[i : i + batch_size]
    batch_texts = texts[i : i + batch_size]

    # Embed
    embeddings = model.encode(
        batch_texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
    )

    # Create points
    for url, embedding in zip(batch_urls, embeddings):
        data = url_to_content[url]
        payload = {
            "url": url,
            "title": data["title"],
            "content_length": data["content_length"],
            "document_type": data["document_type"],
            "status": data["status"],
        }

        points.append(
            PointStruct(id=point_id, vector=embedding.tolist(), payload=payload)
        )
        point_id += 1

    # Upload in chunks of 100
    if len(points) >= 100:
        client.upsert(collection_name=NEW_COLLECTION, points=points[:100], wait=True)
        embedded += 100
        points = points[100:]
        print(
            f"   Uploaded: {embedded:,}/{len(urls):,} ({embedded/len(urls)*100:.1f}%)",
            end="\r",
        )

# Upload remaining
if points:
    client.upsert(collection_name=NEW_COLLECTION, points=points, wait=True)
    embedded += len(points)

print(f"\n   ✅ Uploaded {embedded:,} unique documents")

# Verify
info = client.get_collection(NEW_COLLECTION)
print(f"\n📊 New collection: {info.points_count:,} documents (no duplicates!)")

print("\n" + "=" * 70)
print("✅ RECREATION COMPLETE!")
print("=" * 70)
print(f"New collection name: {NEW_COLLECTION}")
print("\nUpdate test_traffic_laws.py to use: traffic_laws_clean")
