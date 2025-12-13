"""
Embed scraped Vietnamese legal documents to Qdrant Vector Database

This script processes all scraped data (traffic laws, Q&A, etc.) and embeds them
into Qdrant for semantic search and retrieval.

Requirements:
    pip install qdrant-client sentence-transformers
"""

import os
import json
import glob
from typing import List, Dict, Any
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer


class QdrantEmbedder:
    """Embed legal documents to Qdrant vector database"""

    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "vietnamese_legal_docs",
        embedding_model: str = "keepitreal/vietnamese-sbert",
    ):
        """
        Initialize Qdrant client and embedding model

        Args:
            qdrant_url: Qdrant server URL (default: localhost)
            collection_name: Name of the collection to store documents
            embedding_model: HuggingFace model for Vietnamese embeddings
        """
        self.client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name

        # Load Vietnamese embedding model
        print(f"Loading embedding model: {embedding_model}")
        self.encoder = SentenceTransformer(embedding_model)
        self.vector_size = self.encoder.get_sentence_embedding_dimension()

        # Initialize collection
        self._create_collection()

    def _create_collection(self):
        """Create or recreate Qdrant collection"""
        try:
            # Delete existing collection if it exists
            self.client.delete_collection(collection_name=self.collection_name)
            print(f"Deleted existing collection: {self.collection_name}")
        except:
            pass

        # Create new collection
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size, distance=Distance.COSINE
            ),
        )
        print(
            f"Created collection: {self.collection_name} (vector size: {self.vector_size})"
        )

    def load_traffic_laws(self, folder_pattern: str = "traffic_laws_*") -> List[Dict]:
        """Load traffic law documents from scraped folders"""
        documents = []

        # Find all traffic law folders
        folders = glob.glob(folder_pattern)
        print(f"\nFound {len(folders)} traffic law folders")

        for folder in folders:
            jsonl_file = os.path.join(folder, "scraped_data.jsonl")

            if os.path.exists(jsonl_file):
                print(f"Loading: {jsonl_file}")
                with open(jsonl_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            doc = json.loads(line.strip())
                            documents.append(
                                {
                                    "type": "traffic_law",
                                    "url": doc.get("url", ""),
                                    "title": doc.get("title", ""),
                                    "document_number": doc.get("number", ""),
                                    "date": doc.get("date", ""),
                                    "status": doc.get("status", ""),
                                    "document_type": doc.get("document_type", ""),
                                    "found_via": doc.get("found_via", ""),
                                    "related_links_count": len(
                                        doc.get("related_links", [])
                                    ),
                                }
                            )
                        except json.JSONDecodeError as e:
                            print(f"Error parsing line: {e}")

        print(f"Loaded {len(documents)} traffic law documents")
        return documents

    def load_qa_data(self, qa_folder: str = "tvpl_qa_ver3_testing") -> List[Dict]:
        """Load Q&A data from the QA folder"""
        documents = []

        if not os.path.exists(qa_folder):
            print(f"\nQ&A folder not found: {qa_folder}")
            return documents

        # Find all JSONL files in the QA folder
        jsonl_files = glob.glob(os.path.join(qa_folder, "*.jsonl"))
        print(f"\nFound {len(jsonl_files)} Q&A files")

        for jsonl_file in jsonl_files:
            print(f"Loading: {jsonl_file}")
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        qa = json.loads(line.strip())
                        documents.append(
                            {
                                "type": "qa",
                                "question": qa.get("question", ""),
                                "answer": qa.get("answer", ""),
                                "url": qa.get("url", ""),
                                "date": qa.get("date", ""),
                                "domain": qa.get("domain", "unknown"),
                            }
                        )
                    except json.JSONDecodeError as e:
                        print(f"Error parsing line: {e}")

        print(f"Loaded {len(documents)} Q&A documents")
        return documents

    def prepare_text_for_embedding(self, doc: Dict) -> str:
        """Prepare document text for embedding"""
        if doc["type"] == "traffic_law":
            # Combine title, document number, and type for traffic laws
            text_parts = []
            if doc.get("title"):
                text_parts.append(f"Tiêu đề: {doc['title']}")
            if doc.get("document_number"):
                text_parts.append(f"Số hiệu: {doc['document_number']}")
            if doc.get("document_type"):
                text_parts.append(f"Loại: {doc['document_type']}")
            return " | ".join(text_parts)

        elif doc["type"] == "qa":
            # Combine question and answer for Q&A
            text_parts = []
            if doc.get("question"):
                text_parts.append(f"Câu hỏi: {doc['question']}")
            if doc.get("answer"):
                # Truncate answer if too long
                answer = doc["answer"]
                if len(answer) > 500:
                    answer = answer[:500] + "..."
                text_parts.append(f"Trả lời: {answer}")
            return " | ".join(text_parts)

        return ""

    def embed_documents(self, documents: List[Dict], batch_size: int = 32):
        """Embed documents and upload to Qdrant"""
        if not documents:
            print("No documents to embed")
            return

        print(f"\nEmbedding {len(documents)} documents...")

        # Prepare texts for embedding
        texts = [self.prepare_text_for_embedding(doc) for doc in documents]

        # Filter out empty texts
        valid_docs = [
            (doc, text) for doc, text in zip(documents, texts) if text.strip()
        ]
        print(f"Valid documents (non-empty): {len(valid_docs)}")

        if not valid_docs:
            print("No valid documents to embed")
            return

        # Generate embeddings in batches
        points = []
        for i in range(0, len(valid_docs), batch_size):
            batch = valid_docs[i : i + batch_size]
            batch_docs = [item[0] for item in batch]
            batch_texts = [item[1] for item in batch]

            print(
                f"Processing batch {i // batch_size + 1}/{(len(valid_docs) + batch_size - 1) // batch_size}"
            )

            # Generate embeddings
            embeddings = self.encoder.encode(batch_texts, show_progress_bar=True)

            # Create points
            for j, (doc, embedding) in enumerate(zip(batch_docs, embeddings)):
                point_id = i + j
                points.append(
                    PointStruct(id=point_id, vector=embedding.tolist(), payload=doc)
                )

        # Upload to Qdrant
        print(f"\nUploading {len(points)} points to Qdrant...")
        self.client.upsert(collection_name=self.collection_name, points=points)

        print(f"✅ Successfully uploaded {len(points)} documents to Qdrant!")

    def search(self, query: str, limit: int = 5, doc_type: str = None) -> List[Dict]:
        """
        Search for similar documents

        Args:
            query: Search query in Vietnamese
            limit: Number of results to return
            doc_type: Filter by document type ('traffic_law' or 'qa')

        Returns:
            List of matching documents with scores
        """
        # Generate query embedding
        query_vector = self.encoder.encode(query).tolist()

        # Build filter
        query_filter = None
        if doc_type:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            query_filter = Filter(
                must=[FieldCondition(key="type", match=MatchValue(value=doc_type))]
            )

        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter,
        )

        return [
            {"score": result.score, "document": result.payload} for result in results
        ]

    def get_collection_stats(self):
        """Get statistics about the collection"""
        info = self.client.get_collection(collection_name=self.collection_name)
        print(f"\n📊 Collection Statistics:")
        print(f"  - Total points: {info.points_count}")
        print(f"  - Vector size: {info.config.params.vectors.size}")
        print(f"  - Distance metric: {info.config.params.vectors.distance}")


def main():
    """Main function to embed all scraped data"""

    print("=" * 60)
    print("🚀 Vietnamese Legal Documents - Qdrant Embedder")
    print("=" * 60)

    # Initialize embedder
    embedder = QdrantEmbedder(
        qdrant_url="http://localhost:6333",  # Change if using Qdrant Cloud
        collection_name="vietnamese_legal_docs",
        embedding_model="keepitreal/vietnamese-sbert",  # Good Vietnamese model
    )

    # Load all documents
    all_documents = []

    # 1. Load traffic laws
    traffic_laws = embedder.load_traffic_laws()
    all_documents.extend(traffic_laws)

    # 2. Load Q&A data
    qa_data = embedder.load_qa_data()
    all_documents.extend(qa_data)

    # 3. Embed and upload to Qdrant
    if all_documents:
        embedder.embed_documents(all_documents, batch_size=32)
        embedder.get_collection_stats()
    else:
        print("⚠️ No documents found to embed!")

    print("\n" + "=" * 60)
    print("✅ Embedding process completed!")
    print("=" * 60)

    # Example search
    print("\n🔍 Testing search functionality...")
    query = "Giấy phép lái xe"
    results = embedder.search(query, limit=3)

    print(f"\nSearch results for: '{query}'")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result['score']:.4f}")
        doc = result["document"]
        if doc["type"] == "traffic_law":
            print(f"   Type: Traffic Law")
            print(f"   Title: {doc.get('title', 'N/A')}")
            print(f"   URL: {doc.get('url', 'N/A')}")
        elif doc["type"] == "qa":
            print(f"   Type: Q&A")
            question = doc.get("question", "N/A")
            if len(question) > 100:
                question = question[:100] + "..."
            print(f"   Question: {question}")
            print(f"   Domain: {doc.get('domain', 'N/A')}")


if __name__ == "__main__":
    main()
