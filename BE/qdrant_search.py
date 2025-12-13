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


def search_traffic_laws(query: str, limit: int = 10) -> List[Dict]:
    """
    Search traffic law documents in Qdrant

    Args:
        query: User's search query
        limit: Maximum number of results to return (default: 10)

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

        # Log all raw results from Qdrant
        logger.info(f"🔍 Qdrant returned {len(search_results)} documents:")
        for i, result in enumerate(search_results, 1):
            year = result.payload.get("year", "N/A")
            title = result.payload.get("title", "").strip() or "[No Title]"
            url = result.payload.get("url", "")[:80] or "[No URL]"
            original_score = result.score
            logger.info(f"  {i}. [Year: {year}] Score: {original_score:.4f}")
            logger.info(f"      Title: {title[:100]}")
            logger.info(f"      URL: {url}")

        # Boost newer documents by year (STRONGLY prefer 2024-2025 laws)
        current_year = 2025
        for result in search_results:
            year = result.payload.get("year", 2000)

            # AGGRESSIVE boost for very recent documents (2023-2025)
            if year >= 2023:
                year_boost = 1.0  # Massive boost for recent laws
            elif year >= 2020:
                year_boost = 0.5  # Medium boost for recent laws
            elif year >= 2015:
                year_boost = 0.2  # Small boost
            else:
                year_boost = -0.3  # Penalty for old documents

            result.score += year_boost

            # Extra boost for penalty/violation related documents (Nghị định)
            title = result.payload.get("title", "")
            if "Nghị định" in title and any(
                word in title for word in ["xử phạt", "vi phạm", "phạt"]
            ):
                result.score += 0.3  # Penalty documents get extra boost

        # 🎯 KEYWORD BOOSTING: Massive boost for exact document number matches
        import re

        # Extract document numbers from query (e.g., "35/2024", "168/2024")
        doc_numbers = re.findall(r"\b\d+/\d{4}\b", query)

        for result in search_results:
            title = result.payload.get("title", "")
            url = result.payload.get("url", "")

            for doc_num in doc_numbers:
                # Check if document number appears in title or URL
                if doc_num in title or doc_num in url:
                    result.score += 2.0  # HUGE boost for exact document match
                    logger.info(
                        f"🎯 Keyword boost +2.0 for doc number '{doc_num}' in: {title[:80]}"
                    )

        # Re-sort by boosted score AND year (tie-breaker)
        search_results = sorted(
            search_results,
            key=lambda x: (x.score, x.payload.get("year", 0)),
            reverse=True,
        )

        # Log after boosting
        logger.info(
            f"📊 After year-based boosting (top {min(5, len(search_results))}):"
        )
        for i, result in enumerate(search_results[:5], 1):
            year = result.payload.get("year", "N/A")
            title = result.payload.get("title", "Untitled")[:100]
            boosted_score = result.score
            logger.info(
                f"  {i}. [Year: {year}] Boosted Score: {boosted_score:.4f} - {title}"
            )

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

    # Log which documents are being used
    logger.info("📚 Documents being used as context:")
    for i, result in enumerate(search_results, 1):
        year = result.get("year", "N/A")
        title = result.get("title", "Untitled")[:80]
        score = result.get("score", 0)
        logger.info(f"  {i}. [Year: {year}] Score: {score:.4f} - {title}")

    context_parts = ["Tài liệu tham khảo từ cơ sở dữ liệu luật giao thông:\n"]
    current_length = len(context_parts[0])

    for i, result in enumerate(search_results, 1):
        # Format each document with year prominently displayed
        year = result.get("year", "N/A")
        doc_text = f"\n[Tài liệu {i} - NĂM {year}] {result['title']}\n"
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
