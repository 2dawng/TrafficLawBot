"""Remove duplicate documents from Qdrant collection"""

from qdrant_client import QdrantClient
from collections import defaultdict

print("=" * 70)
print("🧹 Removing Duplicates from Collection")
print("=" * 70)

client = QdrantClient(url="http://localhost:6333", timeout=60)
collection_name = "traffic_laws_only"

# Get collection info
info = client.get_collection(collection_name)
total_docs = info.points_count
print(f"\n📊 Current collection: {total_docs:,} documents")

print("\n🔍 Scanning for duplicates...")
print("   (This may take a few minutes)")

# Scroll through all points
url_to_ids = defaultdict(list)
offset = None
batch_size = 100
scanned = 0

while True:
    results = client.scroll(
        collection_name=collection_name,
        limit=batch_size,
        offset=offset,
        with_payload=True,
        with_vectors=False,
    )

    points, next_offset = results

    if not points:
        break

    for point in points:
        url = point.payload.get("url", "")
        if url:
            url_to_ids[url].append(point.id)

    scanned += len(points)
    print(
        f"   Scanned: {scanned:,}/{total_docs:,} ({scanned/total_docs*100:.1f}%)",
        end="\r",
    )

    if next_offset is None:
        break
    offset = next_offset

print(f"\n   ✅ Scanned all {scanned:,} documents")

# Find duplicates
duplicates_to_delete = []
unique_urls = 0
duplicate_count = 0

for url, ids in url_to_ids.items():
    if len(ids) > 1:
        # Keep the first ID, delete the rest
        duplicates_to_delete.extend(ids[1:])
        duplicate_count += len(ids) - 1
    unique_urls += 1

print(f"\n📊 Results:")
print(f"   Unique URLs: {unique_urls:,}")
print(f"   Duplicate documents: {duplicate_count:,}")
print(f"   Will keep: {total_docs - duplicate_count:,} documents")

if duplicate_count == 0:
    print("\n✅ No duplicates found!")
    exit(0)

# Delete duplicates
print(f"\n🗑️ Deleting {duplicate_count:,} duplicate documents...")
batch_size = 100
deleted = 0

for i in range(0, len(duplicates_to_delete), batch_size):
    batch = duplicates_to_delete[i : i + batch_size]
    client.delete(collection_name=collection_name, points_selector=batch)
    deleted += len(batch)
    print(
        f"   Deleted: {deleted:,}/{duplicate_count:,} ({deleted/duplicate_count*100:.1f}%)",
        end="\r",
    )

print(f"\n   ✅ Deleted {deleted:,} duplicates")

# Verify
info = client.get_collection(collection_name)
final_count = info.points_count
print(f"\n📊 Final collection: {final_count:,} documents")
print(f"   Removed: {total_docs - final_count:,} duplicates")

print("\n" + "=" * 70)
print("✅ CLEANUP COMPLETE!")
print("=" * 70)
print("\nTest again with: python test_traffic_laws.py")
