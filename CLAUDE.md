# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Resume Query RAG System

## Project Overview
AI-powered resume search platform combining semantic understanding with traditional keyword search for recruiting. Originally built as a Contextual Retrieval demonstration, evolved into a production-ready resume search system processing 10,000+ candidate profiles with intelligent search capabilities.

## Core Architecture

### Multi-Modal Search System
- **Semantic Search**: Voyage AI `voyage-2` embeddings with cosine similarity
- **BM25/Keyword Search**: Elasticsearch-based traditional search
- **Hybrid Search**: Combines semantic (70%) + BM25 (30%) with Reciprocal Rank Fusion
- **Weighted Search**: Multi-criteria search with customizable importance weights and threshold filtering
- **Reranking**: Cohere `rerank-v3.5` (latest) for result quality enhancement

### Data Processing Pipeline
**Three-Chunk Strategy**: Each candidate creates multiple searchable chunks for targeted retrieval:
1. **Candidate Summary Chunk**: `Location: {location}` (for geographic search)
2. **Position Chunks**: One per job experience with company, title, job description
3. **Education Chunks**: One per school with institution name and degree

**Content Optimization Philosophy**: 
- ✅ Include: Location, company, title, job descriptions, schools, degrees
- ❌ Exclude: Name, email, stage, headline (noise reduction for better search relevance)

## Key Components

### Backend (`app.py`)
Flask web application serving as the main interface:
- `/api/search` - Multi-modal search endpoint supporting all search modes
- `/api/databases` - List available vector databases 
- `/api/switch-database` - Dynamic database switching
- `/api/candidate/<id>` - Detailed candidate information with social links
- Database auto-initialization with fallback handling
- Weighted search with multi-criteria scoring and threshold filtering

### Resume Query Package (`resume_query/`)
- `database.py` - Vector database with Voyage AI embeddings and query caching
- `search.py` - BM25 and hybrid search implementations using Elasticsearch
- `data_processing.py` - Resume chunking with three-chunk strategy
- `reranking.py` - Cohere reranking with model selection
- `config.py` - Centralized configuration and environment management
- `education_database.py` - Specialized education-only search database

### Frontend (`templates/`, `static/`)
Modern web interface with dynamic search modes:
- **Four Search Modes**: Semantic, Hybrid, Keyword, Weighted
- **Database Selection**: Dropdown to switch between available databases
- **Weighted Search UI**: Multi-criteria inputs with weight sliders and threshold control
- **Result Display**: Candidate profiles with expandable job/education details
- **Social Integration**: Automatic Lever profile links and enhanced social links

## Development Commands

```bash
# Start web application (main interface)
python app.py

# Debug data processing and chunking
python view_chunks.py
python view_raw_chunk.py

# Test education-specific databases
python test_education_db.py [custom_file.json]
python education_example.py

# Enhance candidates with social links (Lever API integration)
python enhance_candidates_with_links.py --file candidates_with_parsed_resumes.json --test
python enhance_candidates_with_links.py --file candidates_with_parsed_resumes.json

# Force rebuild vector embeddings (after data processing changes)
rm -rf ./data/resume_db_*/
rm -rf ./data/education_*/

# Wait for file completion then auto-run pipeline
python wait_and_run.py
```

## Configuration and Environment

### Required Environment Variables (.env)
```bash
VOYAGE_API_KEY=your_voyage_api_key    # Embeddings only
COHERE_API_KEY=your_cohere_api_key    # Reranking
LEVER_API_KEY=your_lever_api_key      # Social link enhancement (optional)
```

### Key Configuration (`resume_query/config.py`)
- `DEFAULT_RESUME_FILE`: Primary data source (currently `10000_candidates_with_parsed_resumes.json`)
- `EMBEDDING_MODEL`: Voyage AI model (`voyage-2`)
- `DEFAULT_SEMANTIC_WEIGHT`/`DEFAULT_BM25_WEIGHT`: Hybrid search balance (0.7/0.3)
- `RERANK_MODEL`: Cohere reranking model (`rerank-v3.5` latest, `rerank-english-v3.0`, `rerank-multilingual-v3.0`, `rerank-english-v2.0`)

## Data Architecture

### File Structure
- `candidates_with_parsed_resumes.json` - Standard 1K candidate dataset
- `10000_candidates_with_parsed_resumes.json` - Large dataset
- `./data/resume_db_*/vector_db.pkl` - Cached embeddings (auto-generated)
- `./data/education_*/vector_db.pkl` - Education-specific databases
- `enhance_candidates.log` - Link enhancement progress

### Database Auto-Discovery
The system automatically scans `./data/` for vector databases and presents them in a dropdown. Database names are generated from JSON filenames using `get_db_name_from_file()`.

## Search Mode Implementation Details

### Weighted Search Architecture
Advanced multi-criteria search with customizable importance:
- **Four Criteria**: Skills/Technologies, Experience Level, Company Background, Education
- **Weighted Scoring**: `Total = (Skills×W1) + (Experience×W2) + (Company×W3) + (Education×W4)`
- **Threshold Filtering**: Configurable minimum match score
- **Backend Logic**: Uses existing semantic search infrastructure with score aggregation
- **No Reranking**: Weighted search bypasses reranking since it already provides sophisticated scoring

### Hybrid Search Flow
1. Parallel execution of semantic and BM25 searches
2. Reciprocal Rank Fusion for result combination
3. Configurable weight balancing
4. Optional reranking as final step

## Performance Characteristics

### Embedding Creation
- ~17 minutes for 10,000 candidates (batch processing)
- Persistent caching in `./data/resume_db_*/vector_db.pkl`
- Query embedding cache for improved search speed

### Search Performance
- Real-time semantic search (~200-500ms)
- Hybrid search with reranking: ~1-2 seconds
- Weighted search: ~2-3 seconds (multiple semantic queries)

### API Rate Limiting
- Lever API: 10 requests/second (vs originally assumed 100 req/min)
- Voyage AI: Batch processing with `DEFAULT_BATCH_SIZE = 128`
- Cohere: Standard reranking rate limits

## Development Workflow

1. **Data Processing Changes**: Delete vector DB cache → Restart app (auto-rebuilds embeddings)
2. **Testing Strategy**: Use `--test` flag for small datasets, then scale
3. **Debugging Tools**: `view_chunks.py` to inspect chunk processing
4. **Database Switching**: Use web interface dropdown to test different datasets
5. **Weighted Search Testing**: Adjust criteria weights/thresholds via web UI

## Troubleshooting

### Common Issues
- **Import errors**: Verify `VOYAGE_API_KEY` and `COHERE_API_KEY` in config.py and environment
- **Database initialization failures**: Check JSON file format and accessibility
- **Search timeouts**: Reduce result limits or check Elasticsearch status
- **Weighted search 500 errors**: Ensure numpy float conversion in result formatting
- **Missing education data**: Switch to education-specific database or verify data structure

### Performance Issues
- **Slow embedding creation**: Check Voyage AI API connectivity and rate limits
- **Reranking failures**: Verify Cohere API key and connectivity
- **Poor search results**: Rebuild vector DB after data processing modifications
- **Elasticsearch errors**: Hybrid/BM25 search automatically falls back to semantic-only

## Important Design Decisions

### Content Processing
- **Removed** name/email/stage from searchable content (noise reduction)
- **Preserved** location and duration (professionally relevant)
- **Three-chunk strategy** optimizes for different search patterns

### Search Implementation
- **Weighted search replaces reranking** for multi-criteria queries
- **Database switching** allows A/B testing different datasets
- **Fallback mechanisms** ensure system reliability (BM25→semantic, failed DB→default)

### Frontend Architecture
- **Dynamic UI** adapts to selected search mode
- **Progressive enhancement** from basic to weighted search
- **Real-time feedback** with similarity/weighted scores