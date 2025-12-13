"""Simple fix: Delete corrupt collection and re-run embed script"""

from qdrant_client import QdrantClient

print("=" * 70)
print("🧹 Deleting Corrupt Collection")
print("=" * 70)

client = QdrantClient(url="http://localhost:6333", timeout=60)

# Delete the corrupt collection
print("\n🗑️ Deleting traffic_laws_only collection...")
try:
    client.delete_collection("traffic_laws_only")
    print("   ✅ Deleted")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n📊 Checking collections...")
collections = client.get_collections().collections
print(f"   Collections: {len(collections)}")
for c in collections:
    print(f"      - {c.name}")

if len(collections) == 0:
    print("\n✅ All clean! Now run:")
    print("   1. Delete processed_traffic_files.txt")
    print("   2. Run: python embed_traffic_laws_v2.py")
    print("\n   This will re-embed WITHOUT duplicates!")
else:
    print("\n⚠️ Still have collections, manually delete them")

print("\n" + "=" * 70)
