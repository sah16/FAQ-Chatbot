"""Text embedding generator for vector retrieval."""

from typing import List, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize


class TextEmbedder:
    """Generates normalized TF-IDF vector embeddings for chunks and queries."""

    def __init__(self, max_features: int = 2048):
        self.max_features = max_features
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            analyzer="word",
            max_features=max_features,
            sublinear_tf=True,
            stop_words="english",
            max_df=0.85
        )
        self._is_fitted = False

    def fit_and_embed(self, texts: List[str]) -> List[List[float]]:
        """Fits vectorizer on corpus and returns normalized dense embeddings."""
        if not texts:
            return []

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            analyzer="word",
            max_features=self.max_features,
            sublinear_tf=True,
            stop_words="english",
            max_df=0.85
        )
        matrix = self.vectorizer.fit_transform(texts).toarray()
        normalized = normalize(matrix, norm="l2", axis=1)
        self._is_fitted = True
        return [row.tolist() for row in normalized]

    def embed_text(self, text: str) -> List[float]:
        """Embeds a single query string using the fitted vectorizer."""
        if not self._is_fitted:
            return []

        matrix = self.vectorizer.transform([text]).toarray()
        normalized = normalize(matrix, norm="l2", axis=1)
        return normalized[0].tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embeds a batch of texts."""
        if not self._is_fitted:
            return self.fit_and_embed(texts)
        matrix = self.vectorizer.transform(texts).toarray()
        normalized = normalize(matrix, norm="l2", axis=1)
        return [row.tolist() for row in normalized]
