"""
Simple test to check if Qdrant search is working
"""

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Connect to Qdrant
client = QdrantClient(host="localhost", port=6333)

try:
    # Get collection info
    info = client.get_collection("traffic_laws_only")
    print(f"✅ Qdrant is running")
    print(f"📊 Total documents: {info.points_count:,}")
    print("=" * 70)

    # Load model
    print("\n🔄 Loading embedding model...")
    model = SentenceTransformer("keepitreal/vietnamese-sbert")

    # Test search for specific document: Thông tư 35/2024
    print("\n🔍 Testing search: 'Thông tư 35/2024'")
    query = "Thông tư 35/2024"
    query_embedding = model.encode(query).tolist()

    search_results = client.query_points(
        collection_name="traffic_laws_only",
        query=query_embedding,
        limit=10,
        with_payload=True,
    ).points

    print(f"\n✅ Found {len(search_results)} results:")
    print("-" * 70)

    for i, result in enumerate(search_results, 1):
        year = result.payload.get("year", "N/A")
        title = result.payload.get("title", "No title")[:100]
        score = result.score

        print(f"\n{i}. [Year: {year}] Score: {score:.4f}")
        print(f"   {title}")
        print(f"   URL: {result.payload.get('url', '')[:80]}...")

    print("\n" + "=" * 70)
    print("✅ Search is working!")
    print(
        "\nℹ️  If your backend shows 'No relevant documents found', restart it to pick up the code changes."
    )

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
