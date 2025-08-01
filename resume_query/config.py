"""
Configuration and Environment Setup for Resume Query System
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Elasticsearch configuration
ELASTICSEARCH_HOST = "http://localhost:9200"
DEFAULT_INDEX_NAME = "resume_bm25_index"

# Search configuration
DEFAULT_SEARCH_RESULTS = 10
MAX_SEARCH_RESULTS = 20
DEFAULT_RECALL_SIZE = 100

# Hybrid search weights
DEFAULT_SEMANTIC_WEIGHT = 0.7
DEFAULT_BM25_WEIGHT = 0.3

# Database configuration
DEFAULT_DB_NAME = "resume_db"
DEFAULT_BATCH_SIZE = 128
EMBEDDING_MODEL = "voyage-2"

# Voyage AI configuration
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")

# Cohere configuration
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

# File paths
DEFAULT_RESUME_FILE = "10000_candidates_with_parsed_resumes.json"

# Lever API configuration
LEVER_API_BASE_URL = "https://api.lever.co/v1"
LEVER_API_KEY = os.getenv("LEVER_API_KEY")

# Reranking configuration (Cohere)
RERANK_MODEL = "rerank-v3.5"  # Options: "rerank-v3.5", "rerank-english-v3.0", "rerank-multilingual-v3.0", "rerank-english-v2.0"
RERANK_TOP_N = 50  # Number of top results to rerank (for efficiency)
ENABLE_RERANKING = True  # Whether to enable reranking by default
RERANK_CACHE_ENABLED = True  # Whether to cache rerank results


def get_db_name_from_file(resume_file: str) -> str:
    """
    Generate a unique database name based on the resume file name.
    
    Args:
        resume_file: Path to the resume JSON file
        
    Returns:
        Database name string
    """
    # Extract filename without extension
    filename = os.path.splitext(os.path.basename(resume_file))[0]
    # Clean filename for use as database name (remove special chars, replace with underscore)
    clean_name = "".join(c if c.isalnum() else "_" for c in filename)
    return f"resume_db_{clean_name}"