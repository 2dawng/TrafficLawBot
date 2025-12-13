"""Verify Qdrant is truly clean and working"""

import subprocess
import requests
import time

print("=" * 70)
print("🔍 QDRANT DIAGNOSTIC")
print("=" * 70)

# Check container
print("\n1. Checking Docker container...")
result = subprocess.run(["docker", "ps"], capture_output=True, text=True)
if "qdrant" in result.stdout:
    print("   ✅ Container running")

    # Get mount info
    mount_result = subprocess.run(
        [
            "docker",
            "inspect",
            "qdrant",
            "--format",
            "{{range .Mounts}}{{.Source}} -> {{.Destination}}{{end}}",
        ],
        capture_output=True,
        text=True,
    )
    print(f"   📁 Storage: {mount_result.stdout.strip()}")

    if "qdrant_storage" in mount_result.stdout:
        print("   ❌ ERROR: Still using OLD storage (qdrant_storage)!")
        print("   Should be: D:\\qdrant_traffic_laws")
    elif "qdrant_traffic_laws" in mount_result.stdout:
        print("   ✅ Using correct storage (qdrant_traffic_laws)")
else:
    print("   ❌ Container NOT running")
    exit(1)

# Check Qdrant API
print("\n2. Testing Qdrant API...")
try:
    r = requests.get("http://localhost:6333/collections", timeout=10)
    print(f"   Status: {r.status_code}")

    if r.status_code == 200:
        data = r.json()
        collections = data.get("result", {}).get("collections", [])
        print(f"   Collections: {len(collections)}")

        if len(collections) == 0:
            print("   ✅ EMPTY - Ready for fresh data!")
        else:
            for coll in collections:
                print(f"      - {coll['name']}: {coll.get('points_count', 0):,} docs")

            # Check if traffic_laws_only exists
            traffic_coll = next(
                (c for c in collections if c["name"] == "traffic_laws_only"), None
            )
            if traffic_coll:
                count = traffic_coll.get("points_count", 0)
                if count == 0:
                    print("   ✅ traffic_laws_only exists but EMPTY")
                elif count > 100000:
                    print(
                        f"   ❌ ERROR: traffic_laws_only has {count:,} docs (should be < 100K)"
                    )
                    print("   This means it's still using OLD data!")
                else:
                    print(f"   ✅ traffic_laws_only has {count:,} docs")
    else:
        print(f"   ❌ Bad status: {r.status_code}")

except requests.exceptions.Timeout:
    print("   ❌ TIMEOUT - Qdrant is overloaded!")
    print("   This means it's loading the old 5.5M collection")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n3. Recommendation:")
print("=" * 70)

# Check if we need full restart
try:
    r = requests.get("http://localhost:6333/collections", timeout=5)
    if r.status_code == 200:
        collections = r.json().get("result", {}).get("collections", [])
        if len(collections) == 0:
            print("✅ Qdrant is READY - Run: python embed_traffic_laws_v2.py")
        else:
            total_docs = sum(c.get("points_count", 0) for c in collections)
            if total_docs > 1000000:
                print("❌ DELETE OLD DATA - Run: python restart_clean_qdrant.py")
            else:
                print("✅ Qdrant looks OK - Run: python embed_traffic_laws_v2.py")
    else:
        print("❌ RESTART NEEDED - Run: python restart_clean_qdrant.py")
except:
    print("❌ QDRANT STUCK - Run: python restart_clean_qdrant.py")

print("=" * 70)
