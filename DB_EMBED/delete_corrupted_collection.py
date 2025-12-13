"""
Delete corrupted collection and start fresh
"""

from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)

try:
    # Delete corrupted collection
    print("🗑️  Deleting corrupted collection: traffic_laws_only")
    client.delete_collection("traffic_laws_only")
    print("✅ Collection deleted successfully!")
    print("\nℹ️  Next steps:")
    print("1. Run the embedding script to recreate the collection")
    print("2. The script will process all traffic law documents again")
    print("3. This should take about 3-5 minutes")

except Exception as e:
    print(f"❌ Error: {e}")
