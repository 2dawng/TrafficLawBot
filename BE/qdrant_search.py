"""
Qdrant search integration for traffic law documents
"""

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Initialize Qdrant client and embedding model (singleton)
qdrant_client = None
embedding_model = None


def get_qdrant_client():
    """Get or create Qdrant client singleton"""
    global qdrant_client
    if qdrant_client is None:
        qdrant_client = QdrantClient(host="localhost", port=6333)
    return qdrant_client


def get_embedding_model():
    """Get or create embedding model singleton"""
    global embedding_model
    if embedding_model is None:
        embedding_model = SentenceTransformer("keepitreal/vietnamese-sbert")
    return embedding_model


def search_traffic_laws(query: str, limit: int = 5) -> List[Dict]:
    """
    Search traffic law documents in Qdrant

    Args:
        query: User's search query
        limit: Maximum number of results to return

    Returns:
        List of relevant documents with metadata
    """
    try:
        client = get_qdrant_client()
        model = get_embedding_model()

        # Generate query embedding
        logger.info(f"Searching for: {query[:100]}")
        query_embedding = model.encode(query).tolist()

        # Search in Qdrant
        search_results = client.query_points(
            collection_name="traffic_laws_only",
            query=query_embedding,
            limit=limit * 3,  # Get more results to filter duplicates
        ).points

        # Boost newer documents by year (strongly prefer 2024-2025 laws)
        current_year = 2025
        for result in search_results:
            year = result.payload.get("year", 2000)
            # Strong boost for documents from last 5 years (up to +0.5)
            year_boost = min(0.5, (year - (current_year - 5)) * 0.1)
            if year_boost > 0:
                result.score += year_boost

            # Extra boost for penalty/violation related documents (Nghị định)
            title = result.payload.get("title", "")
            if "Nghị định" in title and any(
                word in title for word in ["xử phạt", "vi phạm", "phạt"]
            ):
                result.score += 0.2  # Penalty documents get extra boost

        # Re-sort by boosted score
        search_results = sorted(search_results, key=lambda x: x.score, reverse=True)

        # Deduplicate results by URL
        seen_urls = set()
        unique_results = []

        for result in search_results:
            url = result.payload.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(
                    {
                        "title": result.payload.get("title", "Untitled"),
                        "content": result.payload.get("content", ""),
                        "url": url,
                        "score": result.score,
                        "content_length": result.payload.get("content_length", 0),
                        "document_type": result.payload.get("document_type", ""),
                        "status": result.payload.get("status", ""),
                        "year": result.payload.get("year", 2000),
                    }
                )

                if len(unique_results) >= limit:
                    break

        logger.info(
            f"Found {len(unique_results)} unique results (from {len(search_results)} total)"
        )
        return unique_results

    except Exception as e:
        logger.error(f"Error searching Qdrant: {e}", exc_info=True)
        return []


def format_context_for_llm(search_results: List[Dict], max_length: int = 4000) -> str:
    """
    Format search results into context string for LLM

    Args:
        search_results: List of search results from Qdrant
        max_length: Maximum character length for context

    Returns:
        Formatted context string
    """
    if not search_results:
        return ""

    context_parts = ["Tài liệu tham khảo từ cơ sở dữ liệu luật giao thông:\n"]
    current_length = len(context_parts[0])

    for i, result in enumerate(search_results, 1):
        # Format each document
        doc_text = f"\n[Tài liệu {i}] {result['title']}\n"
        doc_text += f"Nguồn: {result['url']}\n"

        # Truncate content if needed
        content = result["content"]
        if len(content) > 1000:
            content = content[:1000] + "..."
        doc_text += f"Nội dung: {content}\n"

        # Check if adding this doc exceeds max length
        if current_length + len(doc_text) > max_length:
            break

        context_parts.append(doc_text)
        current_length += len(doc_text)

    return "".join(context_parts)
