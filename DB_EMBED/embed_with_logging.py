"""
Embed Vietnamese legal documents WITH CONTENT to Qdrant Vector Database
WITH PROGRESS TRACKING AND LOGGING

This script processes JSON files one at a time and tracks progress in log files.
If interrupted, it can resume from where it left off.

Key features:
- Processes ONE file at a time (avoids memory issues)
- Tracks processed files in processed_files.txt
- Logs all activities in embedding_progress.log
- Can resume after interruption
- GPU-accelerated with RTX 3060
- Uses Vietnamese language model for better search

Usage:
    python embed_with_logging.py
"""

import os
import json
import glob
import time
from typing import List, Dict
from datetime import datetime
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
        """Initialize Qdrant client and embedding model"""
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
        """Create or use existing Qdrant collection"""
        try:
            # Try to get existing collection
            self.client.get_collection(collection_name=self.collection_name)
            print(f"✅ Using existing collection: {self.collection_name}")
        except:
            # Create new collection if doesn't exist
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size, distance=Distance.COSINE
                ),
            )
            print(
                f"✅ Created new collection: {self.collection_name} (vector size: {self.vector_size})"
            )

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

    # Progress log files
    log_file = "embedding_progress.log"
    processed_files_log = "processed_files.txt"

    # Load already processed files
    processed_files = set()
    if os.path.exists(processed_files_log):
        with open(processed_files_log, "r", encoding="utf-8") as f:
            processed_files = set(line.strip() for line in f if line.strip())
        print(f"📋 Found {len(processed_files)} already processed files")

    # Initialize embedder
    embedder = ContentEmbedder(
        qdrant_url="http://localhost:6333",
        collection_name="vietnamese_legal_content",
        embedding_model="keepitreal/vietnamese-sbert",
        api_key=None,
    )

    # Find all folders
    folders = glob.glob("traffic_laws_WITH_CONTENT_*")
    print(f"\n📁 Found {len(folders)} total folders")

    # Filter out already processed folders
    folders_to_process = [f for f in folders if f not in processed_files]
    print(f"📁 {len(folders_to_process)} folders remaining to process")

    if not folders_to_process:
        print("✅ All files already processed!")
        embedder.get_collection_stats()
        return

    total_processed = 0
    total_embedded = 0
    start_time = time.time()

    # Get current point ID (continue from where we left off)
    try:
        current_count = embedder.client.get_collection(
            embedder.collection_name
        ).points_count
        next_point_id = current_count
        print(
            f"📊 Collection already has {current_count:,} documents. Continuing from there..."
        )
    except:
        next_point_id = 0
        print("📊 Starting fresh collection...")

    # Open log file for appending
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\n{'='*70}\n")
        log.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Folders to process: {len(folders_to_process)}\n")
        log.write(f"{'='*70}\n")

    # Process each folder one at a time
    for idx, folder in enumerate(folders_to_process, 1):
        json_file = os.path.join(folder, "scraped_data_with_content.json")

        if not os.path.exists(json_file):
            continue

        print(f"\n{'='*70}")
        print(f"📂 [{idx}/{len(folders_to_process)}] {folder}")
        print(f"{'='*70}")

        try:
            # Load THIS file only
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            items = data if isinstance(data, list) else [data]

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
                    "source_folder": folder,
                }
                documents.append(doc)

            if not documents:
                print(f"   ⚠️ No documents with content")
                # Still mark as processed
                with open(processed_files_log, "a", encoding="utf-8") as pf:
                    pf.write(f"{folder}\n")
                with open(log_file, "a", encoding="utf-8") as log:
                    log.write(
                        f"[{datetime.now().strftime('%H:%M:%S')}] SKIPPED: {folder} (no content)\n"
                    )
                continue

            print(f"   ✅ Loaded {len(documents)} documents")
            total_processed += len(documents)

            # Prepare texts
            texts = [embedder.prepare_text_for_embedding(doc) for doc in documents]
            valid_docs = [
                (doc, text) for doc, text in zip(documents, texts) if text.strip()
            ]

            if not valid_docs:
                print(f"   ⚠️ No valid text")
                with open(processed_files_log, "a", encoding="utf-8") as pf:
                    pf.write(f"{folder}\n")
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
                        convert_to_numpy=True,
                    )

                    for j, (doc, embedding) in enumerate(zip(batch_docs, embeddings)):
                        points.append(
                            PointStruct(
                                id=next_point_id, vector=embedding.tolist(), payload=doc
                            )
                        )
                        next_point_id += 1

                except Exception as e:
                    print(f"   ❌ Embedding error: {e}")
                    with open(log_file, "a", encoding="utf-8") as log:
                        log.write(
                            f"[{datetime.now().strftime('%H:%M:%S')}] EMBED ERROR: {folder} - {str(e)}\n"
                        )

            # Upload to Qdrant in smaller chunks to avoid 32MB payload limit
            if points:
                try:
                    # Upload in chunks of 100 documents max
                    max_chunk_size = 100
                    uploaded_count = 0
                    total_chunks = (len(points) + max_chunk_size - 1) // max_chunk_size

                    for chunk_idx in range(0, len(points), max_chunk_size):
                        chunk = points[chunk_idx : chunk_idx + max_chunk_size]
                        embedder.client.upsert(
                            collection_name=embedder.collection_name,
                            points=chunk,
                            wait=True,  # Wait for confirmation
                        )
                        uploaded_count += len(chunk)

                    total_embedded += uploaded_count
                    if total_chunks > 1:
                        print(
                            f"   ✅ Uploaded {uploaded_count} documents in {total_chunks} chunks"
                        )
                    else:
                        print(f"   ✅ Uploaded {uploaded_count} documents")

                    # Mark as successfully processed
                    with open(processed_files_log, "a", encoding="utf-8") as pf:
                        pf.write(f"{folder}\n")

                    with open(log_file, "a", encoding="utf-8") as log:
                        log.write(
                            f"[{datetime.now().strftime('%H:%M:%S')}] SUCCESS: {folder} - {len(points)} docs\n"
                        )

                    # Show progress
                    elapsed = time.time() - start_time
                    files_per_hour = idx / (elapsed / 3600) if elapsed > 0 else 0
                    remaining_files = len(folders_to_process) - idx
                    eta_hours = (
                        remaining_files / files_per_hour if files_per_hour > 0 else 0
                    )

                    print(
                        f"   📊 Progress: {idx/len(folders_to_process)*100:.1f}% | Total: {total_embedded:,} docs"
                    )
                    print(
                        f"   ⏱️ Speed: {files_per_hour:.1f} files/hr | ETA: {eta_hours:.1f} hours"
                    )

                except Exception as e:
                    print(f"   ❌ Upload error: {e}")
                    with open(log_file, "a", encoding="utf-8") as log:
                        log.write(
                            f"[{datetime.now().strftime('%H:%M:%S')}] UPLOAD ERROR: {folder} - {str(e)}\n"
                        )

        except json.JSONDecodeError as e:
            print(f"   ❌ JSON parse error: {e}")
            with open(log_file, "a", encoding="utf-8") as log:
                log.write(
                    f"[{datetime.now().strftime('%H:%M:%S')}] JSON ERROR: {folder}\n"
                )
        except Exception as e:
            print(f"   ❌ Error: {e}")
            with open(log_file, "a", encoding="utf-8") as log:
                log.write(
                    f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: {folder} - {str(e)}\n"
                )

    # Final statistics
    print(f"\n{'='*70}")
    print(f"✅ COMPLETED!")
    print(f"{'='*70}")
    print(f"📊 Files processed: {idx}/{len(folders_to_process)}")
    print(f"📊 Documents processed: {total_processed:,}")
    print(f"📊 Documents embedded: {total_embedded:,}")
    print(f"⏱️ Total time: {(time.time() - start_time)/3600:.2f} hours")

    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"\n{'='*70}\n")
        log.write(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Files processed: {idx}/{len(folders_to_process)}\n")
        log.write(f"Documents processed: {total_processed:,}\n")
        log.write(f"Documents embedded: {total_embedded:,}\n")
        log.write(f"Total time: {(time.time() - start_time)/3600:.2f} hours\n")
        log.write(f"{'='*70}\n")

    embedder.get_collection_stats()


if __name__ == "__main__":
    main()
