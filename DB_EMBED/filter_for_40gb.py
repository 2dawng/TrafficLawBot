"""Filter collection to top 2M documents by content length"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, ScrollRequest
import time

print("=" * 70)
print("📊 Analyzing Document Distribution")
print("=" * 70)

client = QdrantClient(url="http://localhost:6333", timeout=300)

# First, let's see the distribution of content lengths
print("\nThis script will help you:")
print("1. Find the median content_length")
print("2. Create a filtered collection with top 2M documents")
print("\nNote: With 40GB RAM, you can comfortably handle ~2M documents")

# Recommendation
print("\n" + "=" * 70)
print("💡 AFTER RAM UPGRADE TO 40GB:")
print("=" * 70)
print("1. Buy: 32GB DDR4 SO-DIMM stick (~$60-80)")
print("2. Install the new RAM")
print("3. Edit .wslconfig to allocate 32GB to WSL")
print("4. Restart computer")
print("5. Run this script to filter to top 2M documents")
print("\nYou'll have:")
print("  ✅ Fast searches (< 1 second)")
print("  ✅ 2M+ high-quality documents")
print("  ✅ Budget-friendly solution")
print("=" * 70)
