#!/usr/bin/env python3
"""
Resume Search Interface

This script provides an interactive command-line interface to search through
candidates_with_parsed_resumes.json using the same RAG technology as query_rag.py
but optimized for resume/candidate data.
"""

import os
import pickle
import json
import numpy as np
import voyageai
from typing import List, Dict, Any
from tqdm import tqdm
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class ResumeElasticsearchBM25:
    """Elasticsearch-based BM25 search optimized for resume data."""
    
    def __init__(self, index_name: str = "resume_bm25_index"):
        self.es_client = Elasticsearch("http://localhost:9200")
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
        """Index resume chunks in Elasticsearch."""
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
        """Search resumes using BM25."""
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

class ResumeVectorDB:
    """Vector Database optimized for candidate/resume data."""
    
    def __init__(self, name: str = "resume_db", api_key=None):
        if api_key is None:
            api_key = os.getenv("VOYAGE_API_KEY")
        self.client = voyageai.Client(api_key=api_key)
        self.name = name
        self.embeddings = []
        self.metadata = []
        self.query_cache = {}
        self.db_path = f"./data/{name}/vector_db.pkl"

    def process_resume_data(self, resume_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process resume JSON data into searchable chunks."""
        chunks = []
        
        for candidate in tqdm(resume_data, desc="Processing candidates"):
            candidate_id = candidate.get('candidate_id', 'unknown')
            name = candidate.get('name', 'Unknown')
            email = candidate.get('email', '')
            location = candidate.get('location', '')
            headline = candidate.get('headline', '')
            stage = candidate.get('stage', '')
            
            # Create candidate summary chunk
            candidate_summary = f"""
            Name: {name}
            Email: {email}
            Location: {location}
            Stage: {stage}
            Professional Summary: {headline}
            """.strip()
            
            chunks.append({
                'content': candidate_summary,
                'metadata': {
                    'chunk_type': 'candidate_summary',
                    'candidate_id': candidate_id,
                    'name': name,
                    'email': email,
                    'location': location,
                    'headline': headline,
                    'stage': stage
                }
            })
            
            # Process individual positions
            parsed_resume = candidate.get('parsed_resume', {})
            positions = parsed_resume.get('positions', [])
            
            for i, position in enumerate(positions):
                org = position.get('org', '')
                title = position.get('title', '')
                summary = position.get('summary', '')
                location_pos = position.get('location', '')
                start = position.get('start', {})
                end = position.get('end', {})
                
                # Format dates
                start_date = self.format_date(start)
                end_date = self.format_date(end) if end else "Present"
                
                position_text = f"""
                Candidate: {name}
                Company: {org}
                Title: {title}
                Duration: {start_date} - {end_date}
                Location: {location_pos}
                
                Experience Details:
                {summary}
                """.strip()
                
                chunks.append({
                    'content': position_text,
                    'metadata': {
                        'chunk_type': 'position',
                        'candidate_id': candidate_id,
                        'name': name,
                        'email': email,
                        'position_index': i,
                        'company': org,
                        'title': title,
                        'start_date': start_date,
                        'end_date': end_date,
                        'location': location_pos,
                        'summary': summary
                    }
                })
        
        return chunks

    def format_date(self, date_dict: Dict) -> str:
        """Format date dictionary to readable string."""
        if not date_dict:
            return ""
        
        year = date_dict.get('year', '')
        month = date_dict.get('month', '')
        
        if year and month:
            try:
                return f"{datetime(year, month, 1).strftime('%b %Y')}"
            except:
                return f"{month}/{year}"
        elif year:
            return str(year)
        else:
            return ""

    def load_data(self, resume_file_path: str):
        """Load resume data and create embeddings."""
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
        chunks = self.process_resume_data(resume_data)
        
        # Extract texts and metadata
        texts_to_embed = [chunk['content'] for chunk in chunks]
        metadata = [chunk['metadata'] for chunk in chunks]
        
        print(f"Created {len(texts_to_embed)} searchable chunks")
        
        # Create embeddings
        self._embed_and_store(texts_to_embed, metadata)
        self.save_db()
        
        print(f"Resume database loaded and saved. Total chunks processed: {len(texts_to_embed)}")

    def _embed_and_store(self, texts: List[str], data: List[Dict[str, Any]]):
        """Create embeddings for text chunks."""
        batch_size = 128
        with tqdm(total=len(texts), desc="Creating embeddings") as pbar:
            result = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                batch_result = self.client.embed(batch, model="voyage-2").embeddings
                result.extend(batch_result)
                pbar.update(len(batch))
        
        self.embeddings = result
        self.metadata = data

    def search(self, query: str, k: int = 20) -> List[Dict[str, Any]]:
        """Search for candidates matching the query."""
        if query in self.query_cache:
            query_embedding = self.query_cache[query]
        else:
            query_embedding = self.client.embed([query], model="voyage-2").embeddings[0]
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
                "content": self.get_content_from_metadata(self.metadata[idx])
            }
            top_results.append(result)
        
        return top_results

    def get_content_from_metadata(self, metadata: Dict[str, Any]) -> str:
        """Reconstruct content from metadata for display."""
        if metadata['chunk_type'] == 'candidate_summary':
            return f"""Name: {metadata['name']}
Email: {metadata['email']}
Location: {metadata['location']}
Stage: {metadata['stage']}
Professional Summary: {metadata['headline']}"""
        else:  # position
            return f"""Candidate: {metadata['name']}
Company: {metadata['company']}
Title: {metadata['title']}
Duration: {metadata['start_date']} - {metadata['end_date']}
Location: {metadata['location']}

Experience Details:
{metadata['summary']}"""

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

def create_resume_bm25_index(db: ResumeVectorDB):
    """Create and populate BM25 index from ResumeVectorDB."""
    es_bm25 = ResumeElasticsearchBM25()
    es_bm25.index_documents(db.metadata)
    return es_bm25

def retrieve_hybrid_resume(query: str, db: ResumeVectorDB, es_bm25: ResumeElasticsearchBM25, k: int, 
                          semantic_weight: float = 0.7, bm25_weight: float = 0.3):
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
    num_chunks_to_recall = min(100, len(db.metadata))  # Adjust based on resume data size

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

def format_resume_results(results: List[Dict[str, Any]], query: str, show_full_content: bool = False) -> None:
    """Format and display resume search results."""
    print(f"\n🔍 Resume Search: '{query}'")
    print(f"👥 Found {len(results)} matching candidates/positions:")
    print("=" * 80)
    
    for i, result in enumerate(results, 1):
        metadata = result['metadata']
        similarity = result['similarity']
        content = result['content']
        content_length = len(content)
        
        # Show either full content or preview
        if show_full_content or content_length <= 300:
            content_display = content
        else:
            content_display = content[:300] + "..."
        
        # Different display based on chunk type
        if metadata['chunk_type'] == 'candidate_summary':
            print(f"\n{i}. 👤 CANDIDATE PROFILE")
            print(f"   📧 {metadata['name']} ({metadata['email']})")
            print(f"   📍 {metadata['location']}")
            print(f"   🎯 Stage: {metadata['stage']}")
            print(f"   🔗 Similarity: {similarity:.4f}")
        else:  # position
            print(f"\n{i}. 💼 JOB EXPERIENCE")
            print(f"   👤 {metadata['name']} ({metadata['email']})")
            print(f"   🏢 {metadata['company']} - {metadata['title']}")
            print(f"   📅 {metadata['start_date']} - {metadata['end_date']}")
            print(f"   🔗 Similarity: {similarity:.4f}")
        
        print(f"   📏 Content Length: {content_length} characters")
        print(f"   📝 Details:")
        
        # Format content with proper wrapping
        import textwrap
        wrapped_content = textwrap.fill(content_display, width=76, initial_indent="      ", subsequent_indent="      ")
        print(wrapped_content)
        
        if not show_full_content and content_length > 300:
            print(f"      ... ({content_length - 300} more characters)")
        
        print("-" * 80)

def show_full_resume_result(results: List[Dict[str, Any]], result_number: int) -> None:
    """Show the full details of a specific resume result."""
    if 1 <= result_number <= len(results):
        result = results[result_number - 1]
        metadata = result['metadata']
        content = result['content']
        
        print(f"\n📖 Full Details for Result #{result_number}:")
        print("=" * 80)
        
        if metadata['chunk_type'] == 'candidate_summary':
            print(f"👤 CANDIDATE: {metadata['name']}")
            print(f"📧 Email: {metadata['email']}")
            print(f"📍 Location: {metadata['location']}")
            print(f"🎯 Stage: {metadata['stage']}")
            print(f"🔗 Similarity: {result['similarity']:.4f}")
            print(f"\n💼 Professional Summary:")
            print(f"{metadata['headline']}")
        else:
            print(f"💼 JOB EXPERIENCE")
            print(f"👤 Candidate: {metadata['name']} ({metadata['email']})")
            print(f"🏢 Company: {metadata['company']}")
            print(f"📋 Title: {metadata['title']}")
            print(f"📅 Duration: {metadata['start_date']} - {metadata['end_date']}")
            print(f"📍 Location: {metadata['location']}")
            print(f"🔗 Similarity: {result['similarity']:.4f}")
            print(f"\n📝 Experience Details:")
            print("-" * 40)
            import textwrap
            wrapped_summary = textwrap.fill(metadata['summary'], width=76)
            print(wrapped_summary)
        
        print("=" * 80)
    else:
        print(f"❌ Invalid result number. Please choose between 1 and {len(results)}.")

def interactive_resume_query_loop(db: ResumeVectorDB) -> None:
    """Main interactive resume query loop with hybrid search options."""
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
    search_mode = "semantic"  # Default search mode
    
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
            
            # Check for search mode and full content mode
            show_full = False
            search_mode = "semantic"  # Default
            
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
                k = 10  # Default to 10 for resumes
            
            # Validate inputs
            if not query:
                print("⚠️ Please enter a valid search query.")
                continue
                
            if k > 20:
                print("⚠️ Maximum 20 results allowed. Setting to 20.")
                k = 20
            elif k < 1:
                print("⚠️ Minimum 1 result required. Setting to 1.")
                k = 1
            
            # Perform search based on mode
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

def main():
    """Main function to initialize and run the resume search interface."""
    try:
        print("🚀 Initializing Resume Search System...")
        print("=" * 50)
        
        # Initialize ResumeVectorDB
        print("🗄️ Initializing Resume Database...")
        resume_db = ResumeVectorDB("resume_db")
        
        # Load and process resume data
        print("⚡ Loading and processing resume data...")
        resume_db.load_data('candidates_with_parsed_resumes.json')
        
        print(f"✅ Resume database ready with {len(resume_db.metadata)} searchable chunks!")
        
        # Start interactive query loop
        interactive_resume_query_loop(resume_db)
        
    except FileNotFoundError as e:
        print(f"❌ Error: Required resume file not found: {e}")
        print("💡 Make sure 'candidates_with_parsed_resumes.json' exists in your directory.")
    except Exception as e:
        print(f"❌ Error initializing system: {e}")
        print("💡 Check your API keys and resume data file.")

if __name__ == "__main__":
    main()