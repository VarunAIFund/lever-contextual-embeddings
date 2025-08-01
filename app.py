#!/usr/bin/env python3
"""
Resume Query Web Frontend

Flask web application that provides a browser interface for the resume_query system.
"""

from flask import Flask, render_template, request, jsonify
import json
import os
import glob
from resume_query.database import ResumeVectorDB
from resume_query.search import create_resume_bm25_index, retrieve_hybrid_resume
from resume_query.config import DEFAULT_RESUME_FILE, get_db_name_from_file
from resume_query.reranking import create_reranker

app = Flask(__name__)

# Global variables to store database instances
resume_db = None
es_bm25 = None
db_initialized = False
candidates_data = None  # Store original JSON data for links access
reranker = None  # Cohere reranker instance
current_database = None  # Currently active database name

def perform_weighted_search(criteria, weights, threshold, db, k=20):
    """
    Perform weighted multi-criteria search.
    
    Args:
        criteria: Dict of criterion_name -> query_string
        weights: Dict of criterion_name -> weight (0-1)
        threshold: Minimum score threshold (0-1)
        db: ResumeVectorDB instance
        k: Number of results to return
    
    Returns:
        List of search results with weighted scores
    """
    candidate_scores = {}
    
    # Run separate searches for each criterion
    for criterion_name, query in criteria.items():
        if not query.strip():
            continue
            
        weight = weights.get(criterion_name, 0)
        if weight == 0:
            continue
            
        print(f"🔍 Searching {criterion_name}: '{query}' (weight: {weight:.1%})")
        
        # Use existing semantic search
        results = db.search(query, k=100)  # Get more results for better scoring
        
        # Score each candidate for this criterion
        for result in results:
            candidate_id = result['metadata']['candidate_id']
            similarity = result['similarity']
            weighted_score = similarity * weight
            
            if candidate_id not in candidate_scores:
                candidate_scores[candidate_id] = {
                    'total_score': 0,
                    'breakdown': {},
                    'candidate_data': None
                }
            
            # Only keep the best score for each criterion per candidate
            if criterion_name not in candidate_scores[candidate_id]['breakdown'] or \
               similarity > candidate_scores[candidate_id]['breakdown'][criterion_name]['raw_score']:
                
                # Remove old weighted score if exists
                if criterion_name in candidate_scores[candidate_id]['breakdown']:
                    old_weighted = candidate_scores[candidate_id]['breakdown'][criterion_name]['weighted_score']
                    candidate_scores[candidate_id]['total_score'] -= old_weighted
                
                # Add new weighted score
                candidate_scores[candidate_id]['total_score'] += weighted_score
                candidate_scores[candidate_id]['breakdown'][criterion_name] = {
                    'raw_score': float(similarity),
                    'weighted_score': float(weighted_score),
                    'weight': float(weight)
                }
                
                # Store best matching result data for this candidate
                if not candidate_scores[candidate_id]['candidate_data']:
                    candidate_scores[candidate_id]['candidate_data'] = result
    
    print(f"📊 Scored {len(candidate_scores)} candidates, threshold: {threshold:.1%}")
    
    # Filter by threshold
    filtered_candidates = {
        cid: data for cid, data in candidate_scores.items() 
        if data['total_score'] >= threshold
    }
    
    print(f"✅ {len(filtered_candidates)} candidates above threshold")
    
    # Sort by total score and format results
    sorted_candidates = sorted(
        filtered_candidates.items(), 
        key=lambda x: x[1]['total_score'], 
        reverse=True
    )[:k]
    
    # Format results
    formatted_results = []
    for candidate_id, score_data in sorted_candidates:
        result = score_data['candidate_data']
        if result:
            formatted_result = {
                'candidate_id': candidate_id,
                'name': result['metadata']['name'],
                'email': result['metadata']['email'],
                'chunk_type': result['metadata']['chunk_type'],
                'similarity': float(score_data['total_score']),
                'content': result['content'],
                'metadata': result['metadata'],
                'weighted_score': float(score_data['total_score']),
                'score_breakdown': score_data['breakdown']
            }
            formatted_results.append(formatted_result)
    
    return formatted_results

def get_available_databases():
    """Scan data folder and return list of available databases."""
    databases = []
    data_dir = "./data"
    
    if not os.path.exists(data_dir):
        return databases
    
    # Look for directories containing vector_db.pkl files
    for item in os.listdir(data_dir):
        db_path = os.path.join(data_dir, item)
        if os.path.isdir(db_path):
            vector_db_file = os.path.join(db_path, "vector_db.pkl")
            if os.path.exists(vector_db_file):
                databases.append({
                    'name': item,
                    'path': db_path,
                    'size': os.path.getsize(vector_db_file)
                })
    
    return sorted(databases, key=lambda x: x['name'])

def initialize_database(db_name=None):
    """Initialize the resume database and search indices."""
    global resume_db, es_bm25, db_initialized, candidates_data, reranker, current_database
    
    # If db_name is provided or we're switching databases, reset initialization
    if db_name and current_database != db_name:
        db_initialized = False
        resume_db = None
        es_bm25 = None
        candidates_data = None
        current_database = db_name
    elif db_initialized and not db_name:
        return True
    
    try:
        print("🚀 Initializing Resume Database for Web Interface...")
        
        # Use provided db_name or generate from default file
        if not db_name:
            db_name = get_db_name_from_file(DEFAULT_RESUME_FILE)
            current_database = db_name
        
        print(f"📁 Using database: {db_name}")
        
        # Initialize ResumeVectorDB
        resume_db = ResumeVectorDB(db_name)
        
        # Load original candidates data (for links access)
        print("📄 Loading original candidates data...")
        with open(DEFAULT_RESUME_FILE, 'r') as f:
            candidates_data = json.load(f)
        
        # Load and process resume data
        resume_db.load_data(DEFAULT_RESUME_FILE)
        
        print(f"✅ Database ready with {len(resume_db.metadata)} searchable chunks!")
        
        # Try to initialize BM25 search
        try:
            print("🔧 Initializing hybrid search capabilities...")
            es_bm25 = create_resume_bm25_index(resume_db)
            print("✅ Hybrid search ready!")
        except Exception as e:
            print(f"⚠️ Hybrid search unavailable (Elasticsearch not running): {e}")
            es_bm25 = None
        
        # Try to initialize reranker
        try:
            print("🔧 Initializing Cohere reranker...")
            reranker = create_reranker()
            if reranker:
                print("✅ Reranking ready!")
            else:
                print("⚠️ Reranker initialization failed")
        except Exception as e:
            print(f"⚠️ Reranking unavailable: {e}")
            reranker = None
        
        db_initialized = True
        return True
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False

@app.route('/')
def index():
    """Serve the main web interface."""
    return render_template('index.html')

@app.route('/api/health')
def health():
    """Get system health and database status."""
    if not db_initialized:
        initialize_database()
    
    return jsonify({
        'status': 'ready' if db_initialized else 'error',
        'database_loaded': resume_db is not None,
        'total_chunks': len(resume_db.metadata) if resume_db else 0,
        'hybrid_search_available': es_bm25 is not None,
        'reranking_available': reranker is not None,
        'resume_file': DEFAULT_RESUME_FILE,
        'current_database': current_database
    })

@app.route('/api/databases')
def list_databases():
    """Get list of available databases."""
    try:
        databases = get_available_databases()
        return jsonify({
            'databases': databases,
            'current': current_database,
            'total': len(databases)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/switch-database', methods=['POST'])
def switch_database():
    """Switch to a different database."""
    try:
        data = request.get_json()
        new_db_name = data.get('database', '').strip()
        
        if not new_db_name:
            return jsonify({'error': 'Database name is required'}), 400
        
        # Check if database exists
        available_dbs = get_available_databases()
        db_names = [db['name'] for db in available_dbs]
        
        if new_db_name not in db_names:
            return jsonify({'error': f'Database "{new_db_name}" not found'}), 404
        
        # Initialize with new database
        success = initialize_database(new_db_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Switched to database: {new_db_name}',
                'database': new_db_name,
                'total_chunks': len(resume_db.metadata) if resume_db else 0
            })
        else:
            return jsonify({'error': 'Failed to initialize database'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search', methods=['POST'])
def search():
    """Perform resume search."""
    if not db_initialized:
        if not initialize_database():
            return jsonify({'error': 'Database not initialized'}), 500
    
    try:
        data = request.get_json()
        search_mode = data.get('mode', 'semantic')  # semantic, bm25, hybrid, weighted
        k = min(int(data.get('limit', 10)), 20)  # Max 20 results
        use_reranking = data.get('rerank', False)  # Whether to apply reranking
        rerank_model = data.get('rerank_model', 'rerank-lite-1')  # Which rerank model to use
        
        # Handle weighted search
        if search_mode == 'weighted':
            criteria = data.get('criteria', {})
            weights = data.get('weights', {})
            threshold = data.get('threshold', 0.7)
            
            # Validate weighted search input
            if not any(criteria.values()):
                return jsonify({'error': 'At least one search criterion is required'}), 400
            
            try:
                results = perform_weighted_search(criteria, weights, threshold, resume_db, k)
                search_info = {
                    'mode': 'weighted',
                    'criteria_used': [k for k, v in criteria.items() if v.strip()],
                    'threshold': threshold,
                    'total_weight': sum(weights.values())
                }
            except Exception as e:
                print(f"❌ Weighted search error: {e}")
                return jsonify({'error': f'Weighted search failed: {str(e)}'}), 500
        else:
            # Regular search modes
            query = data.get('query', '').strip()
            if not query:
                return jsonify({'error': 'Query is required'}), 400
            
            # Perform search based on mode
            if search_mode == 'hybrid' and es_bm25:
                results, semantic_count, bm25_count = retrieve_hybrid_resume(query, resume_db, es_bm25, k)
                search_info = {
                    'mode': 'hybrid',
                    'semantic_count': semantic_count,
                    'bm25_count': bm25_count
                }
            elif search_mode == 'bm25' and es_bm25:
                bm25_results = es_bm25.search(query, k=k)
                # Convert BM25 results to standard format
                results = []
                for result in bm25_results:
                    metadata = next((meta for meta in resume_db.metadata 
                                   if meta['candidate_id'] == result['candidate_id']), None)
                    if metadata:
                        results.append({
                            'metadata': metadata,
                            'content': result['content'],
                            'similarity': result['score']
                        })
                search_info = {'mode': 'bm25'}
            else:
                if search_mode != 'semantic':
                    search_mode = 'semantic'  # Fallback
                results = resume_db.search(query, k=k)
                search_info = {'mode': 'semantic'}
        
        # Apply reranking if requested and available (skip for weighted search)
        if use_reranking and results and search_mode != 'weighted':
            try:
                print(f"🔄 Reranking {len(results)} results with {rerank_model}...")
                
                # Create reranker with specified model or use existing one
                current_reranker = reranker
                if not current_reranker or current_reranker.model != rerank_model:
                    from resume_query.reranking import create_reranker
                    current_reranker = create_reranker(model=rerank_model)
                
                if current_reranker:
                    reranked_results, rerank_metadata = current_reranker.rerank_search_results(
                        query=query,
                        search_results=results,
                        rerank_top_n=min(50, len(results)),  # Rerank top 50 or all if less
                        return_top_k=k
                    )
                    results = reranked_results
                    search_info.update({
                        'reranked': True,
                        'rerank_metadata': rerank_metadata
                    })
                    print(f"✅ Reranking completed: {rerank_metadata.get('candidates_reranked', 0)} candidates reranked with {rerank_model}")
                else:
                    raise Exception(f"Could not create reranker with model {rerank_model}")
                    
            except Exception as e:
                print(f"⚠️ Reranking failed: {e}, using original results")
                search_info['rerank_error'] = str(e)
        elif use_reranking and search_mode == 'weighted':
            search_info['rerank_skipped'] = 'Reranking not applicable to weighted search'
        elif use_reranking:
            search_info['rerank_unavailable'] = 'Reranker not available'
        
        # Format results for JSON response
        formatted_results = []
        try:
            for i, result in enumerate(results):
                try:
                    metadata = result['metadata']
                    formatted_result = {
                        'candidate_id': metadata['candidate_id'],
                        'name': metadata['name'],
                        'email': metadata['email'],
                        'chunk_type': metadata['chunk_type'],
                        'similarity': result.get('similarity', result.get('score', 0)),
                        'content': result['content'],
                        'metadata': metadata  # Include full metadata for details view
                    }
                    
                    # Add rerank score if available
                    if 'rerank_score' in result:
                        formatted_result['rerank_score'] = result['rerank_score']
                        formatted_result['original_rank'] = result.get('original_rank', 0)
                    
                    # Add weighted search scores if available
                    if 'weighted_score' in result:
                        formatted_result['weighted_score'] = result['weighted_score']
                        formatted_result['score_breakdown'] = result.get('score_breakdown', {})
                    
                    formatted_results.append(formatted_result)
                except Exception as format_error:
                    print(f"❌ Error formatting result {i}: {format_error}")
                    print(f"Result data: {result}")
                    continue
        except Exception as results_error:
            print(f"❌ Error processing results: {results_error}")
            print(f"Results type: {type(results)}, length: {len(results) if hasattr(results, '__len__') else 'unknown'}")
            raise
        
        # Handle query field for different search modes
        response_query = ""
        if search_mode == 'weighted':
            # Create a summary of criteria for weighted search
            used_criteria = [f"{k}: {v}" for k, v in criteria.items() if v.strip()]
            response_query = " | ".join(used_criteria)
        else:
            response_query = query
        
        return jsonify({
            'results': formatted_results,
            'query': response_query,
            'total': len(formatted_results),
            'search_info': search_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/candidate/<candidate_id>')
def get_candidate(candidate_id):
    """Get all information for a specific candidate."""
    if not db_initialized:
        if not initialize_database():
            return jsonify({'error': 'Database not initialized'}), 500
    
    try:
        # Find all chunks for this candidate
        candidate_chunks = [meta for meta in resume_db.metadata 
                          if meta['candidate_id'] == candidate_id]
        
        if not candidate_chunks:
            return jsonify({'error': 'Candidate not found'}), 404
        
        # Separate candidate summary, positions, and education
        candidate_summary = next((chunk for chunk in candidate_chunks 
                                if chunk['chunk_type'] == 'candidate_summary'), None)
        positions = [chunk for chunk in candidate_chunks 
                    if chunk['chunk_type'] == 'position']
        education = [chunk for chunk in candidate_chunks 
                    if chunk['chunk_type'] == 'education']
        
        # Find links from original candidates data
        candidate_links = []
        if candidates_data:
            original_candidate = next((c for c in candidates_data 
                                     if c.get('candidate_id') == candidate_id), None)
            if original_candidate:
                candidate_links = original_candidate.get('links', [])
        
        return jsonify({
            'candidate_id': candidate_id,
            'summary': candidate_summary,
            'positions': positions,
            'education': education,
            'links': candidate_links,
            'total_positions': len(positions),
            'total_education': len(education)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🌐 Starting Resume Query Web Interface...")
    print("=" * 50)
    print("📍 Server will be available at: http://localhost:5000")
    print("💡 Press Ctrl+C to stop the server")
    print()
    
    # Initialize database on startup
    initialize_database()
    
    # Run Flask app
    app.run(debug=True, host='127.0.0.1', port=5000)