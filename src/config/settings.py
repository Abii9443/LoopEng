"""Configuration settings for Loop Engineering POC."""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Model configuration
    sentiment_model: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    generation_model: str = "google/flan-t5-base"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    nli_model: str = "microsoft/deberta-v3-small"
    issue_classifier_model: str = "facebook/bart-large-mnli"

    # Device (cuda, mps, or cpu)
    device: str = "cpu"

    # Storage paths
    database_path: str = "data/traces/loop_eng.db"
    faiss_index_path: str = "data/embeddings/knowledge_base.faiss"

    # Loop parameters
    verification_threshold: float = 0.70
    max_retries: int = 3
    hill_climbing_batch_size: int = 100
    hill_climbing_frequency: int = 100  # Trigger every N reviews

    # Logging
    log_level: str = "INFO"

    # Dataset
    dataset_name: str = "amazon_polarity"
    dataset_split: str = "train[:10000]"

    # Verification criteria weights
    weight_relevance: float = 0.25
    weight_tone: float = 0.20
    weight_completeness: float = 0.25
    weight_actionability: float = 0.20
    weight_accuracy: float = 0.10

    # A/B testing parameters
    ab_test_sample_size: int = 20
    ab_test_min_improvement: float = 0.10  # 10% improvement required

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def get_database_dir(self) -> Path:
        """Get database directory, creating if it doesn't exist."""
        db_path = Path(self.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path.parent

    def get_faiss_dir(self) -> Path:
        """Get FAISS index directory, creating if it doesn't exist."""
        faiss_path = Path(self.faiss_index_path)
        faiss_path.parent.mkdir(parents=True, exist_ok=True)
        return faiss_path.parent

    def get_verification_weights(self) -> dict:
        """Get verification criteria weights as a dictionary."""
        return {
            "relevance": self.weight_relevance,
            "tone": self.weight_tone,
            "completeness": self.weight_completeness,
            "actionability": self.weight_actionability,
            "accuracy": self.weight_accuracy,
        }


# Global settings instance
settings = Settings()
