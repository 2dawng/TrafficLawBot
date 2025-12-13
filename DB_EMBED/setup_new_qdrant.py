"""Setup new Qdrant for traffic laws only"""

import subprocess
import os
import time

print("=" * 70)
print("🚀 Setting Up Clean Qdrant for Traffic Laws")
print("=" * 70)

# Step 1: Stop old Qdrant
print("\n1. Stopping old Qdrant container...")
try:
    subprocess.run(["docker", "stop", "qdrant"], capture_output=True, timeout=30)
    print("   ✅ Old container stopped")
except:
    print("   ⚠️ No old container or already stopped")

# Step 2: Remove old container
print("\n2. Removing old container...")
try:
    subprocess.run(["docker", "rm", "qdrant"], capture_output=True, timeout=30)
    print("   ✅ Old container removed")
except:
    print("   ⚠️ No old container to remove")

# Step 3: Create new storage directory
storage_path = r"D:\qdrant_traffic_laws"
print(f"\n3. Creating storage directory: {storage_path}")
os.makedirs(storage_path, exist_ok=True)
print("   ✅ Directory created")

# Step 4: Start new Qdrant container
print("\n4. Starting new Qdrant container...")
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

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode == 0:
        print("   ✅ New Qdrant started!")
        container_id = result.stdout.strip()[:12]
        print(f"   Container ID: {container_id}")
    else:
        print(f"   ❌ Error: {result.stderr}")
        exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# Step 5: Wait for Qdrant to be ready
print("\n5. Waiting for Qdrant to start (30 seconds)...")
time.sleep(30)

print("\n6. Testing connection...")
import requests

try:
    r = requests.get("http://localhost:6333/", timeout=10)
    if r.status_code == 200:
        print("   ✅ Qdrant is ready!")
    else:
        print(f"   ⚠️ Status: {r.status_code}")
except Exception as e:
    print(f"   ⚠️ Not ready yet: {e}")
    print("   Wait another minute and continue")

print("\n" + "=" * 70)
print("✅ New Qdrant Setup Complete!")
print("=" * 70)
print(f"\nStorage location: {storage_path}")
print("Dashboard: http://localhost:6333/dashboard")
print("\nNext: python embed_traffic_laws_only.py")
print("=" * 70)
