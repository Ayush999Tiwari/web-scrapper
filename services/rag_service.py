import hashlib
import logging
from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import (
    SentenceTransformerEmbeddingFunction,
)

logger = logging.getLogger(__name__)
CHROMA_PATH = Path(__file__).resolve().parent.parent / "chroma_db"
COLLECTION_NAME = "scraped_website_content"
_client = None
_collection = None

def get_collection():
    """Initialize the persistent vector collection on first use."""
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        embedding_function = SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_function,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection

def split_into_chunks(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[str]:
    """Split website content into overlapping character-based chunks."""
    text = " ".join(text.split())
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks
def index_scrape(
    scrape_id: int,
    url: str,
    title: str | None,
    content: str,
) -> int:
    """Index one scrape and replace its previous chunks."""
    chunks = split_into_chunks(content)
    if not chunks:
        raise ValueError("Scraped content is empty.")
    collection = get_collection()
    ids = [
        hashlib.sha256(
            f"{scrape_id}:{index}".encode("utf-8")
        ).hexdigest()
        for index in range(len(chunks))
    ]
    metadatas = [
        {
            "scrape_id": scrape_id,
            "url": url,
            "title": title or url,
            "chunk_index": index,
        }
        for index in range(len(chunks))
    ]
    # Upsert overwrites matching chunk IDs and inserts new ones.
    # Delete any old trailing chunks if a re-indexed page became shorter.
    collection.upsert(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
    )
    collection.delete(
        where={
            "$and": [
                {"scrape_id": scrape_id},
                {"chunk_index": {"$gte": len(chunks)}},
            ]
        }
    )
    logger.info(
        "Indexed scrape_id=%s with %s chunks",
        scrape_id,
        len(chunks),
    )
    return len(chunks)

def search_scraped_content(
    question: str,
    top_k: int = 5,
) -> list[dict]:
    """Retrieve the closest matching chunks from ChromaDB."""
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return []
    result = collection.query(
        query_texts=[question],
        n_results=min(top_k, total),
        include=["documents", "metadatas", "distances"],
    )
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    matches = []
    for document, metadata, distance in zip(
        documents, metadatas, distances
    ):
        matches.append(
            {
                "content": document,
                "scrape_id": metadata["scrape_id"],
                "url": metadata["url"],
                "title": metadata["title"],
                "distance": distance,
            }
        )
    return matches

def get_index_stats() -> dict:
    """Return basic vector index statistics."""
    collection = get_collection()
    return {
        "collection": COLLECTION_NAME,
        "indexed_chunks": collection.count(),
        "storage_path": str(CHROMA_PATH),
    }
