"""
Quick script to check what years are stored in the Qdrant database
"""

from qdrant_client import QdrantClient
from collections import Counter

# Connect to Qdrant
client = QdrantClient(host="localhost", port=6333)

# Get collection info
try:
    info = client.get_collection("traffic_laws_only")
    total_docs = info.points_count
    print(f"📊 Total documents in collection: {total_docs:,}")
    print("=" * 70)

    # Sample documents to check years
    print("\n🔍 Sampling documents to check year distribution...")

    # Scroll through all documents
    offset = None
    year_counter = Counter()
    doc_samples = []
    sample_limit = 20  # Show 20 examples

    while True:
        results = client.scroll(
            collection_name="traffic_laws_only",
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        points, next_offset = results

        if not points:
            break

        for point in points:
            year = point.payload.get("year", 0)
            year_counter[year] += 1

            # Collect samples for display
            if len(doc_samples) < sample_limit:
                doc_samples.append(
                    {
                        "title": point.payload.get("title", "No title")[:80],
                        "year": year,
                        "url": point.payload.get("url", ""),
                    }
                )

        if next_offset is None:
            break
        offset = next_offset

    # Display year distribution
    print("\n📅 Year Distribution:")
    print("-" * 70)
    for year in sorted(year_counter.keys(), reverse=True):
        count = year_counter[year]
        percentage = (count / total_docs) * 100
        bar = "█" * int(percentage / 2)
        print(f"{year}: {count:>4} docs ({percentage:>5.1f}%) {bar}")

    # Show sample documents
    print("\n📄 Sample Documents:")
    print("-" * 70)
    for i, doc in enumerate(doc_samples, 1):
        print(f"\n{i}. [{doc['year']}] {doc['title']}")
        print(f"   URL: {doc['url'][:70]}...")

    # Check for documents with year 2024-2025
    recent_count = sum(count for year, count in year_counter.items() if year >= 2024)
    print("\n" + "=" * 70)
    print(
        f"✅ Documents from 2024-2025: {recent_count} ({recent_count/total_docs*100:.1f}%)"
    )
    print(
        f"⚠️  Documents before 2024: {total_docs - recent_count} ({(total_docs - recent_count)/total_docs*100:.1f}%)"
    )

    # Search for Nghị định 168/2024
    print("\n🔍 Searching for 'Nghị định 168/2024'...")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("keepitreal/vietnamese-sbert")

    query_embedding = model.encode("Nghị định 168/2024").tolist()
    search_results = client.query_points(
        collection_name="traffic_laws_only", query=query_embedding, limit=5
    ).points

    print(f"\nTop {len(search_results)} results:")
    for i, result in enumerate(search_results, 1):
        print(
            f"\n{i}. [{result.payload.get('year')}] {result.payload.get('title', 'No title')[:100]}"
        )
        print(f"   Score: {result.score:.4f}")
        print(f"   URL: {result.payload.get('url', '')[:80]}...")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
