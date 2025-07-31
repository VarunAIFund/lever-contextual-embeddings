# Resume Query RAG System

## Project Overview
AI-powered resume search platform combining semantic understanding with traditional keyword search for recruiting. Processes 10,000+ candidate profiles with intelligent search capabilities.

## Architecture
- **Backend**: Flask web application with REST API
- **Search**: Hybrid system with semantic (Voyage AI), BM25 (Elasticsearch), and reranking
- **Frontend**: Modern web interface with real-time search
- **Data**: JSON resume files enhanced with LinkedIn/social links via Lever API

## Key Components
- `app.py` - Flask web server and API endpoints
- `resume_query/` - Modular search system package
  - `database.py` - Vector database with Voyage AI embeddings
  - `search.py` - BM25 and hybrid search implementations
  - `data_processing.py` - Resume chunking and content optimization
  - `reranking.py` - Voyage AI reranking for result quality
  - `interactive.py` - CLI interface (legacy)
- `enhance_candidates_with_links.py` - Lever API integration for social links
- `wait_and_run.py` - Automated pipeline runner

## Data Processing Strategy
**Chunking Approach**: Each candidate creates multiple searchable chunks
1. **Candidate Summary Chunk**: Location-based (geographic search)
2. **Position Chunks**: One per job experience (company, title, dates, description)

**Content Optimization**: 
- ✅ Include: Location, company, title, duration, job descriptions
- ❌ Exclude: Name, email, stage, headline (noise removal for better search)

## API Configuration
- **Voyage AI**: `voyage-2` for embeddings, `rerank-lite-1`/`rerank-1` for reranking
- **Lever API**: 10 requests/second rate limit for link enhancement
- **Elasticsearch**: BM25 search with field boosting (content^2, name^1.5, etc.)

## Common Commands
```bash
# Run web application
python app.py

# View processed chunks (debugging)
python view_chunks.py
python view_raw_chunk.py

# Enhance with social links
python enhance_candidates_with_links.py --file candidates_with_parsed_resumes.json --test
python enhance_candidates_with_links.py --file candidates_with_parsed_resumes.json

# Wait for file completion then auto-run
python wait_and_run.py

# Force rebuild embeddings (after data processing changes)
rm -rf ./data/resume_db_*/
```

## Environment Variables (.env)
```
VOYAGE_API_KEY=your_voyage_api_key
LEVER_API_KEY=your_lever_api_key
```

## File Structure
- `candidates_with_parsed_resumes.json` - Original resume data
- `10000_candidates_with_parsed_resumes.json` - Larger dataset
- `./data/resume_db_*/vector_db.pkl` - Cached embeddings (delete to rebuild)
- `enhance_candidates.log` - Link enhancement progress logs

## Web Interface Features
- **Search Modes**: Semantic, BM25, Hybrid
- **Reranking Toggle**: Choose between rerank-lite-1 (fast) vs rerank-1 (quality)
- **Result Display**: Candidate profiles + job experiences with expandable details
- **Social Links**: LinkedIn, GitHub, portfolio links in candidate modals

## Performance Notes
- **Embedding Creation**: ~17 minutes for 10,000 candidates
- **Link Enhancement**: ~17 minutes for 10,000 candidates (10 req/sec)
- **Search Speed**: Real-time with reranking in ~1-2 seconds
- **Cache Strategy**: Persistent vector storage, query embedding cache

## Development Workflow
1. Modify data processing → Delete vector DB cache → Rebuild embeddings
2. Test with small datasets first (`--test` flag)
3. Use `view_chunks.py` to verify content processing
4. Web interface at `http://localhost:5000`

## Important Decisions Made
- Removed name/email/stage from searchable content (noise reduction)
- Kept duration field (professionally relevant for experience level)
- Two-chunk strategy: candidate summary + individual positions
- Hybrid search weights: 70% semantic, 30% BM25
- Rate limiting: 10 req/sec for Lever API vs 100 req/min originally assumed

## Troubleshooting
- **Import errors**: Check VOYAGE_API_KEY in config.py
- **Poor search results**: Rebuild vector DB after data processing changes  
- **Slow enhancement**: Lever API rate limits, use --start-from to resume
- **Elasticsearch errors**: Hybrid/BM25 search falls back to semantic only