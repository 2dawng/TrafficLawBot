"""NUCLEAR OPTION - Completely wipe and restart"""

import subprocess
import time
import os
import shutil

print("=" * 70)
print("☢️ NUCLEAR RESTART - Complete Wipe")
print("=" * 70)

# Step 1: Kill container
print("\n1. Stopping container...")
subprocess.run(["docker", "stop", "qdrant"], capture_output=True, timeout=10)
print("   ✅ Stopped")

print("\n2. Removing container...")
subprocess.run(["docker", "rm", "qdrant"], capture_output=True, timeout=10)
print("   ✅ Removed")

# Step 2: COMPLETELY DELETE storage
storage_path = r"D:\qdrant_traffic_laws"
print(f"\n3. DELETING ALL DATA: {storage_path}")
if os.path.exists(storage_path):
    try:
        shutil.rmtree(storage_path, ignore_errors=True)
        time.sleep(2)
        print("   ✅ Deleted")
    except Exception as e:
        print(f"   ⚠️ Error: {e}")

# Step 3: Wait a moment
time.sleep(2)

# Step 4: Create truly empty directory
print(f"\n4. Creating EMPTY storage...")
os.makedirs(storage_path, exist_ok=True)
print("   ✅ Empty directory created")

# Verify it's empty
items = os.listdir(storage_path)
if len(items) == 0:
    print("   ✅ Verified EMPTY")
else:
    print(f"   ⚠️ WARNING: {len(items)} items still exist!")

# Step 5: Start container
print("\n5. Starting NEW container...")
cmd = [
    "docker",
    "run",
    "-d",
    "-p",
    "6333:6333",
    "-p",
    "6334:6334",
    "-v",
    f"{storage_path}:/qdrant/storage",
    "--name",
    "qdrant",
    "qdrant/qdrant",
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
if result.returncode == 0:
    print(f"   ✅ Started! ID: {result.stdout.strip()[:12]}")
else:
    print(f"   ❌ Error: {result.stderr}")
    exit(1)

# Step 6: Wait for startup
print("\n6. Waiting 20 seconds for Qdrant to initialize...")
time.sleep(20)

# Step 7: Test
print("\n7. Testing connection...")
import requests

try:
    r = requests.get("http://localhost:6333/collections", timeout=10)
    if r.status_code == 200:
        collections = r.json()["result"]["collections"]
        print(f"   ✅ Qdrant is READY!")
        print(f"   Collections: {len(collections)} (should be 0)")
        if len(collections) == 0:
            print("   ✅ PERFECT - Truly empty!")
        else:
            print(f"   ⚠️ Has collections: {collections}")
    else:
        print(f"   ⚠️ Status: {r.status_code}")
except Exception as e:
    print(f"   ❌ Error: {e}")
    print("   Wait another minute and try: python test_long_timeout.py")

print("\n" + "=" * 70)
print("✅ NUCLEAR RESTART COMPLETE!")
print("=" * 70)
print(f"Storage: {storage_path} (EMPTY)")
print("Now run: python embed_traffic_laws_v2.py")
print("=" * 70)
