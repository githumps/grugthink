#!/usr/bin/env python3
"""Grug's Memory Database - SQLite + FAISS
Manages Grug's long-term memory using a relational database for facts
and a vector index for semantic search.
"""

import logging
import os
import sqlite3
import threading

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from grug_structured_logger import get_logger

log = get_logger(__name__)


class GrugDB:
    def __init__(self, db_path, model_name="all-MiniLM-L6-v2"):
        self.db_path = db_path
        self.index_path = db_path.replace(".db", ".index")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_model_path = os.path.join(current_dir, "models", "sentence-transformers", model_name)
        self.embedder = SentenceTransformer(local_model_path, local_files_only=True)
        self.dimension = self.embedder.get_sentence_embedding_dimension()

        self.conn = None
        self.index = None
        self.lock = threading.Lock()

        self._init_db()
        self._load_index()

    def _init_db(self):
        """Initialize SQLite database and create facts table."""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL UNIQUE,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()
            log.info("Database initialized", extra={"db_path": self.db_path})
        except Exception as e:
            log.error("Error initializing database", extra={"error": str(e)})
            raise

    def _load_index(self):
        """Load FAISS index from disk or create a new one."""
        if os.path.exists(self.index_path):
            try:
                self.index = faiss.read_index(self.index_path)
                log.info("Loaded FAISS index", extra={"index_path": self.index_path, "vectors": self.index.ntotal})
            except Exception as e:
                log.error("Failed to load FAISS index, creating new one", extra={"error": str(e)})
                self._create_new_index()
        else:
            self._create_new_index()

    def _create_new_index(self):
        """Create a new FAISS index and build it from existing DB facts."""
        log.info("Creating new FAISS index")
        self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.dimension))
        self.rebuild_index()

    def add_fact(self, fact_text: str) -> bool:
        """Add a new fact to the database and the FAISS index."""
        # Encoding is CPU-bound and can be done outside the lock
        embedding = self.embedder.encode([fact_text])

        with self.lock:
            try:
                # Use a transaction so DB insert and index update succeed or fail together
                with self.conn:
                    cursor = self.conn.execute(
                        "INSERT INTO facts (content) VALUES (?)",
                        (fact_text,),
                    )
                    fact_id = cursor.lastrowid
                    # If this raises, the transaction will be rolled back
                    self.index.add_with_ids(embedding, np.array([fact_id]))

                log.info("Added fact", extra={"fact_id": fact_id, "fact": fact_text})
                return True
            except sqlite3.IntegrityError:
                log.warning("Fact already exists", extra={"fact": fact_text})
                return False
            except Exception as e:
                log.error("Error adding fact", extra={"error": str(e)})
                return False

    def search_facts(self, query: str, k: int = 5) -> list[str]:
        """Search for relevant facts using semantic search."""
        if self.index.ntotal == 0:
            return []

        # Encoding is CPU-bound and can be done outside the lock
        query_embedding = self.embedder.encode([query])

        with self.lock:
            try:
                distances, indices = self.index.search(query_embedding, k)

                results = []
                cursor = self.conn.cursor()
                for i in indices[0]:
                    # FAISS indices are 0-based, SQLite IDs are 1-based
                    # This assumes a direct mapping, which is true if we only add.
                    # For a robust system, we'd use faiss.IndexIDMap
                    cursor.execute("SELECT content FROM facts WHERE id=?", (int(i),))
                    row = cursor.fetchone()
                    if row:
                        results.append(row[0])

                log.info("Found results for query", extra={"query": query, "results": len(results)})
                return results
            except Exception as e:
                log.error("Error searching facts", extra={"error": str(e)})
                return []

    def get_all_facts(self) -> list[str]:
        """Retrieve all facts from the database."""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT content FROM facts ORDER BY timestamp DESC")
                return [row[0] for row in cursor.fetchall()]
            except Exception as e:
                log.error("Error getting all facts", extra={"error": str(e)})
                return []

    def save_index(self):
        """Save the FAISS index to disk."""
        with self.lock:
            try:
                faiss.write_index(self.index, self.index_path)
                log.info("FAISS index saved", extra={"index_path": self.index_path})
            except Exception as e:
                log.error("Error saving FAISS index", extra={"error": str(e)})

    def rebuild_index(self):
        """Rebuild the entire FAISS index from the SQLite database."""
        log.info("Rebuilding FAISS index from scratch...")
        with self.lock:
            self.index.reset()
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, content FROM facts ORDER BY id")
            all_facts_data = cursor.fetchall()

            if all_facts_data:
                ids = np.array([row[0] for row in all_facts_data])
                contents = [row[1] for row in all_facts_data]
                embeddings = self.embedder.encode(contents)
                self.index.add_with_ids(embeddings, ids)

        log.info("Index rebuilt", extra={"vectors": self.index.ntotal})

    def close(self):
        """Close the database connection and save the index."""
        self.save_index()
        if self.conn:
            with self.lock:
                self.conn.close()
                log.info("Database connection closed.")


if __name__ == "__main__":
    # Example usage and migration from grug_lore.json
    logging.basicConfig(level=logging.INFO)
    log.info("Running GrugDB standalone for migration...")

    db = GrugDB(db_path="grug_lore.db")

    # Migrate from old JSON file if it exists
    json_lore_path = "grug_lore.json"
    if os.path.exists(json_lore_path):
        log.info("Found old lore file, attempting migration", extra={"path": json_lore_path})
        import json

        try:
            with open(json_lore_path, "r") as f:
                lore_data = json.load(f)
                facts = lore_data.get("facts", [])
                migrated_count = 0
                for fact in facts:
                    if db.add_fact(fact):
                        migrated_count += 1
                log.info("Migration complete", extra={"migrated": migrated_count, "total": len(facts)})
                # Rename the old file to prevent re-migration
                os.rename(json_lore_path, json_lore_path + ".migrated")
                log.info("Renamed old lore file to avoid re-migration")
        except Exception as e:
            log.error("Error during migration", extra={"error": str(e)})

    # Test search
    print("\n--- Testing Search ---")
    test_query = "what grug think of ugga?"
    results = db.search_facts(test_query)
    print(f"Search results for: '{test_query}'")
    for res in results:
        print(f" - {res}")

    # Close connection
    db.close()
