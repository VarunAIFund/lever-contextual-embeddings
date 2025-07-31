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

# File paths
DEFAULT_RESUME_FILE = "candidates_with_parsed_resumes.json"