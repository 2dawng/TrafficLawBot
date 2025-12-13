"""
Embed Vietnamese legal documents to LOCAL Qdrant

This version:
- Works with local Qdrant (Docker or standalone)
- Filters out empty content (content_length = 0)
- Handles large datasets efficiently
- No API key needed for local setup

Requirements:
- Qdrant running locally on port 6333
- Run: docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant

Usage:
    python embed_local.py
"""

import os
import json
import glob
from typing import List, Dict
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer


class LocalContentEmbedder:
    """Embed legal documents to local Qdrant instance"""

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "vietnamese_legal_content",
        embedding_model: str = "keepitreal/vietnamese-sbert",
    ):
        """
        Initialize local Qdrant client and embedding model

        Args:
            qdrant_url: Local Qdrant URL (default: localhost:6333)
            collection_name: Collection name
            embedding_model: Vietnamese embedding model
        """
        print(f"Connecting to local Qdrant at: {qdrant_url}")
        self.client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name

        print(f"Loading embedding model: {embedding_model}")
        self.encoder = SentenceTransformer(embedding_model)
        self.vector_size = self.encoder.get_sentence_embedding_dimension()

        self._create_collection()

    def _create_collection(self):
        """Create or recreate Qdrant collection"""
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            print(f"Deleted existing collection: {self.collection_name}")
        except:
            pass

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size, distance=Distance.COSINE
            ),
        )
        print(
            f"✅ Created collection: {self.collection_name} (vector size: {self.vector_size})"
        )

    def load_content_files(
        self,
        folder_pattern: str = "traffic_laws_WITH_CONTENT_*",
        min_content_length: int = 1,  # Skip empty content
    ) -> List[Dict]:
        """
        Load documents from JSON files with content filtering

        Args:
            folder_pattern: Pattern to match folders
            min_content_length: Minimum content length (default: 1 = skip empty)

        Returns:
            List of document dictionaries
        """
        documents = []
        stats = {
            "total": 0,
            "with_content": 0,
            "empty_content": 0,
            "too_short": 0,
        }

        # Find all folders matching pattern
        folders = glob.glob(folder_pattern)
        print(f"\n📁 Found {len(folders)} folders matching pattern: {folder_pattern}")

        for folder in folders:
            json_files = glob.glob(os.path.join(folder, "*.json"))

            for json_file in json_files:
                print(f"\r📄 Loading: {json_file:<80}", end="", flush=True)

                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Handle both list and single object
                    items = data if isinstance(data, list) else [data]

                    for item in items:
                        stats["total"] += 1

                        # Get content and content_length
                        content = item.get("content", "").strip()
                        content_length = item.get("content_length", len(content))

                        # IMPORTANT: Skip if content_length is 0 or content is empty
                        if content_length == 0 or not content:
                            stats["empty_content"] += 1
                            continue

                        # Skip if content is too short
                        if content_length < min_content_length:
                            stats["too_short"] += 1
                            continue

                        stats["with_content"] += 1

                        # Create document (excluding date and number)
                        doc = {
                            "url": item.get("url", ""),
                            "title": item.get("title", ""),
                            "type": item.get("type", ""),
                            "status": item.get("status", ""),
                            "content": content,
                            "content_length": content_length,
                            "document_type": item.get("document_type", ""),
                            "source_file": os.path.basename(json_file),
                        }

                        documents.append(doc)

                except json.JSONDecodeError as e:
                    print(f"\n❌ Error parsing {json_file}: {e}")
                except Exception as e:
                    print(f"\n❌ Error loading {json_file}: {e}")

        print("\n")  # New line after loading
        print(f"\n📊 Loading Statistics:")
        print(f"  - Total documents scanned: {stats['total']:,}")
        print(f"  - With valid content: {stats['with_content']:,}")
        print(f"  - Empty content (skipped): {stats['empty_content']:,}")
        print(f"  - Too short (skipped): {stats['too_short']:,}")
        print(f"  - Loaded for embedding: {len(documents):,}")

        return documents

    def prepare_text_for_embedding(self, doc: Dict) -> str:
        """Prepare document text for embedding"""
        parts = []

        # Add title if exists
        title = doc.get("title", "").strip()
        if title and title != "thuvienphapluat.vn":
            parts.append(f"Tiêu đề: {title}")

        # Add content (main part)
        content = doc.get("content", "").strip()
        if content:
            # Truncate if too long
            max_content_length = 8000
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
            parts.append(content)

        return " | ".join(parts) if parts else ""

    def embed_documents(self, documents: List[Dict], batch_size: int = 32):
        """
        Embed documents and upload to Qdrant

        Args:
            documents: List of document dictionaries
            batch_size: Number of documents to process at once
        """
        if not documents:
            print("⚠️ No documents to embed")
            return

        print(f"\n🔄 Embedding {len(documents):,} documents...")

        # Prepare texts for embedding
        texts = [self.prepare_text_for_embedding(doc) for doc in documents]

        # Filter out empty texts
        valid_docs = [
            (doc, text) for doc, text in zip(documents, texts) if text.strip()
        ]
        print(f"Valid documents (non-empty): {len(valid_docs):,}")

        if not valid_docs:
            print("⚠️ No valid documents to embed")
            return

        # Generate embeddings in batches
        points = []
        total_batches = (len(valid_docs) + batch_size - 1) // batch_size

        for i in range(0, len(valid_docs), batch_size):
            batch = valid_docs[i : i + batch_size]
            batch_docs = [item[0] for item in batch]
            batch_texts = [item[1] for item in batch]

            current_batch = i // batch_size + 1
            progress = (current_batch / total_batches) * 100
            print(
                f"Processing batch {current_batch}/{total_batches} ({progress:.1f}%)...",
                end="\r",
                flush=True,
            )

            try:
                # Generate embeddings
                embeddings = self.encoder.encode(
                    batch_texts, show_progress_bar=False, batch_size=batch_size
                )

                # Create points
                for j, (doc, embedding) in enumerate(zip(batch_docs, embeddings)):
                    point_id = i + j
                    points.append(
                        PointStruct(id=point_id, vector=embedding.tolist(), payload=doc)
                    )

                # Upload in chunks of 1000 to avoid memory issues
                if len(points) >= 1000:
                    print(f"\n⬆️ Uploading {len(points):,} points to Qdrant...")
                    self.client.upsert(
                        collection_name=self.collection_name, points=points
                    )
                    print(f"✅ Uploaded successfully")
                    points = []  # Clear for next batch

            except Exception as e:
                print(f"\n❌ Error processing batch {current_batch}: {e}")
                continue

        # Upload remaining points
        if points:
            print(f"\n⬆️ Uploading final {len(points):,} points to Qdrant...")
            try:
                self.client.upsert(collection_name=self.collection_name, points=points)
                print(f"✅ Successfully uploaded all documents to Qdrant!")
            except Exception as e:
                print(f"❌ Error uploading final batch: {e}")

    def search(
        self, query: str, limit: int = 5, min_content_length: int = 0
    ) -> List[Dict]:
        """Search for similar documents"""
        query_vector = self.encoder.encode(query).tolist()

        query_filter = None
        if min_content_length > 0:
            from qdrant_client.models import Filter, FieldCondition, Range

            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="content_length",
                        range=Range(gte=min_content_length),
                    )
                ]
            )

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter,
            )

            return [
                {"score": result.score, "document": result.payload}
                for result in results
            ]
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []

    def get_collection_stats(self):
        """Get statistics about the collection"""
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            print(f"\n📊 Collection Statistics:")
            print(f"  - Collection name: {self.collection_name}")
            print(f"  - Total documents: {info.points_count:,}")
            print(f"  - Vector size: {info.config.params.vectors.size}")
            print(f"  - Distance metric: {info.config.params.vectors.distance}")
            return info.points_count
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return 0


def main():
    """Main function to embed content to local Qdrant"""

    print("=" * 70)
    print("🚀 Vietnamese Legal Documents - Local Embedder")
    print("=" * 70)

    # Check if Qdrant is running
    print("\n🔍 Checking if local Qdrant is running...")
    try:
        test_client = QdrantClient(url="http://localhost:6333")
        collections = test_client.get_collections()
        print("✅ Qdrant is running!")
    except Exception as e:
        print("❌ Cannot connect to Qdrant!")
        print("\n💡 Please start Qdrant first:")
        print("   Docker: docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant")
        print("   Or download from: https://github.com/qdrant/qdrant/releases")
        return

    # Initialize embedder
    embedder = LocalContentEmbedder(
        qdrant_url="http://localhost:6333",
        collection_name="vietnamese_legal_content",
        embedding_model="keepitreal/vietnamese-sbert",
    )

    # Load documents with filtering (skip content_length = 0)
    print("\n📚 Loading documents from JSON files...")
    print("⚠️ Filtering: Skipping documents with content_length = 0")

    documents = embedder.load_content_files(
        folder_pattern="traffic_laws_WITH_CONTENT_*",
        min_content_length=1,  # Skip empty content
    )

    if not documents:
        print("⚠️ No documents found to embed!")
        return

    # Estimate time and storage
    estimated_hours = (len(documents) / 50000) * 1.5  # ~1.5 hours per 50k docs
    estimated_gb = (len(documents) / 50000) * 1  # ~1GB per 50k docs

    print(f"\n⏱️ Estimated Processing Time: {estimated_hours:.1f} hours")
    print(f"💾 Estimated Storage: ~{estimated_gb:.1f} GB")

    response = input("\n▶️ Continue with embedding? (yes/no): ").strip().lower()
    if response not in ["yes", "y"]:
        print("❌ Embedding cancelled")
        return

    # Embed and upload
    embedder.embed_documents(documents, batch_size=32)
    count = embedder.get_collection_stats()

    if count > 0:
        # Test search
        print("\n" + "=" * 70)
        print("🔍 Testing search functionality...")
        print("=" * 70)

        test_queries = [
            "Chạy xe máy buông tay múa quạt xử phạt thế nào",
            "Giấy phép lái xe",
            "Vi phạm giao thông",
        ]

        for query in test_queries:
            print(f"\n🔎 Query: '{query}'")
            results = embedder.search(query, limit=3, min_content_length=100)

            if results:
                for i, result in enumerate(results, 1):
                    doc = result["document"]
                    print(f"\n  {i}. Score: {result['score']:.4f}")
                    title = doc.get("title", "No title")
                    if len(title) > 80:
                        title = title[:80] + "..."
                    print(f"     Title: {title}")
                    print(
                        f"     Content length: {doc.get('content_length', 0):,} chars"
                    )

    print("\n" + "=" * 70)
    print("✅ Embedding process completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
