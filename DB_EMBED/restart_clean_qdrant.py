"""Completely restart Qdrant with EMPTY storage"""

import subprocess
import time
import os
import shutil

print("=" * 70)
print("🧹 CLEAN RESTART QDRANT")
print("=" * 70)

# Step 1: Stop and remove container
print("\n1. Stopping Qdrant...")
subprocess.run(["docker", "stop", "qdrant"], capture_output=True)
print("   ✅ Stopped")

print("\n2. Removing container...")
subprocess.run(["docker", "rm", "qdrant"], capture_output=True)
print("   ✅ Removed")

# Step 2: Delete OLD storage (COMPLETELY)
old_storage = r"D:\qdrant_traffic_laws"
if os.path.exists(old_storage):
    print(f"\n3. Deleting old storage: {old_storage}")
    try:
        shutil.rmtree(old_storage)
        print("   ✅ Deleted")
    except Exception as e:
        print(f"   ⚠️ Error deleting: {e}")
        print("   Manually delete the folder if needed")

# Step 3: Create fresh empty directory
print(f"\n4. Creating fresh storage: {old_storage}")
os.makedirs(old_storage, exist_ok=True)
print("   ✅ Created empty directory")

# Step 4: Start NEW Qdrant with EMPTY storage
print("\n5. Starting NEW Qdrant container...")
cmd = [
    "docker",
    "run",
    "-d",
    "-p",
    "6333:6333",
    "-p",
    "6334:6334",
    "-v",
    f"{old_storage}:/qdrant/storage",
    "--name",
    "qdrant",
    "qdrant/qdrant",
]

result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode == 0:
    print("   ✅ Started!")
    print(f"   Container ID: {result.stdout.strip()[:12]}")
else:
    print(f"   ❌ Error: {result.stderr}")
    exit(1)

# Step 6: Wait for startup
print("\n6. Waiting for Qdrant to be ready (20 seconds)...")
time.sleep(20)

# Step 7: Test connection
print("\n7. Testing connection...")
import requests

try:
    r = requests.get("http://localhost:6333/collections", timeout=10)
    if r.status_code == 200:
        collections = r.json()["result"]["collections"]
        print(f"   ✅ Qdrant is ready!")
        print(f"   Collections: {len(collections)} (should be 0)")
    else:
        print(f"   ⚠️ Status: {r.status_code}")
except Exception as e:
    print(f"   ⚠️ Not ready: {e}")

print("\n" + "=" * 70)
print("✅ CLEAN QDRANT READY!")
print("=" * 70)
print(f"Storage: {old_storage} (EMPTY)")
print("Dashboard: http://localhost:6333/dashboard")
print("\nNow run: python embed_traffic_laws_only.py")
print("=" * 70)
