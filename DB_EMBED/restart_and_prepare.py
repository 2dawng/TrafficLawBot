"""Complete solution: Restart Qdrant and create working collection"""

import subprocess
import time
import sys

print("=" * 70)
print("🔧 Complete Fix for Overloaded Qdrant")
print("=" * 70)

print("\n1. Restarting Qdrant container...")
try:
    result = subprocess.run(
        ["docker", "restart", "qdrant"], capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        print("✅ Qdrant restarted")
    else:
        print(f"❌ Error: {result.stderr}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Error restarting: {e}")
    print("\nManually run: docker restart qdrant")
    sys.exit(1)

print("\n2. Waiting for Qdrant to start (60 seconds)...")
for i in range(60, 0, -10):
    print(f"   {i} seconds remaining...")
    time.sleep(10)

print("\n3. Checking if Qdrant is ready...")
import requests

try:
    r = requests.get("http://localhost:6333/", timeout=10)
    if r.status_code == 200:
        print("✅ Qdrant is responding!")
    else:
        print(f"⚠️ Qdrant returned status: {r.status_code}")
except Exception as e:
    print(f"❌ Qdrant not ready yet: {e}")
    print("Wait another minute and try again")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ Qdrant is ready!")
print("=" * 70)
print("\nNext step: Create fast collection")
print("Run: python create_fast_collection_v2.py")
