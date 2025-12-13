"""Simple test - query just 1 result to see if it works"""

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import torch

print("=" * 70)
print("🧪 Simple Test - Just Get 1 Result")
print("=" * 70)

print("\n1. Loading model...")
model = SentenceTransformer("keepitreal/vietnamese-sbert")
if torch.cuda.is_available():
    model = model.to("cuda")
    print("   ✅ Using GPU")

print("\n2. Connecting to Qdrant (with long timeout)...")
client = QdrantClient(url="http://localhost:6333", timeout=600)  # 10 min timeout

print("\n3. Encoding a simple query...")
query = "Giấy phép lái xe"
print(f"   Query: '{query}'")
query_vector = model.encode(query).tolist()
print("   ✅ Query encoded")

print("\n4. Searching for just 1 result (this may take 1-5 minutes)...")
print("   ⏳ Please wait...")

try:
    results = client.query_points(
        collection_name="vietnamese_legal_content",
        query=query_vector,
        limit=1,  # Just get 1 result
        with_payload=True,
        timeout=600,
    ).points

    if results:
        print("\n" + "=" * 70)
        print("✅ SUCCESS! IT WORKS!")
        print("=" * 70)

        result = results[0]
        print(f"\nScore: {result.score:.4f}")
        print(f"Title: {result.payload.get('title', 'N/A')[:200]}")
        print(f"URL: {result.payload.get('url', 'N/A')}")
        print(f"Content length: {result.payload.get('content_length', 0)} chars")

        content = result.payload.get("content", "")[:300]
        print(f"\nContent preview:\n{content}...")

        print("\n" + "=" * 70)
        print("🎉 Your collection works! It's just SLOW with 16GB RAM")
        print("   With 24GB RAM, this will be < 1 second instead of minutes")
        print("=" * 70)
    else:
        print("\n❌ No results found")

except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nThis means Qdrant is too overloaded even for 1 result.")
    print("Recommendation: Restart Qdrant and try again")
    print("  docker restart qdrant")

print("\nDone!")
