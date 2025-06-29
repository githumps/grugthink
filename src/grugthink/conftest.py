"""
Global pytest configuration and fixtures for CI optimization.
"""

import importlib.util
import os
import sys
import types
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="session", autouse=True)
def mock_heavy_dependencies():
    """Mock heavy dependencies to speed up CI."""

    # Mock FAISS completely
    if "faiss" not in sys.modules:
        fake_faiss = types.ModuleType("faiss")
        fake_faiss.__spec__ = importlib.util.spec_from_loader("faiss", loader=None)

        # Minimal FAISS implementation for tests
        class IndexFlatL2:
            def __init__(self, dim):
                self.dim = dim
                self.ntotal = 0

            def add(self, vecs):
                self.ntotal += len(vecs)

            def reset(self):
                self.ntotal = 0

            def search(self, queries, k):
                import numpy as np

                batch_size = len(queries)
                dists = np.zeros((batch_size, k), dtype=np.float32)
                idx = np.full((batch_size, k), -1, dtype=np.int64)
                return dists, idx

        class IndexIDMap:
            def __init__(self, index):
                self.index = index
                self.ntotal = 0

            def add_with_ids(self, embeddings, ids):
                self.index.add(embeddings)
                self.ntotal = self.index.ntotal

            def search(self, queries, k):
                return self.index.search(queries, k)

            def reset(self):
                self.index.reset()
                self.ntotal = 0

        def write_index(index, path):
            pass

        def read_index(path):
            return IndexIDMap(IndexFlatL2(384))

        fake_faiss.IndexFlatL2 = IndexFlatL2
        fake_faiss.IndexIDMap = IndexIDMap
        fake_faiss.write_index = write_index
        fake_faiss.read_index = read_index
        sys.modules["faiss"] = fake_faiss

    # Mock sentence transformers
    if "sentence_transformers" not in sys.modules:
        fake_st = types.ModuleType("sentence_transformers")
        fake_st.__spec__ = importlib.util.spec_from_loader("sentence_transformers", loader=None)

        class SentenceTransformer:
            def __init__(self, model_name, **kwargs):
                self.model_name = model_name

            def encode(self, texts, **kwargs):
                import hashlib

                import numpy as np

                if isinstance(texts, str):
                    texts = [texts]
                # Create deterministic embeddings with keyword-based similarity
                embeddings = []
                for text in texts:
                    # Create embedding based on word content - deterministic
                    words = set(text.lower().replace("?", "").replace(".", "").split())
                    embedding = np.zeros(384, dtype=np.float32)

                    # Use deterministic hash of words as features
                    for word in words:
                        # Use MD5 for deterministic hashing across platforms
                        word_hash = int(hashlib.md5(word.encode()).hexdigest()[:8], 16) % 384
                        embedding[word_hash] += 1.0

                    # Add some keyword-specific features for better matching
                    keyword_map = {
                        "hunt": 10,
                        "mammoth": 11,
                        "grug": 12,
                        "fire": 20,
                        "make": 21,
                        "ugga": 22,
                        "good": 23,
                        "find": 30,
                        "stone": 31,
                        "bork": 32,
                        "shiny": 33,
                        "sky": 40,
                        "blue": 41,
                        "think": 42,
                        "color": 40,  # color->sky mapping
                    }

                    for word in words:
                        if word in keyword_map:
                            embedding[keyword_map[word]] += 2.0  # Boost important keywords

                    # Normalize to unit vector for cosine similarity
                    norm = np.linalg.norm(embedding)
                    if norm > 0:
                        embedding = embedding / norm

                    embeddings.append(embedding)
                return np.array(embeddings, dtype=np.float32)

            def get_sentence_embedding_dimension(self):
                return 384

        fake_st.SentenceTransformer = SentenceTransformer
        sys.modules["sentence_transformers"] = fake_st

    # Mock torch
    if "torch" not in sys.modules:
        fake_torch = types.ModuleType("torch")
        fake_torch.__spec__ = importlib.util.spec_from_loader("torch", loader=None)
        fake_torch.cuda = MagicMock()
        fake_torch.cuda.is_available = MagicMock(return_value=False)
        sys.modules["torch"] = fake_torch


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    os.environ.setdefault("DISCORD_TOKEN", "test_token")
    os.environ.setdefault("GEMINI_API_KEY", "test_gemini_key")
    os.environ.setdefault("LOG_LEVEL", "WARNING")  # Reduce log noise in tests
