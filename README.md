# Enhancing RAG with Contextual Retrieval

A comprehensive implementation of Retrieval Augmented Generation (RAG) enhanced with Contextual Embeddings, achieving up to 35% reduction in retrieval failure rates.

## 🎯 Overview

This project demonstrates how to build and optimize a Contextual Retrieval system using multiple techniques:

- **Basic RAG**: Traditional document chunking and embedding
- **Contextual Embeddings**: Adding situational context to chunks before embedding
- **Contextual BM25**: Hybrid search combining semantic and keyword search
- **Reranking**: Final performance optimization using Cohere's reranking model

### Performance Improvements

| Method | Pass@5 | Pass@10 | Pass@20 |
|--------|--------|---------|---------|
| Basic RAG | 80.92% | 87.15% | 90.06% |
| Contextual Embeddings | 86.37% | 92.81% | 93.78% |
| Contextual BM25 | 86.43% | 93.21% | 94.99% |
| With Reranking | 91.24% | 94.79% | 96.30% |

## 🚀 Quick Start

### Prerequisites

1. **Python 3.8+**
2. **API Keys** for:
   - Anthropic (Claude)
   - Voyage AI (embeddings)
   - Cohere (reranking)
3. **Docker** (for Elasticsearch)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd lever-contextual-embeddings

# Install dependencies
pip install anthropic voyageai cohere elasticsearch pandas numpy matplotlib scikit-learn

# Set up Elasticsearch (for BM25 stage)
docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.8.0
```

### Environment Setup

Create a `.env` file or set environment variables:

```bash
export VOYAGE_API_KEY="your_voyage_api_key"
export ANTHROPIC_API_KEY="your_anthropic_api_key"
export COHERE_API_KEY="your_cohere_api_key"
```

### Running the Pipeline

```python
# 1. Basic RAG
from basic_rag import main as basic_main
basic_db, results5, results10, results20 = basic_main()

# 2. Contextual Embeddings
from contextual_embeddings import main as contextual_main
contextual_db, r5, r10, r20 = contextual_main()

# 3. Contextual BM25 (Hybrid Search)
from contextual_bm25 import main as bm25_main
hybrid_db, bm25_r5, bm25_r10, bm25_r20 = bm25_main()

# 4. Reranking
from reranking import main as rerank_main
rerank_db, rerank_r5, rerank_r10, rerank_r20 = rerank_main()
```

## 📁 Project Structure

```
lever-contextual-embeddings/
├── README.md                    # This file
├── setup.py                     # Setup and configuration
├── basic_rag.py                 # Stage 1: Basic RAG implementation
├── contextual_embeddings.py     # Stage 2: Contextual embeddings
├── contextual_bm25.py          # Stage 3: Hybrid search with BM25
├── reranking.py                # Stage 4: Reranking optimization
└── data/
    ├── codebase_chunks.json    # Chunked codebase dataset
    └── evaluation_set.jsonl     # Evaluation queries and ground truth
```

## 🏗️ Architecture

### Stage 1: Basic RAG (`basic_rag.py`)

Traditional "Naive RAG" approach:
- Document chunking by content sections
- Embedding with Voyage AI's `voyage-2` model
- Cosine similarity search

```python
from basic_rag import VectorDB

# Initialize and load data
db = VectorDB("my_db")
db.load_data(dataset)

# Search
results = db.search("your query", k=10)
```

### Stage 2: Contextual Embeddings (`contextual_embeddings.py`)

Enhanced embeddings with situational context:
- Uses Claude to generate context for each chunk
- Prompt caching for cost efficiency (90% discount on cached tokens)
- Improved chunk representation

```python
from contextual_embeddings import ContextualVectorDB

# Initialize with contextual enhancement
contextual_db = ContextualVectorDB("contextual_db")
contextual_db.load_data(dataset, parallel_threads=5)

# Search with better context
results = contextual_db.search("your query", k=10)
```

**Key Innovation**: Each chunk gets situational context:
```
Original Chunk: "def process_input(data)..."
+ Context: "This function is part of the data validation module that processes user input before database insertion."
```

### Stage 3: Contextual BM25 (`contextual_bm25.py`)

Hybrid search combining semantic and keyword search:
- Elasticsearch-based BM25 search
- Reciprocal Rank Fusion (RRF) for result combination
- Configurable weights for semantic vs. BM25 results

```python
from contextual_bm25 import evaluate_db_advanced

# Run hybrid search evaluation
results, source_breakdown = evaluate_db_advanced(contextual_db, 'data/evaluation_set.jsonl', 10)
```

### Stage 4: Reranking (`reranking.py`)

Final optimization using Cohere's reranking model:
- Retrieves 10x more candidates initially
- Uses Cohere's `rerank-english-v3.0` model
- Selects top-k most relevant results

```python
from reranking import RerankingPipeline

pipeline = RerankingPipeline()
results = pipeline.retrieve_and_rerank(query, contextual_db, k=10)
```

## 🔧 Configuration

### API Keys

Set these environment variables:

```bash
# Required for all stages
VOYAGE_API_KEY=your_voyage_api_key     # Embedding generation
ANTHROPIC_API_KEY=your_anthropic_key   # Context generation

# Required for reranking stage
COHERE_API_KEY=your_cohere_api_key     # Document reranking
```

### Performance Tuning

**Contextual Embeddings:**
- Adjust `parallel_threads` based on API rate limits
- Default: 5 threads, reduce if hitting rate limits

**BM25 Hybrid Search:**
- Tune `semantic_weight` and `bm25_weight` (default: 0.8, 0.2)
- Adjust `num_chunks_to_recall` for initial retrieval

**Reranking:**
- Modify `recall_multiplier` (default: 10x initial retrieval)
- Consider batch processing for large datasets

## 💰 Cost Considerations

### Prompt Caching Benefits

The contextual embeddings stage uses Anthropic's prompt caching:
- **77.04%** of input tokens read from cache (90% discount)
- Cost: ~$1.02 per million document tokens
- Cache TTL: 5 minutes

### Estimated Costs

For the provided 737-chunk dataset:
- **Basic RAG**: Embedding costs only (~$0.10)
- **Contextual Embeddings**: ~$2.50 (with caching)
- **BM25**: Infrastructure costs (Elasticsearch)
- **Reranking**: ~$0.50 per 1000 queries

## 📊 Evaluation Metrics

### Pass@k Metric

The system uses Pass@k to evaluate retrieval quality:
- **Pass@k**: Percentage of queries where the correct answer appears in the top k results
- **Golden Chunks**: Ground truth answers for each query
- **248 test queries** across 9 codebases

### Dataset

- **Source**: 9 codebases with 737 total chunks
- **Evaluation**: 248 queries with golden chunk annotations
- **File**: `data/evaluation_set.jsonl`

## 🐳 Docker Setup

### Elasticsearch (Required for BM25)

```bash
# Start Elasticsearch
docker run -d --name elasticsearch \
  -p 9200:9200 -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.8.0

# Verify it's running
curl http://localhost:9200
```

### Full Docker Compose (Optional)

```yaml
version: '3.8'
services:
  elasticsearch:
    image: elasticsearch:8.8.0
    ports:
      - "9200:9200"
      - "9300:9300"
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - es_data:/usr/share/elasticsearch/data

volumes:
  es_data:
```

## 🔍 Usage Examples

### Basic RAG Example

```python
from basic_rag import VectorDB, load_json

# Load data
dataset = load_json('data/codebase_chunks.json')

# Initialize database
db = VectorDB("example_db")
db.load_data(dataset)

# Search
query = "How to implement error handling?"
results = db.search(query, k=5)

for i, result in enumerate(results):
    print(f"{i+1}. Similarity: {result['similarity']:.3f}")
    print(f"   Content: {result['metadata']['content'][:100]}...")
```

### Contextual Embeddings Example

```python
from contextual_embeddings import ContextualVectorDB

# Initialize with context generation
db = ContextualVectorDB("contextual_example")
db.load_data(dataset, parallel_threads=3)  # Adjust threads as needed

# Search with enhanced context
results = db.search("error handling patterns", k=5)

for result in results:
    print(f"Original: {result['metadata']['original_content'][:50]}...")
    print(f"Context: {result['metadata']['contextualized_content']}")
    print("---")
```

### Hybrid Search Example

```python
from contextual_bm25 import retrieve_advanced, create_elasticsearch_bm25_index

# Setup
es_bm25 = create_elasticsearch_bm25_index(contextual_db)

# Hybrid search with custom weights
results, semantic_count, bm25_count = retrieve_advanced(
    query="async function implementation",
    db=contextual_db,
    es_bm25=es_bm25,
    k=10,
    semantic_weight=0.7,  # Favor semantic search
    bm25_weight=0.3       # Some keyword matching
)

print(f"Results: {len(results)}")
print(f"From semantic: {semantic_count}, From BM25: {bm25_count}")
```

### Reranking Example

```python
from reranking import RerankingPipeline

# Initialize reranking pipeline
pipeline = RerankingPipeline()

# Retrieve and rerank
query = "database connection pooling"
results = pipeline.retrieve_and_rerank(
    query=query,
    db=contextual_db,
    k=5,
    recall_multiplier=20  # Retrieve 100 candidates, rerank to top 5
)

for i, result in enumerate(results):
    print(f"{i+1}. Relevance: {result['score']:.3f}")
    print(f"   {result['chunk']['original_content'][:80]}...")
```

## 🚨 Troubleshooting

### Common Issues

**1. API Rate Limits**
```python
# Reduce parallel threads
contextual_db.load_data(dataset, parallel_threads=1)

# Add delays in reranking
import time
time.sleep(0.2)  # Increase delay between requests
```

**2. Elasticsearch Connection Issues**
```bash
# Check if Elasticsearch is running
curl http://localhost:9200

# Restart if needed
docker restart elasticsearch

# Check logs
docker logs elasticsearch
```

**3. Memory Issues**
```python
# Process smaller batches
batch_size = 64  # Reduce from default 128
```

**4. Missing API Keys**
```python
import os
print(os.getenv("VOYAGE_API_KEY"))  # Should not be None
print(os.getenv("ANTHROPIC_API_KEY"))
print(os.getenv("COHERE_API_KEY"))
```

### Performance Troubleshooting

**Slow Context Generation:**
- Reduce `parallel_threads`
- Check network latency to Anthropic API
- Monitor prompt caching effectiveness

**Poor Retrieval Results:**
- Verify data quality in `codebase_chunks.json`
- Check embedding model compatibility
- Validate evaluation queries

## 🏗️ Production Deployment

### AWS Bedrock Integration

The project includes AWS Lambda function code for Bedrock Knowledge Bases:
- See `contextual-rag-lambda-function/lambda_function.py`
- Deploy as custom chunking option in Bedrock
- Contact AWS team for implementation guidance

### GCP Vertex AI Integration

- Adapt the contextual embeddings approach for Vertex AI
- Use Cloud Run for serverless deployment
- Contact GCP account team for specific implementation

### Scalability Considerations

1. **Database**: Replace in-memory vector DB with production solutions:
   - Pinecone
   - Weaviate
   - Qdrant
   - PostgreSQL with pgvector

2. **Caching**: Implement persistent caching:
   - Redis for query caching
   - File-based caching for embeddings

3. **API Management**: 
   - Implement proper rate limiting
   - Add retry logic with exponential backoff
   - Monitor API usage and costs

## 📈 Next Steps

### Potential Improvements

1. **Advanced Chunking**: Implement semantic chunking strategies
2. **Multi-Modal**: Add support for images and code snippets
3. **Real-time Updates**: Implement incremental index updates
4. **A/B Testing**: Framework for testing different configurations
5. **Monitoring**: Add comprehensive logging and metrics

### Research Directions

1. **Dynamic Context**: Adapt context generation based on query type
2. **Hierarchical Retrieval**: Multi-level document retrieval
3. **Cross-Lingual**: Support for multiple programming languages
4. **Personalization**: User-specific retrieval optimization

## 📜 License

[Add your license here]

## 🤝 Contributing

[Add contribution guidelines here]

## 📚 References

- [Anthropic's Contextual Retrieval Blog Post](https://example.com)
- [Voyage AI Documentation](https://docs.voyageai.com)
- [Cohere Reranking Documentation](https://docs.cohere.ai)
- [Elasticsearch BM25 Guide](https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules-similarity.html)

## 📞 Support

For questions and support:
- Open an issue in the repository
- Contact your AWS/GCP account team for cloud deployment
- Reach out to Anthropic for enterprise support

---

**Note**: This implementation is for educational and research purposes. For production use, consider additional security, monitoring, and scalability measures.# lever-contextual-embeddings
