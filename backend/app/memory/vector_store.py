"""ChromaDB vector store with direct vector embedding computation."""
import uuid
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional
from app.config import settings
from app.utils.logger import logger


def compute_embedding(text: str) -> List[float]:
    """
    Computes a deterministic 384-dimensional dense embedding vector.
    Instantaneous (0ms), completely offline, zero downloads required.
    """
    tokens = text.lower().split()
    vec = np.zeros(384, dtype=np.float32)
    for i, token in enumerate(tokens):
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        idx = h % 384
        sign = 1.0 if ((h >> 9) & 1) else -1.0
        vec[idx] += sign / (1.0 + 0.05 * i)
    norm = np.linalg.norm(vec)
    if norm > 1e-6:
        vec = vec / norm
    return vec.tolist()


class VectorMemoryStore:
    """Manages persistent vector embeddings of past lessons, solutions, and corrections."""

    def __init__(self):
        self._client = None
        self._collection = None

    def _init_chroma(self):
        if self._collection is None:
            try:
                import chromadb
                from chromadb.config import Settings as ChromaSettings

                settings.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
                self._client = chromadb.PersistentClient(
                    path=str(settings.CHROMA_DIR),
                    settings=ChromaSettings(anonymized_telemetry=False)
                )
                # No internal embedding function: we provide explicit embeddings directly!
                self._collection = self._client.get_or_create_collection(
                    name="study_experiences_v2",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info("ChromaDB vector store initialized.")
            except Exception as e:
                logger.error(f"ChromaDB initialization failed: {e}")

    async def add_experience(
        self,
        query: str,
        solution: str,
        user_id: str = "default_user",
        task_type: str = "conceptual",
        success: bool = True
    ) -> str:
        """Stores a problem and solution with pre-computed embedding."""
        self._init_chroma()
        if self._collection is None:
            return ""

        doc_id = str(uuid.uuid4())
        document_text = f"Question: {query}\n\nSolution Strategy:\n{solution}"
        embedding = compute_embedding(document_text)

        metadata = {
            "user_id": user_id,
            "task_type": task_type,
            "success": bool(success),
            "snippet": query[:200]
        }

        try:
            self._collection.add(
                documents=[document_text],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id]
            )
            return doc_id
        except Exception as e:
            logger.error(f"Failed to write to vector memory: {e}")
            return ""

    async def search_similar(
        self,
        query: str,
        user_id: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """Searches past experiences using query vector embedding."""
        self._init_chroma()
        if self._collection is None:
            return []

        try:
            query_vec = compute_embedding(query)
            where_filter = {"user_id": user_id} if user_id else None

            results = self._collection.query(
                query_embeddings=[query_vec],
                n_results=top_k,
                where=where_filter
            )

            matches = []
            if results and results.get("documents") and results["documents"][0]:
                for doc, meta, dist, doc_id in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                    results["ids"][0]
                ):
                    matches.append({
                        "id": doc_id,
                        "document": doc,
                        "metadata": meta,
                        "distance": dist,
                        "similarity": round(1.0 - dist, 3) if dist is not None else 1.0
                    })
            return matches
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []


vector_store = VectorMemoryStore()
