"""Create fast collection - Version 2 with better error handling"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import time

print("=" * 70)
print("🚀 Creating Fast Working Collection (v2)")
print("=" * 70)

# Connect with very long timeout
client = QdrantClient(url="http://localhost:6333", timeout=600)

new_collection = "vietnamese_legal_fast"

# Step 1: Delete if exists
print("\n1. Cleaning up old collection...")
try:
    client.delete_collection(new_collection)
    print("   Deleted old collection")
    time.sleep(2)
except:
    print("   No old collection to delete")

# Step 2: Create new simple collection
print("\n2. Creating new collection (simplified)...")
try:
    client.create_collection(
        collection_name=new_collection,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )
    print("✅ Collection created!")
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nQdrant is still too busy. Try these options:")
    print("\nOption A: Wait and restart everything")
    print("  1. docker stop qdrant")
    print("  2. Wait 2 minutes")
    print("  3. docker start qdrant")
    print("  4. Wait 2 minutes")
    print("  5. Try again")
    print("\nOption B: Just use a smaller filtered subset")
    print("  I can create a script that reads from your JSON files directly")
    print("  and creates a NEW Qdrant with only 100K docs")
    exit(1)

# Step 3: Copy data in small batches
print("\n3. Starting to copy documents...")
print("   This will copy in small batches to avoid overload")

old_collection = "vietnamese_legal_content"
copied = 0
batch_size = 50  # Very small batches
max_docs = 100000

try:
    offset = None

    while copied < max_docs:
        print(f"   Copying batch {copied//batch_size + 1}... ({copied:,} docs so far)")

        # Get batch from old collection
        result = client.scroll(
            collection_name=old_collection,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=True,
            scroll_filter=None,  # No filter for now, just get any docs
        )

        points, offset = result

        if not points:
            print(f"\n   Reached end at {copied:,} documents")
            break

        # Upload to new collection
        client.upsert(
            collection_name=new_collection,
            points=points,
            wait=True,  # Wait for each batch
        )

        copied += len(points)

        if copied >= max_docs:
            break

        time.sleep(0.5)  # Small delay between batches

except Exception as e:
    print(f"\n❌ Error at {copied:,} documents: {e}")
    print(f"\nBut we got {copied:,} documents - might be usable!")

print(f"\n✅ Copied {copied:,} documents")
print("\nTest with: python test_fast_collection.py")
print("=" * 70)
