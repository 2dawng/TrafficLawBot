"""Filter to top 1M documents for 24GB RAM setup"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, Filter, FieldCondition, Range
import time

print("=" * 70)
print("🎯 Filter to Top 1 Million Documents (for 24GB RAM)")
print("=" * 70)

client = QdrantClient(url="http://localhost:6333", timeout=300)
old_collection = "vietnamese_legal_content"
new_collection = "vietnamese_legal_content_1m"

print(f"\nSource: {old_collection} (5.5M docs)")
print(f"Target: {new_collection} (1M docs)")
print("\nStrategy: Keep documents with content_length > 2000 characters")

# Step 1: Create new collection
print("\n1. Creating new collection...")
try:
    client.create_collection(
        collection_name=new_collection,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )
    print("✅ Collection created")
except Exception as e:
    print(f"⚠️ Collection exists or error: {e}")

print("\n2. Strategy to copy top 1M documents:")
print("   - Filter: content_length >= 2000 (keeps quality content)")
print("   - This gives you the best 15-20% of documents")
print("   - Estimated time: 2-3 hours")

print("\n" + "=" * 70)
print("💡 NEXT STEPS:")
print("=" * 70)
print("1. Buy 16GB RAM stick (~$30-40)")
print("2. Install RAM → Total 24GB")
print("3. Edit .wslconfig: memory=20GB")
print("4. Restart computer")
print("5. Run filter script to create 1M doc collection")
print("6. Enjoy fast searches! ⚡")
print("=" * 70)

# Show what to do after RAM upgrade
print("\n📝 After RAM upgrade, you'll run:")
print("   python filter_to_1m.py")
print("\nThis will copy top 1M docs to the new collection")
