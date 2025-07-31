"""
Resume Vector Database Module

Handles vector database operations for resume search.
"""

import os
import pickle
import json
import numpy as np
import voyageai
from typing import List, Dict, Any
from tqdm import tqdm

from resume_query.config import DEFAULT_DB_NAME, DEFAULT_BATCH_SIZE, EMBEDDING_MODEL
from resume_query.data_processing import process_resume_data, get_content_from_metadata


class ResumeVectorDB:
    """Vector Database optimized for candidate/resume data."""
    
    def __init__(self, name: str = DEFAULT_DB_NAME, api_key=None):
        if api_key is None:
            api_key = os.getenv("VOYAGE_API_KEY")
        self.client = voyageai.Client(api_key=api_key)
        self.name = name
        self.embeddings = []
        self.metadata = []
        self.query_cache = {}
        self.db_path = f"./data/{name}/vector_db.pkl"

    def load_data(self, resume_file_path: str):
        """
        Load resume data and create embeddings.
        
        Args:
            resume_file_path: Path to the JSON file containing resume data
        """
        if self.embeddings and self.metadata:
            print("Resume database is already loaded. Skipping data loading.")
            return
        if os.path.exists(self.db_path):
            print("Loading resume database from disk.")
            self.load_db()
            return

        # Load resume data
        print(f"Loading resume data from {resume_file_path}...")
        with open(resume_file_path, 'r') as f:
            resume_data = json.load(f)
        
        print(f"Found {len(resume_data)} candidates")
        
        # Process into chunks
        chunks = process_resume_data(resume_data)
        
        # Extract texts and metadata
        texts_to_embed = [chunk['content'] for chunk in chunks]
        metadata = [chunk['metadata'] for chunk in chunks]
        
        print(f"Created {len(texts_to_embed)} searchable chunks")
        
        # Create embeddings
        self._embed_and_store(texts_to_embed, metadata)
        self.save_db()
        
        print(f"Resume database loaded and saved. Total chunks processed: {len(texts_to_embed)}")

    def _embed_and_store(self, texts: List[str], data: List[Dict[str, Any]]):
        """
        Create embeddings for text chunks.
        
        Args:
            texts: List of text strings to embed
            data: List of corresponding metadata dictionaries
        """
        batch_size = DEFAULT_BATCH_SIZE
        with tqdm(total=len(texts), desc="Creating embeddings") as pbar:
            result = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                batch_result = self.client.embed(batch, model=EMBEDDING_MODEL).embeddings
                result.extend(batch_result)
                pbar.update(len(batch))
        
        self.embeddings = result
        self.metadata = data

    def search(self, query: str, k: int = 20) -> List[Dict[str, Any]]:
        """
        Search for candidates matching the query.
        
        Args:
            query: Search query string
            k: Number of top results to retrieve
            
        Returns:
            List of search results with metadata and similarity scores
        """
        if query in self.query_cache:
            query_embedding = self.query_cache[query]
        else:
            query_embedding = self.client.embed([query], model=EMBEDDING_MODEL).embeddings[0]
            self.query_cache[query] = query_embedding

        if not self.embeddings:
            raise ValueError("No data loaded in the resume database.")

        similarities = np.dot(self.embeddings, query_embedding)
        top_indices = np.argsort(similarities)[::-1][:k]
        
        top_results = []
        for idx in top_indices:
            result = {
                "metadata": self.metadata[idx],
                "similarity": float(similarities[idx]),
                "content": get_content_from_metadata(self.metadata[idx])
            }
            top_results.append(result)
        
        return top_results

    def get_content_from_metadata(self, metadata: Dict[str, Any]) -> str:
        """
        Reconstruct content from metadata for display.
        
        Args:
            metadata: Chunk metadata dictionary
            
        Returns:
            Reconstructed content string
        """
        return get_content_from_metadata(metadata)

    def save_db(self):
        """Save database to disk."""
        data = {
            "embeddings": self.embeddings,
            "metadata": self.metadata,
            "query_cache": json.dumps(self.query_cache),
        }
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, "wb") as file:
            pickle.dump(data, file)

    def load_db(self):
        """Load database from disk."""
        if not os.path.exists(self.db_path):
            raise ValueError("Resume database file not found. Use load_data to create a new database.")
        with open(self.db_path, "rb") as file:
            data = pickle.load(file)
        self.embeddings = data["embeddings"]
        self.metadata = data["metadata"]
        self.query_cache = json.loads(data["query_cache"])