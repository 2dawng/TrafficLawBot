"""
Embed Vietnamese legal documents WITH CONTENT to Qdrant Vector Database

This script processes JSON files containing scraped Vietnamese legal documents
with their full content and embeds them into Qdrant for semantic search.

Key features:
- Handles JSON files (not JSONL)
- Embeds the actual content field
- Ignores documents with empty content
- Filters out date and number fields as requested
- Uses Vietnamese language model for better search

Usage:
    python embed_content_to_qdrant.py
"""

import os
import json
import glob
from typing import List, Dict, Any
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer


class ContentEmbedder:
    """Embed legal documents with content to Qdrant"""

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "vietnamese_legal_content",
        embedding_model: str = "keepitreal/vietnamese-sbert",
        api_key: str = None,
    ):
        """
        Initialize Qdrant client and embedding model

        Args:
            qdrant_url: Qdrant server URL
            collection_name: Name of the collection
            embedding_model: Vietnamese embedding model
            api_key: Qdrant Cloud API key (required for cloud, not for localhost)
        """
        # Initialize Qdrant client with or without API key
        if api_key:
            self.client = QdrantClient(url=qdrant_url, api_key=api_key)
        else:
            self.client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name

        print(f"Loading embedding model: {embedding_model}")
        self.encoder = SentenceTransformer(embedding_model)

        # Use GPU if available (RTX 3060)
        import torch

        if torch.cuda.is_available():
            self.encoder = self.encoder.to("cuda")
            print(f"✅ Using GPU: {torch.cuda.get_device_name(0)}")
            print(
                f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
            )
        else:
            print("⚠️ GPU not detected, using CPU (will be slower)")

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
        self, folder_pattern: str = "traffic_laws_WITH_CONTENT_*"
    ) -> List[Dict]:
        """
        Load documents from JSON files with content

        Args:
            folder_pattern: Pattern to match folders

        Returns:
            List of document dictionaries
        """
        documents = []
        stats = {"total": 0, "with_content": 0, "empty_content": 0}

        # Find all folders matching pattern
        folders = glob.glob(folder_pattern)
        print(f"\n📁 Found {len(folders)} folders matching pattern: {folder_pattern}")

        for folder in folders:
            # Look ONLY for scraped_data_with_content.json files
            json_file = os.path.join(folder, "scraped_data_with_content.json")

            # Skip if the specific file doesn't exist
            if not os.path.exists(json_file):
                continue

            json_files = [json_file]

            for json_file in json_files:
                print(f"\n📄 Loading: {json_file}")

                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # Handle both list and single object
                    if isinstance(data, list):
                        items = data
                    else:
                        items = [data]

                    for item in items:
                        stats["total"] += 1

                        # Check if content exists and is not empty
                        content = item.get("content", "").strip()
                        if not content:
                            stats["empty_content"] += 1
                            continue

                        stats["with_content"] += 1

                        # Create document (excluding date and number as requested)
                        doc = {
                            "url": item.get("url", ""),
                            "title": item.get("title", ""),
                            "type": item.get("type", ""),
                            "status": item.get("status", ""),
                            "content": content,
                            "content_length": item.get("content_length", len(content)),
                            "document_type": item.get("document_type", ""),
                            "source_file": os.path.basename(json_file),
                        }

                        documents.append(doc)

                except json.JSONDecodeError as e:
                    print(f"❌ Error parsing {json_file}: {e}")
                except Exception as e:
                    print(f"❌ Error loading {json_file}: {e}")

        print(f"\n📊 Loading Statistics:")
        print(f"  - Total documents: {stats['total']}")
        print(f"  - With content: {stats['with_content']}")
        print(f"  - Empty content (skipped): {stats['empty_content']}")
        print(f"  - Loaded for embedding: {len(documents)}")

        return documents

    def prepare_text_for_embedding(self, doc: Dict) -> str:
        """
        Prepare document text for embedding

        Combines title and content for better semantic search

        Args:
            doc: Document dictionary

        Returns:
            Text string ready for embedding
        """
        parts = []

        # Add title if exists
        title = doc.get("title", "").strip()
        if title and title != "thuvienphapluat.vn":  # Skip default titles
            parts.append(f"Tiêu đề: {title}")

        # Add content (main part)
        content = doc.get("content", "").strip()
        if content:
            # Truncate if too long (models have max length)
            # Most models can handle 512 tokens, roughly 2000 characters
            max_content_length = 8000  # Adjust based on your needs
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
            parts.append(content)

        return " | ".join(parts) if parts else ""

    def embed_documents(self, documents: List[Dict], batch_size: int = 64):
        """
        Embed documents and upload to Qdrant (GPU-optimized)

        Args:
            documents: List of document dictionaries
            batch_size: Number of documents to process at once (increased for GPU)
        """
        if not documents:
            print("⚠️ No documents to embed")
            return

        print(f"\n🔄 Embedding {len(documents)} documents...")
        print(f"   Batch size: {batch_size} (GPU-optimized)")

        # Prepare texts for embedding
        print("📝 Preparing texts for embedding...")
        texts = [self.prepare_text_for_embedding(doc) for doc in documents]

        # Filter out empty texts
        valid_docs = [
            (doc, text) for doc, text in zip(documents, texts) if text.strip()
        ]
        print(f"✅ Valid documents (non-empty): {len(valid_docs)}")

        if not valid_docs:
            print("⚠️ No valid documents to embed")
            return

        # Generate embeddings in batches
        points = []
        total_batches = (len(valid_docs) + batch_size - 1) // batch_size
        upload_chunk_size = 1000  # Upload every 1000 points
        uploaded_count = 0

        import time

        start_time = time.time()

        for i in range(0, len(valid_docs), batch_size):
            batch = valid_docs[i : i + batch_size]
            batch_docs = [item[0] for item in batch]
            batch_texts = [item[1] for item in batch]

            current_batch = i // batch_size + 1

            # Show progress every 50 batches
            if current_batch % 50 == 0 or current_batch == 1:
                elapsed = time.time() - start_time
                docs_processed = i
                if docs_processed > 0:
                    docs_per_sec = docs_processed / elapsed
                    remaining_docs = len(valid_docs) - docs_processed
                    eta_seconds = (
                        remaining_docs / docs_per_sec if docs_per_sec > 0 else 0
                    )
                    eta_hours = eta_seconds / 3600

                    print(
                        f"📊 Batch {current_batch}/{total_batches} ({(current_batch/total_batches*100):.1f}%)"
                    )
                    print(
                        f"   Speed: {docs_per_sec:.0f} docs/sec | Uploaded: {uploaded_count:,} | ETA: {eta_hours:.1f} hours"
                    )

            try:
                # Generate embeddings using GPU
                embeddings = self.encoder.encode(
                    batch_texts,
                    show_progress_bar=False,  # Disable per-batch progress bar
                    batch_size=batch_size,
                    convert_to_numpy=True,
                )

                # Create points
                for j, (doc, embedding) in enumerate(zip(batch_docs, embeddings)):
                    point_id = i + j
                    points.append(
                        PointStruct(id=point_id, vector=embedding.tolist(), payload=doc)
                    )

                # Upload in chunks to avoid memory issues
                if len(points) >= upload_chunk_size:
                    try:
                        self.client.upsert(
                            collection_name=self.collection_name,
                            points=points,
                            wait=False,  # Async upload for speed
                        )
                        uploaded_count += len(points)
                        points = []  # Clear the list
                    except Exception as e:
                        print(f"❌ Error uploading chunk: {e}")

            except Exception as e:
                print(f"❌ Error processing batch {current_batch}: {e}")
                continue

        # Upload remaining points
        if points:
            print(f"\n⬆️ Uploading final {len(points)} points to Qdrant...")
            try:
                self.client.upsert(collection_name=self.collection_name, points=points)
                uploaded_count += len(points)
            except Exception as e:
                print(f"❌ Error uploading final batch: {e}")

        total_time = time.time() - start_time
        print(f"\n✅ Successfully uploaded {uploaded_count:,} documents to Qdrant!")
        print(
            f"   Total time: {total_time/3600:.2f} hours ({total_time/60:.1f} minutes)"
        )
        print(f"   Average speed: {uploaded_count/total_time:.0f} docs/second")

    def search(
        self, query: str, limit: int = 5, min_content_length: int = 0
    ) -> List[Dict]:
        """
        Search for similar documents

        Args:
            query: Search query in Vietnamese
            limit: Number of results to return
            min_content_length: Minimum content length filter

        Returns:
            List of matching documents with scores
        """
        # Generate query embedding
        query_vector = self.encoder.encode(query).tolist()

        # Build filter if needed
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

        # Search
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
            print(f"  - Total documents: {info.points_count}")
            print(f"  - Vector size: {info.config.params.vectors.size}")
            print(f"  - Distance metric: {info.config.params.vectors.distance}")
            return info.points_count
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return 0


def main():
    """Main function to embed content to Qdrant - Process ONE FILE at a time"""

    print("=" * 70)
    print("🚀 Vietnamese Legal Documents Content Embedder")
    print("   (Processing one file at a time to avoid memory issues)")
    print("=" * 70)

    # Initialize embedder - LOCAL VERSION
    embedder = ContentEmbedder(
        qdrant_url="http://localhost:6333",  # Local Qdrant
        collection_name="vietnamese_legal_content",
        embedding_model="keepitreal/vietnamese-sbert",
        api_key=None,  # No API key needed for local
    )

    # Find all folders
    import glob
    import time
    
    folders = glob.glob("traffic_laws_WITH_CONTENT_*")
    print(f"\n📁 Found {len(folders)} folders to process")
    
    total_processed = 0
    total_embedded = 0
    start_time = time.time()
    
    # Get current point ID (continue from where we left off)
    try:
        current_count = embedder.client.get_collection(embedder.collection_name).points_count
        next_point_id = current_count
        print(f"� Collection already has {current_count} documents. Continuing from there...")
    except:
        next_point_id = 0
        print("📊 Starting fresh collection...")
    
    # Process each folder one at a time
    for idx, folder in enumerate(folders, 1):
        json_file = os.path.join(folder, "scraped_data_with_content.json")
        
        if not os.path.exists(json_file):
            continue
        
        print(f"\n{'='*70}")
        print(f"📂 Processing folder {idx}/{len(folders)}: {folder}")
        print(f"{'='*70}")
        
        try:
            # Load THIS file only
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, list):
                items = data
            else:
                items = [data]
            
            # Filter documents with content
            documents = []
            for item in items:
                content = item.get("content", "").strip()
                if not content:
                    continue
                
                doc = {
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "type": item.get("type", ""),
                    "status": item.get("status", ""),
                    "content": content,
                    "content_length": item.get("content_length", len(content)),
                    "document_type": item.get("document_type", ""),
                    "source_file": os.path.basename(json_file),
                }
                documents.append(doc)
            
            if not documents:
                print(f"   ⚠️ No documents with content in this file")
                continue
            
            print(f"   ✅ Loaded {len(documents)} documents with content")
            total_processed += len(documents)
            
            # Prepare texts
            texts = [embedder.prepare_text_for_embedding(doc) for doc in documents]
            valid_docs = [(doc, text) for doc, text in zip(documents, texts) if text.strip()]
            
            if not valid_docs:
                print(f"   ⚠️ No valid documents after text preparation")
                continue
            
            print(f"   🔄 Embedding {len(valid_docs)} documents...")
            
            # Embed in batches
            points = []
            batch_size = 64  # GPU-optimized
            
            for i in range(0, len(valid_docs), batch_size):
                batch = valid_docs[i : i + batch_size]
                batch_docs = [item[0] for item in batch]
                batch_texts = [item[1] for item in batch]
                
                try:
                    embeddings = embedder.encoder.encode(
                        batch_texts, 
                        show_progress_bar=False,
                        batch_size=batch_size,
                        convert_to_numpy=True
                    )
                    
                    for j, (doc, embedding) in enumerate(zip(batch_docs, embeddings)):
                        points.append(
                            PointStruct(
                                id=next_point_id, 
                                vector=embedding.tolist(), 
                                payload=doc
                            )
                        )
                        next_point_id += 1
                
                except Exception as e:
                    print(f"   ❌ Error embedding batch: {e}")
                    continue
            
            # Upload to Qdrant
            if points:
                try:
                    embedder.client.upsert(
                        collection_name=embedder.collection_name, 
                        points=points,
                        wait=False
                    )
                    total_embedded += len(points)
                    print(f"   ✅ Uploaded {len(points)} documents to Qdrant")
                    
                    # Show progress
                    elapsed = time.time() - start_time
                    files_per_hour = idx / (elapsed / 3600) if elapsed > 0 else 0
                    remaining_files = len(folders) - idx
                    eta_hours = remaining_files / files_per_hour if files_per_hour > 0 else 0
                    
                    print(f"   📊 Progress: {idx}/{len(folders)} files ({idx/len(folders)*100:.1f}%)")
                    print(f"   📈 Total embedded: {total_embedded:,} documents")
                    print(f"   ⏱️ Speed: {files_per_hour:.1f} files/hour | ETA: {eta_hours:.1f} hours")
                    
                except Exception as e:
                    print(f"   ❌ Error uploading to Qdrant: {e}")
        
        except json.JSONDecodeError as e:
            print(f"   ❌ Error parsing JSON: {e}")
        except Exception as e:
            print(f"   ❌ Error processing file: {e}")
    
    # Final statistics
    print(f"\n{'='*70}")
    print(f"✅ COMPLETED!")
    print(f"{'='*70}")
    print(f"📊 Total documents processed: {total_processed:,}")
    print(f"📊 Total documents embedded: {total_embedded:,}")
    print(f"⏱️ Total time: {(time.time() - start_time)/3600:.2f} hours")
    
    count = embedder.get_collection_stats()
    
    # Test search if we have documents
    if count > 0:
        print("\n" + "=" * 70)
        print("🔍 Testing search functionality...")
        print("=" * 70)

        test_queries = [
            "Chạy xe máy buông tay múa quạt xử phạt thế nào",
            "Giấy phép lái xe",
            "Vi phạm giao thông",
            "Tước bằng lái xe",
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
                    print(f"     URL: {doc.get('url', 'N/A')}")
                    content = doc.get("content", "")
                    if len(content) > 150:
                        content = content[:150] + "..."
                    print(f"     Content preview: {content}")
            else:
                print("   No results found")

    print("\n" + "=" * 70)
    print("✅ Embedding process completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
