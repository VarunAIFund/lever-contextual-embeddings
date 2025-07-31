"""
Search Module

Handles BM25, hybrid search, and search result processing.
"""

from typing import List, Dict, Any
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from resume_query.config import (
    ELASTICSEARCH_HOST, DEFAULT_INDEX_NAME, DEFAULT_RECALL_SIZE,
    DEFAULT_SEMANTIC_WEIGHT, DEFAULT_BM25_WEIGHT
)


class ResumeElasticsearchBM25:
    """Elasticsearch-based BM25 search optimized for resume data."""
    
    def __init__(self, index_name: str = DEFAULT_INDEX_NAME):
        self.es_client = Elasticsearch(ELASTICSEARCH_HOST)
        self.index_name = index_name
        self.create_index()

    def create_index(self):
        """Create Elasticsearch index optimized for resume data."""
        index_settings = {
            "settings": {
                "analysis": {"analyzer": {"default": {"type": "english"}}},
                "similarity": {"default": {"type": "BM25"}},
                "index.queries.cache.enabled": False
            },
            "mappings": {
                "properties": {
                    "content": {"type": "text", "analyzer": "english"},
                    "candidate_id": {"type": "keyword", "index": False},
                    "name": {"type": "text", "analyzer": "english"},
                    "email": {"type": "keyword", "index": False},
                    "chunk_type": {"type": "keyword", "index": False},
                    "company": {"type": "text", "analyzer": "english"},
                    "title": {"type": "text", "analyzer": "english"},
                    "summary": {"type": "text", "analyzer": "english"},
                }
            },
        }
        if not self.es_client.indices.exists(index=self.index_name):
            self.es_client.indices.create(index=self.index_name, body=index_settings)
            print(f"Created resume index: {self.index_name}")

    def index_documents(self, resume_chunks: List[Dict[str, Any]]):
        """
        Index resume chunks in Elasticsearch.
        
        Args:
            resume_chunks: List of resume chunk metadata
            
        Returns:
            Number of successfully indexed documents
        """
        actions = []
        for i, chunk_meta in enumerate(resume_chunks):
            source_data = {
                "content": chunk_meta.get('content', ''),
                "candidate_id": chunk_meta.get('candidate_id', ''),
                "name": chunk_meta.get('name', ''),
                "email": chunk_meta.get('email', ''),
                "chunk_type": chunk_meta.get('chunk_type', ''),
            }
            
            # Add position-specific fields if available
            if chunk_meta.get('chunk_type') == 'position':
                source_data.update({
                    "company": chunk_meta.get('company', ''),
                    "title": chunk_meta.get('title', ''),
                    "summary": chunk_meta.get('summary', ''),
                })
            
            actions.append({
                "_index": self.index_name,
                "_id": i,
                "_source": source_data
            })
        
        success, _ = bulk(self.es_client, actions)
        self.es_client.indices.refresh(index=self.index_name)
        return success

    def search(self, query: str, k: int = 20) -> List[Dict[str, Any]]:
        """
        Search resumes using BM25.
        
        Args:
            query: Search query string
            k: Number of results to return
            
        Returns:
            List of BM25 search results
        """
        self.es_client.indices.refresh(index=self.index_name)
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["content^2", "name^1.5", "company^1.5", "title^1.5", "summary^1.2"],
                    "type": "best_fields"
                }
            },
            "size": k,
        }
        response = self.es_client.search(index=self.index_name, body=search_body)
        return [
            {
                "candidate_id": hit["_source"]["candidate_id"],
                "name": hit["_source"]["name"],
                "email": hit["_source"]["email"],
                "chunk_type": hit["_source"]["chunk_type"],
                "content": hit["_source"]["content"],
                "score": hit["_score"],
                "company": hit["_source"].get("company", ""),
                "title": hit["_source"].get("title", ""),
            }
            for hit in response["hits"]["hits"]
        ]


def create_resume_bm25_index(db) -> ResumeElasticsearchBM25:
    """
    Create and populate BM25 index from ResumeVectorDB.
    
    Args:
        db: ResumeVectorDB instance
        
    Returns:
        Initialized ResumeElasticsearchBM25 instance
    """
    es_bm25 = ResumeElasticsearchBM25()
    es_bm25.index_documents(db.metadata)
    return es_bm25


def retrieve_hybrid_resume(query: str, db, es_bm25: ResumeElasticsearchBM25, k: int, 
                          semantic_weight: float = DEFAULT_SEMANTIC_WEIGHT, 
                          bm25_weight: float = DEFAULT_BM25_WEIGHT):
    """
    Perform hybrid search combining semantic search and BM25 for resumes.
    
    Args:
        query: Search query
        db: ResumeVectorDB instance
        es_bm25: ResumeElasticsearchBM25 instance
        k: Number of final results to return
        semantic_weight: Weight for semantic search results
        bm25_weight: Weight for BM25 search results
        
    Returns:
        Tuple of (final_results, semantic_count, bm25_count)
    """
    num_chunks_to_recall = min(DEFAULT_RECALL_SIZE, len(db.metadata))

    # Semantic search
    semantic_results = db.search(query, k=num_chunks_to_recall)
    semantic_chunk_ids = [(result['metadata']['candidate_id'], result['metadata'].get('position_index', 0), result['metadata']['chunk_type']) 
                         for result in semantic_results]

    # BM25 search
    bm25_results = es_bm25.search(query, k=num_chunks_to_recall)
    bm25_chunk_ids = [(result['candidate_id'], 0, result['chunk_type']) for result in bm25_results]

    # Combine and score results
    all_chunk_ids = list(set(semantic_chunk_ids + bm25_chunk_ids))
    chunk_id_to_score = {}

    # Score chunks based on ranking in each search method
    for chunk_id in all_chunk_ids:
        score = 0
        if chunk_id in semantic_chunk_ids:
            index = semantic_chunk_ids.index(chunk_id)
            score += semantic_weight * (1 / (index + 1))
        if chunk_id in bm25_chunk_ids:
            index = bm25_chunk_ids.index(chunk_id)
            score += bm25_weight * (1 / (index + 1))
        chunk_id_to_score[chunk_id] = score

    # Sort by combined score
    sorted_chunk_ids = sorted(chunk_id_to_score.keys(), 
                             key=lambda x: chunk_id_to_score[x], reverse=True)

    # Prepare final results
    final_results = []
    semantic_count = 0
    bm25_count = 0
    
    for chunk_id in sorted_chunk_ids[:k]:
        candidate_id, pos_idx, chunk_type = chunk_id
        
        # Find the corresponding metadata
        chunk_metadata = next((meta for meta in db.metadata 
                              if meta['candidate_id'] == candidate_id and 
                              meta['chunk_type'] == chunk_type), None)
        
        if chunk_metadata:
            is_from_semantic = chunk_id in semantic_chunk_ids
            is_from_bm25 = chunk_id in bm25_chunk_ids
            
            final_results.append({
                'metadata': chunk_metadata,
                'content': db.get_content_from_metadata(chunk_metadata),
                'score': chunk_id_to_score[chunk_id],
                'from_semantic': is_from_semantic,
                'from_bm25': is_from_bm25
            })
            
            if is_from_semantic and not is_from_bm25:
                semantic_count += 1
            elif is_from_bm25 and not is_from_semantic:
                bm25_count += 1
            else:  # in both
                semantic_count += 0.5
                bm25_count += 0.5

    return final_results, semantic_count, bm25_count