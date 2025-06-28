#!/usr/bin/env python3
"""Grug's Memory Database - SQLite + FAISS
Manages Grug's long-term memory using a relational database for facts
and a vector index for semantic search.
"""

import logging
import os
import sqlite3
import threading

# Conditional imports for heavy dependencies (may be mocked in CI)
try:
    import numpy as np
except ImportError:
    np = None

try:
    import faiss
except ImportError:
    faiss = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from grug_structured_logger import get_logger

log = get_logger(__name__)


class GrugDB:
    def __init__(self, db_path, model_name="all-MiniLM-L6-v2", server_id="global"):
        self.db_path = db_path
        self.server_id = str(server_id)  # Ensure server_id is string
        self.index_path = db_path.replace(".db", f"_{self.server_id}.index")
        self.model_name = model_name
        self.embedder = None
        self.dimension = 384  # Default dimension, will be updated if embedder loads

        self.conn = None
        self.index = None
        self.lock = threading.Lock()

        self._init_db()
        self._load_index()

    def _ensure_embedder_loaded(self):
        if self.embedder is None:
            with self.lock:  # Acquire lock before loading to prevent race conditions
                if self.embedder is None:  # Double-check inside lock
                    log.info("Loading SentenceTransformer model...")
                    if SentenceTransformer is None:
                        import sys
                        if "sentence_transformers" in sys.modules:
                            self.embedder = sys.modules["sentence_transformers"].SentenceTransformer(self.model_name)
                            self.dimension = self.embedder.get_sentence_embedding_dimension()
                        else:
                            log.warning("SentenceTransformer not available, semantic search will be disabled.")
                    else:
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        local_model_path = os.path.join(current_dir, "models", "sentence-transformers", self.model_name)
                        self.embedder = SentenceTransformer(local_model_path, local_files_only=True)
                        self.dimension = self.embedder.get_sentence_embedding_dimension()
                    log.info("SentenceTransformer model loaded.")

    def _init_db(self):
        """Initialize SQLite database and create facts table."""
        try:
            # Ensure the directory for the database file exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id TEXT DEFAULT 'global',
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(server_id, content)
                )
            """)
            self.conn.commit()
            log.info("Database initialized", extra={"db_path": self.db_path})
        except Exception as e:
            log.error("Error initializing database", extra={"error": str(e)})
            raise

    def _load_index(self):
        """Load FAISS index from disk or create a new one."""
        if faiss is None:
            # Use mocked version from conftest.py
            import sys

            if "faiss" in sys.modules:
                faiss_module = sys.modules["faiss"]
                if os.path.exists(self.index_path):
                    try:
                        self.index = faiss_module.read_index(self.index_path)
                        log.info(
                            "Loaded FAISS index", extra={"index_path": self.index_path, "vectors": self.index.ntotal}
                        )
                    except Exception as e:
                        log.error("Failed to load FAISS index, creating new one", extra={"error": str(e)})
                        self._create_new_index()
                else:
                    self._create_new_index()
            else:
                # No FAISS available, create placeholder
                self.index = None
                log.warning("FAISS not available, vector search disabled")
        else:
            # Normal FAISS operation
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
        if faiss is None:
            # Use mocked version
            import sys

            if "faiss" in sys.modules:
                faiss_module = sys.modules["faiss"]
                self.index = faiss_module.IndexIDMap(faiss_module.IndexFlatL2(self.dimension))
            else:
                self.index = None
                return
        else:
            self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.dimension))
        self.rebuild_index()

    def add_fact(self, fact_text: str) -> bool:
        """Add a new fact to the database and the FAISS index."""
        self._ensure_embedder_loaded()
        # Encoding is CPU-bound and can be done outside the lock
        if self.embedder is None:
            # No embedder available, just add to database without vector search
            embedding = None
        else:
            embedding = self.embedder.encode([fact_text])

        with self.lock:
            try:
                # Use a transaction so DB insert and index update succeed or fail together
                with self.conn:
                    cursor = self.conn.execute(
                        "INSERT INTO facts (server_id, content) VALUES (?, ?)",
                        (self.server_id, fact_text),
                    )
                    fact_id = cursor.lastrowid
                    # Add to vector index if available
                    if embedding is not None and self.index is not None and np is not None:
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
        self._ensure_embedder_loaded()
        if self.index is None or self.embedder is None or np is None:
            # No vector search available, return empty results
            return []

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
                    cursor.execute("SELECT content FROM facts WHERE id=? AND server_id=?", (int(i), self.server_id))
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
                cursor.execute(
                    "SELECT content FROM facts WHERE server_id = ? ORDER BY timestamp DESC", (self.server_id,)
                )
                return [row[0] for row in cursor.fetchall()]
            except Exception as e:
                log.error("Error getting all facts", extra={"error": str(e)})
                return []

    def save_index(self):
        """Save the FAISS index to disk."""
        with self.lock:
            try:
                if faiss is None:
                    # Use mocked version
                    import sys

                    if "faiss" in sys.modules:
                        faiss_module = sys.modules["faiss"]
                        faiss_module.write_index(self.index, self.index_path)
                    # If no FAISS available, just skip saving
                else:
                    faiss.write_index(self.index, self.index_path)
                log.info("FAISS index saved", extra={"index_path": self.index_path})
            except Exception as e:
                log.error("Error saving FAISS index", extra={"error": str(e)})

    def rebuild_index(self):
        """Rebuild the entire FAISS index from the SQLite database."""
        if self.index is None or self.embedder is None or np is None:
            # No vector search available, skip rebuild
            log.info("Skipping index rebuild - vector search not available")
            return

        log.info("Rebuilding FAISS index from scratch...")
        with self.lock:
            self.index.reset()
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, content FROM facts WHERE server_id = ? ORDER BY id", (self.server_id,))
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


class GrugServerManager:
    """Manages separate GrugDB instances for each Discord server."""

    def __init__(self, base_db_path, model_name="all-MiniLM-L6-v2"):
        self.base_db_path = base_db_path
        self.model_name = model_name
        self.server_dbs = {}
        self.lock = threading.Lock()
        log.info("Grug server manager initialized", extra={"base_path": base_db_path})

    def get_server_db(self, server_id) -> GrugDB:
        """Get or create a GrugDB instance for a specific server."""
        server_id = str(server_id) if server_id else "dm"  # Handle DMs

        with self.lock:
            if server_id not in self.server_dbs:
                log.info("Creating new Grug brain for server", extra={"server_id": server_id})
                self.server_dbs[server_id] = GrugDB(self.base_db_path, self.model_name, server_id)
            return self.server_dbs[server_id]

    def close_all(self):
        """Close all server database connections."""
        with self.lock:
            for server_id, db in self.server_dbs.items():
                log.info("Closing Grug brain for server", extra={"server_id": server_id})
                db.close()
            self.server_dbs.clear()
        log.info("All Grug brains closed")

    def get_server_stats(self) -> dict:
        """Get statistics about all server databases."""
        stats = {}
        with self.lock:
            for server_id, db in self.server_dbs.items():
                try:
                    facts = db.get_all_facts()
                    stats[server_id] = {"fact_count": len(facts), "index_vectors": db.index.ntotal if db.index else 0}
                except Exception as e:
                    stats[server_id] = {"error": str(e)}
        return stats

    def migrate_global_facts_to_server(self, target_server_id: str = "global"):
        """Migrate facts without server_id to a specific server."""
        with self.lock:
            try:
                # Find facts without server_id (old format)
                cursor = sqlite3.connect(self.base_db_path).cursor()
                cursor.execute("SELECT id, content FROM facts WHERE server_id IS NULL OR server_id = ''")
                old_facts = cursor.fetchall()

                if old_facts:
                    log.info(f"Migrating {len(old_facts)} global facts to server {target_server_id}")
                    # Update them to belong to the target server
                    cursor.execute(
                        "UPDATE facts SET server_id = ? WHERE server_id IS NULL OR server_id = ''", (target_server_id,)
                    )
                    cursor.connection.commit()
                    log.info("Migration completed successfully")
                else:
                    log.info("No global facts found to migrate")

                cursor.connection.close()
            except Exception as e:
                log.error("Error migrating global facts", extra={"error": str(e)})


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
