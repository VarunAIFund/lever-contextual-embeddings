"""
Interactive Module

Handles the interactive CLI query loop and user interface.
"""

from resume_query.search import create_resume_bm25_index, retrieve_hybrid_resume
from resume_query.formatting import format_resume_results, show_full_resume_result
from resume_query.config import DEFAULT_SEARCH_RESULTS, MAX_SEARCH_RESULTS


def interactive_resume_query_loop(db) -> None:
    """
    Main interactive resume query loop with hybrid search options.
    
    Args:
        db: ResumeVectorDB instance
    """
    print("\n🚀 Resume Search Interface Ready!")
    print("💡 Search Tips:")
    print("   - Search by skills: 'Python developer', 'data scientist', 'ML engineer'")
    print("   - Search by industry: 'healthcare', 'fintech', 'SaaS'")
    print("   - Search by role: 'CEO', 'product manager', 'software engineer'")
    print("   - Search by company: 'Google', 'startup', 'Fortune 500'")
    print("   - Type 'quit', 'exit', or 'q' to exit")
    print("   - Add ':N' after your query to get N results")
    print("   - Add 'full:' before your query to see full content")
    print("   - Add 'hybrid:' before your query for hybrid search (semantic + BM25)")
    print("   - Add 'bm25:' before your query for keyword-only search")
    print("   - Type a number (1-N) to see full details of that result")
    
    # Try to initialize BM25 search
    es_bm25 = None
    try:
        print("🔧 Initializing hybrid search capabilities...")
        es_bm25 = create_resume_bm25_index(db)
        print("✅ Hybrid search ready! Use 'hybrid:' or 'bm25:' prefixes for enhanced search.")
    except Exception as e:
        print(f"⚠️ Hybrid search unavailable (Elasticsearch not running): {e}")
        print("📌 Falling back to semantic search only. Start Elasticsearch for hybrid search.")
    
    current_results = []
    
    while True:
        try:
            # Get user input
            user_input = input("\n❓ Search for candidates: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'q', '']:
                print("👋 Happy hiring!")
                break
            
            # Check if user wants to see full content of a specific result
            if user_input.isdigit() and current_results:
                result_num = int(user_input)
                show_full_resume_result(current_results, result_num)
                continue
            
            # Parse search mode and options
            search_mode, query, k, show_full = parse_user_input(user_input)
            
            # Validate inputs
            if not query:
                print("⚠️ Please enter a valid search query.")
                continue
                
            if k > MAX_SEARCH_RESULTS:
                print(f"⚠️ Maximum {MAX_SEARCH_RESULTS} results allowed. Setting to {MAX_SEARCH_RESULTS}.")
                k = MAX_SEARCH_RESULTS
            elif k < 1:
                print("⚠️ Minimum 1 result required. Setting to 1.")
                k = 1
            
            # Perform search based on mode
            results = perform_search(search_mode, query, k, show_full, db, es_bm25)
            current_results = results
            
            # Display results
            if results:
                format_resume_results(results, query, show_full_content=show_full)
                if not show_full and any(len(r['content']) > 300 for r in results):
                    print(f"\n💡 Tip: Type a number (1-{len(results)}) to see full details of that candidate")
                    print("💡 Or use 'full:your query' to see all full details at once")
            else:
                print("❌ No matching candidates found.")
                
        except KeyboardInterrupt:
            print("\n👋 Happy hiring!")
            break
        except Exception as e:
            print(f"❌ Error occurred: {e}")
            print("Please try again.")
    
    # Cleanup Elasticsearch index
    if es_bm25:
        try:
            if es_bm25.es_client.indices.exists(index=es_bm25.index_name):
                es_bm25.es_client.indices.delete(index=es_bm25.index_name)
                print(f"🧹 Cleaned up Elasticsearch index: {es_bm25.index_name}")
        except Exception as e:
            print(f"⚠️ Could not cleanup Elasticsearch index: {e}")


def parse_user_input(user_input: str) -> tuple:
    """
    Parse user input to extract search mode, query, result count, and options.
    
    Args:
        user_input: Raw user input string
        
    Returns:
        Tuple of (search_mode, query, k, show_full)
    """
    show_full = False
    search_mode = "semantic"  # Default
    
    # Check for search mode and full content mode
    if user_input.lower().startswith('full:'):
        show_full = True
        user_input = user_input[5:].strip()
    elif user_input.lower().startswith('hybrid:'):
        search_mode = "hybrid"
        user_input = user_input[7:].strip()
        if user_input.startswith('full:'):
            show_full = True
            user_input = user_input[5:].strip()
    elif user_input.lower().startswith('bm25:'):
        search_mode = "bm25"
        user_input = user_input[5:].strip()
        if user_input.startswith('full:'):
            show_full = True
            user_input = user_input[5:].strip()
    
    # Parse query and optional result count
    if ':' in user_input and user_input.split(':')[-1].isdigit():
        query, k_str = user_input.rsplit(':', 1)
        k = int(k_str)
        query = query.strip()
    else:
        query = user_input
        k = DEFAULT_SEARCH_RESULTS
    
    return search_mode, query, k, show_full


def perform_search(search_mode: str, query: str, k: int, show_full: bool, db, es_bm25):
    """
    Perform search based on the specified mode.
    
    Args:
        search_mode: Type of search ("semantic", "hybrid", "bm25")
        query: Search query string
        k: Number of results to return
        show_full: Whether showing full content
        db: ResumeVectorDB instance
        es_bm25: ResumeElasticsearchBM25 instance or None
        
    Returns:
        List of search results
    """
    if search_mode == "hybrid" and es_bm25:
        print(f"🔎 Hybrid searching for '{query}' (semantic + BM25, top {k} matches)...")
        if show_full:
            print("📖 Showing full details for all results...")
        
        hybrid_results, semantic_count, bm25_count = retrieve_hybrid_resume(query, db, es_bm25, k)
        results = hybrid_results
        print(f"📊 Results from: {semantic_count:.1f} semantic, {bm25_count:.1f} BM25")
        
    elif search_mode == "bm25" and es_bm25:
        print(f"🔎 BM25 keyword searching for '{query}' (top {k} matches)...")
        if show_full:
            print("📖 Showing full details for all results...")
        
        bm25_results = es_bm25.search(query, k=k)
        # Convert BM25 results to standard format
        results = []
        for result in bm25_results:
            # Find corresponding metadata in the database
            metadata = next((meta for meta in db.metadata 
                           if meta['candidate_id'] == result['candidate_id']), None)
            if metadata:
                results.append({
                    'metadata': metadata,
                    'content': result['content'],
                    'similarity': result['score']
                })
    else:
        if search_mode != "semantic":
            print(f"⚠️ {search_mode.title()} search unavailable, using semantic search")
        print(f"🔎 Semantic searching for '{query}' (top {k} matches)...")
        if show_full:
            print("📖 Showing full details for all results...")
        
        results = db.search(query, k=k)
    
    return results