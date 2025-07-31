"""
Resume Query Package

A modular resume search system with semantic search, BM25, and hybrid search capabilities.
"""

from resume_query.database import ResumeVectorDB
from resume_query.search import ResumeElasticsearchBM25, retrieve_hybrid_resume, create_resume_bm25_index
from resume_query.formatting import format_resume_results, show_full_resume_result
from resume_query.interactive import interactive_resume_query_loop
from resume_query.main import main

__version__ = "1.0.0"
__all__ = [
    "ResumeVectorDB",
    "ResumeElasticsearchBM25", 
    "retrieve_hybrid_resume",
    "create_resume_bm25_index",
    "format_resume_results",
    "show_full_resume_result", 
    "interactive_resume_query_loop",
    "main"
]