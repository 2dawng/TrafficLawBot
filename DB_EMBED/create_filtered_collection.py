"""Create a smaller filtered collection for better performance"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, Filter, FieldCondition, Range
import time

client = QdrantClient(url="http://localhost:6333", timeout=300)

print("=" * 70)
print("🔧 Creating Filtered Collection (Top Quality Documents)")
print("=" * 70)

# Create new smaller collection
new_collection = "vietnamese_legal_content_filtered"

print(f"\n1. Creating new collection: {new_collection}")
try:
    client.create_collection(
        collection_name=new_collection,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )
    print("✅ Collection created")
except Exception as e:
    print(f"⚠️ Collection might already exist: {e}")

# Strategy: Copy only documents with content_length > 1000 characters
# This will give you higher quality documents and reduce from 5.5M to ~500K-1M

print("\n2. This would scroll and copy only long documents (content_length > 1000)")
print("   Estimated result: ~500K-1M high-quality documents")
print("   This will take 2-4 hours to complete")
print("\nTo proceed, you would need to run a scroll + copy operation")
print("But your laptop might struggle with this too")

print("\n" + "=" * 70)
print("💡 RECOMMENDATION: Use Qdrant Cloud or a VPS instead")
print("=" * 70)
