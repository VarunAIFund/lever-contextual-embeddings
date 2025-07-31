#!/usr/bin/env python3
"""
Resume Query Web Frontend

Flask web application that provides a browser interface for the resume_query system.
"""

from flask import Flask, render_template, request, jsonify
import json
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
reranker = None  # Voyage AI reranker instance

def initialize_database():
    """Initialize the resume database and search indices."""
    global resume_db, es_bm25, db_initialized, candidates_data, reranker
    
    if db_initialized:
        return True
    
    try:
        print("🚀 Initializing Resume Database for Web Interface...")
        
        # Generate database name based on resume file
        db_name = get_db_name_from_file(DEFAULT_RESUME_FILE)
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
            print("🔧 Initializing Voyage AI reranker...")
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
        'resume_file': DEFAULT_RESUME_FILE
    })

@app.route('/api/search', methods=['POST'])
def search():
    """Perform resume search."""
    if not db_initialized:
        if not initialize_database():
            return jsonify({'error': 'Database not initialized'}), 500
    
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        search_mode = data.get('mode', 'semantic')  # semantic, bm25, hybrid
        k = min(int(data.get('limit', 10)), 20)  # Max 20 results
        use_reranking = data.get('rerank', False)  # Whether to apply reranking
        rerank_model = data.get('rerank_model', 'rerank-lite-1')  # Which rerank model to use
        
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
        
        # Apply reranking if requested and available
        if use_reranking and results:
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
        elif use_reranking:
            search_info['rerank_unavailable'] = 'Reranker not available'
        
        # Format results for JSON response
        formatted_results = []
        for result in results:
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
            
            formatted_results.append(formatted_result)
        
        return jsonify({
            'results': formatted_results,
            'query': query,
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
        
        # Separate candidate summary and positions
        candidate_summary = next((chunk for chunk in candidate_chunks 
                                if chunk['chunk_type'] == 'candidate_summary'), None)
        positions = [chunk for chunk in candidate_chunks 
                    if chunk['chunk_type'] == 'position']
        
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
            'links': candidate_links,
            'total_positions': len(positions)
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