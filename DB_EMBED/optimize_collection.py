"""Optimize Qdrant collection for better performance"""

import requests
import json
import time

print("=" * 70)
print("🔧 Optimizing Qdrant Collection")
print("=" * 70)

# Update collection config for better performance
config_update = {
    "optimizers_config": {
        "indexing_threshold": 10000,  # Start indexing after 10k points
        "memmap_threshold": 20000,  # Use memory mapping for large datasets
    },
    "hnsw_config": {
        "m": 16,  # Connections per layer (lower = faster but less accurate)
        "ef_construct": 100,  # Index build quality
        "full_scan_threshold": 10000,  # When to use full scan vs index
    },
}

print("\nUpdating collection configuration...")
try:
    response = requests.patch(
        "http://localhost:6333/collections/vietnamese_legal_content",
        json=config_update,
        timeout=180,
    )
    if response.status_code == 200:
        print("✅ Configuration updated")
    else:
        print(f"❌ Update failed: {response.status_code}")
        print(response.text[:500])
except Exception as e:
    print(f"❌ Error: {e}")

print("\n⏳ Waiting for optimization to complete (this may take 10-30 minutes)...")
print("   You can check progress at: http://localhost:6333/dashboard")
print("=" * 70)
