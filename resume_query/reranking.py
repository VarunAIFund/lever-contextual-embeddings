"""
Reranking Module

Provides reranking capabilities using Voyage AI to improve search result quality
by reordering candidates based on deeper query-candidate relevance analysis.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import voyageai
from resume_query.config import VOYAGE_API_KEY

logger = logging.getLogger(__name__)


class VoyageReranker:
    """Voyage AI-powered reranker for resume search results."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "rerank-lite-1"):
        """
        Initialize the Voyage AI reranker.
        
        Args:
            api_key: Voyage AI API key (uses VOYAGE_API_KEY env var if None)
            model: Rerank model to use ('rerank-lite-1' or 'rerank-1')
        """
        if api_key is None:
            api_key = VOYAGE_API_KEY
            
        if not api_key:
            raise ValueError("Voyage API key is required. Set VOYAGE_API_KEY environment variable.")
        
        self.client = voyageai.Client(api_key=api_key)
        self.model = model
        self.cache = {}  # Simple query cache
        
        # Model configurations
        self.model_configs = {
            "rerank-lite-1": {
                "max_documents": 100,
                "description": "Fast, lightweight reranking"
            },
            "rerank-1": {
                "max_documents": 100,
                "description": "High-quality reranking"
            }
        }
        
        if model not in self.model_configs:
            logger.warning(f"Unknown model {model}, using rerank-lite-1")
            self.model = "rerank-lite-1"
    
    def rerank_candidates(
        self, 
        query: str, 
        candidates: List[Dict[str, Any]], 
        top_k: Optional[int] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Rerank candidates using Voyage AI rerank API.
        
        Args:
            query: Search query string
            candidates: List of candidate dictionaries with 'content' field
            top_k: Number of top candidates to return (None for all)
            use_cache: Whether to use query caching
            
        Returns:
            List of candidates reordered by relevance with rerank_score added
        """
        if not candidates:
            return candidates
        
        # Check cache
        cache_key = f"{query}:{len(candidates)}:{self.model}"
        if use_cache and cache_key in self.cache:
            logger.debug(f"Using cached rerank results for query: {query}")
            cached_indices = self.cache[cache_key]
            return self._apply_cached_ranking(candidates, cached_indices, top_k)
        
        try:
            # Extract documents for reranking
            documents = []
            for candidate in candidates:
                # Use content field, fallback to reconstructed content
                content = candidate.get('content', '')
                if not content and 'metadata' in candidate:
                    content = self._reconstruct_content(candidate['metadata'])
                documents.append(content)
            
            # Limit documents to model capacity
            max_docs = self.model_configs[self.model]["max_documents"]
            if len(documents) > max_docs:
                logger.warning(f"Truncating {len(documents)} candidates to {max_docs} for reranking")
                documents = documents[:max_docs]
                candidates = candidates[:max_docs]
            
            logger.info(f"Reranking {len(documents)} candidates with {self.model}")
            
            # Call Voyage AI rerank API
            rerank_result = self.client.rerank(
                query=query,
                documents=documents,
                model=self.model,
                top_k=top_k or len(documents)
            )
            
            # Process results
            reranked_candidates = []
            result_indices = []
            
            for result in rerank_result.results:
                original_candidate = candidates[result.index].copy()
                original_candidate['rerank_score'] = result.relevance_score
                original_candidate['original_rank'] = result.index
                reranked_candidates.append(original_candidate)
                result_indices.append(result.index)
            
            # Cache results
            if use_cache:
                self.cache[cache_key] = result_indices
            
            logger.info(f"Successfully reranked {len(reranked_candidates)} candidates")
            return reranked_candidates
            
        except Exception as e:
            logger.error(f"Reranking failed with error: {e}")
            logger.warning("Falling back to original ranking")
            
            # Return original candidates with dummy rerank scores
            fallback_candidates = []
            for i, candidate in enumerate(candidates):
                candidate_copy = candidate.copy()
                candidate_copy['rerank_score'] = candidate.get('similarity', 1.0 - (i * 0.01))
                candidate_copy['original_rank'] = i
                fallback_candidates.append(candidate_copy)
            
            return fallback_candidates[:top_k] if top_k else fallback_candidates
    
    def rerank_search_results(
        self, 
        query: str, 
        search_results: List[Dict[str, Any]], 
        rerank_top_n: int = 50,
        return_top_k: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Rerank search results with metadata about the reranking process.
        
        Args:
            query: Original search query
            search_results: Results from semantic/hybrid search
            rerank_top_n: Number of top results to rerank (for efficiency)
            return_top_k: Final number of results to return
            
        Returns:
            Tuple of (reranked_results, rerank_metadata)
        """
        if not search_results:
            return search_results, {'reranked': False, 'reason': 'No results to rerank'}
        
        # Only rerank top N results for efficiency
        candidates_to_rerank = search_results[:rerank_top_n]
        remaining_candidates = search_results[rerank_top_n:]
        
        logger.info(f"Reranking top {len(candidates_to_rerank)} of {len(search_results)} results")
        
        # Perform reranking
        reranked_candidates = self.rerank_candidates(
            query=query,
            candidates=candidates_to_rerank,
            top_k=return_top_k
        )
        
        # Combine reranked results with remaining candidates
        if remaining_candidates and (not return_top_k or len(reranked_candidates) < return_top_k):
            remaining_needed = return_top_k - len(reranked_candidates) if return_top_k else len(remaining_candidates)
            final_results = reranked_candidates + remaining_candidates[:remaining_needed]
        else:
            final_results = reranked_candidates
        
        # Create metadata
        rerank_metadata = {
            'reranked': True,
            'model': self.model,
            'candidates_reranked': len(candidates_to_rerank),
            'total_candidates': len(search_results),
            'top_rerank_score': reranked_candidates[0]['rerank_score'] if reranked_candidates else 0,
            'rerank_score_range': (
                min(c['rerank_score'] for c in reranked_candidates),
                max(c['rerank_score'] for c in reranked_candidates)
            ) if reranked_candidates else (0, 0)
        }
        
        return final_results, rerank_metadata
    
    def get_rerank_scores(self, query: str, documents: List[str]) -> List[float]:
        """
        Get rerank scores for a list of documents without full candidate processing.
        
        Args:
            query: Search query
            documents: List of document strings
            
        Returns:
            List of relevance scores
        """
        try:
            rerank_result = self.client.rerank(
                query=query,
                documents=documents,
                model=self.model,
                top_k=len(documents)
            )
            
            # Create score array in original order
            scores = [0.0] * len(documents)
            for result in rerank_result.results:
                scores[result.index] = result.relevance_score
            
            return scores
            
        except Exception as e:
            logger.error(f"Failed to get rerank scores: {e}")
            # Return decreasing scores as fallback
            return [1.0 - (i * 0.01) for i in range(len(documents))]
    
    def _apply_cached_ranking(
        self, 
        candidates: List[Dict[str, Any]], 
        cached_indices: List[int], 
        top_k: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Apply cached ranking indices to candidates."""
        reranked = []
        for i, original_index in enumerate(cached_indices):
            if original_index < len(candidates):
                candidate = candidates[original_index].copy()
                candidate['rerank_score'] = 1.0 - (i * 0.01)  # Approximated score
                candidate['original_rank'] = original_index
                reranked.append(candidate)
        
        return reranked[:top_k] if top_k else reranked
    
    def _reconstruct_content(self, metadata: Dict[str, Any]) -> str:
        """Reconstruct content from metadata if content field is missing."""
        if metadata.get('chunk_type') == 'candidate_summary':
            return f"""Location: {metadata.get('location', '')}"""
        else:  # position
            return f"""Company: {metadata.get('company', '')}
Title: {metadata.get('title', '')}
Duration: {metadata.get('start_date', '')} - {metadata.get('end_date', '')}
Location: {metadata.get('location', '')}

Experience Details:
{metadata.get('summary', '')}"""
    
    def clear_cache(self):
        """Clear the reranking cache."""
        self.cache.clear()
        logger.info("Reranking cache cleared")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current reranking model."""
        return {
            'model': self.model,
            'config': self.model_configs.get(self.model, {}),
            'cache_size': len(self.cache)
        }


# Convenience functions for easy integration

def create_reranker(model: str = "rerank-lite-1") -> VoyageReranker:
    """
    Create a VoyageReranker instance with error handling.
    
    Args:
        model: Model to use for reranking
        
    Returns:
        VoyageReranker instance or None if creation fails
    """
    try:
        return VoyageReranker(model=model)
    except Exception as e:
        logger.error(f"Failed to create reranker: {e}")
        return None


def rerank_candidates(
    query: str, 
    candidates: List[Dict[str, Any]], 
    model: str = "rerank-lite-1",
    top_k: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to rerank candidates.
    
    Args:
        query: Search query
        candidates: List of candidates to rerank
        model: Voyage AI model to use
        top_k: Number of top results to return
        
    Returns:
        Reranked candidates or original candidates if reranking fails
    """
    reranker = create_reranker(model)
    if reranker:
        return reranker.rerank_candidates(query, candidates, top_k)
    else:
        logger.warning("Reranking unavailable, returning original results")
        return candidates[:top_k] if top_k else candidates