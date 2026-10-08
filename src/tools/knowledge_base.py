"""Knowledge base using FAISS for similarity search."""
import json
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import structlog

from src.config import settings

logger = structlog.get_logger()


class KnowledgeBase:
    """FAISS-backed knowledge base for storing and retrieving review-response pairs."""

    def __init__(self):
        """Initialize knowledge base."""
        self.embedding_model_name = settings.embedding_model
        self.index_path = Path(settings.faiss_index_path)
        self.metadata_path = self.index_path.with_suffix('.json')

        self.embedding_model = None
        self.index = None
        self.metadata = []  # Stores review-response pairs and metadata
        self._initialized = False

    def _initialize(self):
        """Lazy initialization of embedding model and index."""
        if self._initialized:
            return

        logger.info("Initializing knowledge base", model=self.embedding_model_name)

        # Load embedding model
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        embedding_dim = self.embedding_model.get_sentence_embedding_dimension()

        # Try to load existing index
        if self.index_path.exists() and self.metadata_path.exists():
            logger.info("Loading existing FAISS index")
            self.index = faiss.read_index(str(self.index_path))
            with open(self.metadata_path, 'r') as f:
                self.metadata = json.load(f)
        else:
            logger.info("Creating new FAISS index", dimension=embedding_dim)
            # Use L2 distance for similarity
            self.index = faiss.IndexFlatL2(embedding_dim)
            self.metadata = []

        self._initialized = True
        logger.info(
            "Knowledge base initialized",
            num_entries=len(self.metadata),
            embedding_dim=embedding_dim
        )

    def add_entry(
        self,
        review_text: str,
        response_text: str,
        sentiment: str,
        issues: List[str],
        verification_score: float
    ):
        """
        Add a successful review-response pair to the knowledge base.

        Args:
            review_text: Original review text
            response_text: Generated response
            sentiment: Sentiment classification
            issues: List of issue categories
            verification_score: Verification score for this response
        """
        self._initialize()

        # Create embedding from review text
        embedding = self.embedding_model.encode([review_text])[0]
        embedding = np.array([embedding], dtype='float32')

        # Add to FAISS index
        self.index.add(embedding)

        # Add metadata
        self.metadata.append({
            "review_text": review_text,
            "response_text": response_text,
            "sentiment": sentiment,
            "issues": issues,
            "verification_score": verification_score
        })

        logger.debug(
            "Added entry to knowledge base",
            total_entries=len(self.metadata),
            sentiment=sentiment
        )

    def search(
        self,
        query_text: str,
        top_k: int = 3,
        sentiment_filter: Optional[str] = None,
        min_score: float = 0.7
    ) -> List[Dict]:
        """
        Search for similar review-response pairs.

        Args:
            query_text: Review text to search for
            top_k: Number of similar entries to return
            sentiment_filter: Optional sentiment to filter by
            min_score: Minimum verification score to include

        Returns:
            List of similar entries with their metadata
        """
        self._initialize()

        if len(self.metadata) == 0:
            logger.warning("Knowledge base is empty")
            return []

        # Create query embedding
        query_embedding = self.embedding_model.encode([query_text])[0]
        query_embedding = np.array([query_embedding], dtype='float32')

        # Search FAISS index
        # Get more results than needed to allow for filtering
        search_k = min(top_k * 3, len(self.metadata))
        distances, indices = self.index.search(query_embedding, search_k)

        # Filter and rank results
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx == -1:  # Invalid index
                continue

            entry = self.metadata[idx].copy()
            entry["distance"] = float(distance)

            # Apply filters
            if sentiment_filter and entry["sentiment"] != sentiment_filter:
                continue

            if entry["verification_score"] < min_score:
                continue

            results.append(entry)

            if len(results) >= top_k:
                break

        logger.debug(
            "Knowledge base search complete",
            query_length=len(query_text),
            results_found=len(results)
        )

        return results

    def save(self):
        """Save FAISS index and metadata to disk."""
        self._initialize()

        # Create directory if it doesn't exist
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, str(self.index_path))

        # Save metadata
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)

        logger.info(
            "Knowledge base saved",
            path=str(self.index_path),
            num_entries=len(self.metadata)
        )

    def get_stats(self) -> Dict:
        """Get knowledge base statistics."""
        self._initialize()

        sentiment_counts = {}
        for entry in self.metadata:
            sentiment = entry["sentiment"]
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1

        avg_score = (
            sum(e["verification_score"] for e in self.metadata) / len(self.metadata)
            if self.metadata else 0.0
        )

        return {
            "total_entries": len(self.metadata),
            "sentiment_distribution": sentiment_counts,
            "avg_verification_score": avg_score
        }

    def clear(self):
        """Clear all entries from knowledge base (use with caution)."""
        self._initialize()
        embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatL2(embedding_dim)
        self.metadata = []
        logger.warning("Knowledge base cleared")


# Global knowledge base instance
knowledge_base = KnowledgeBase()
