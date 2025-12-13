"""Create payload indexes for faster filtered searches"""

from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType

client = QdrantClient(url="http://localhost:6333")
collection_name = "vietnamese_legal_content"

print("=" * 70)
print("🔧 Creating Payload Indexes")
print("=" * 70)

# Fields to index for faster filtering
indexes_to_create = [
    ("content_length", PayloadSchemaType.INTEGER),
    ("type", PayloadSchemaType.KEYWORD),
    ("status", PayloadSchemaType.KEYWORD),
    ("document_type", PayloadSchemaType.KEYWORD),
]

for field_name, schema_type in indexes_to_create:
    try:
        print(f"\nCreating index for field: '{field_name}'...")
        client.create_payload_index(
            collection_name=collection_name,
            field_name=field_name,
            field_schema=schema_type,
        )
        print(f"✅ Index created for '{field_name}'")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"⚠️ Index for '{field_name}' already exists")
        else:
            print(f"❌ Error creating index for '{field_name}': {e}")

print("\n" + "=" * 70)
print("✅ Payload index creation completed!")
print("=" * 70)
print("\nIndexes will speed up filtered queries like:")
print("  - Filter by content_length >= 1000")
print("  - Filter by document_type = 'law'")
print("  - Filter by status = 'active'")
