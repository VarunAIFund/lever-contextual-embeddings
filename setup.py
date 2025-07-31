'''
SETUP
'''

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import anthropic

client = anthropic.Anthropic(
    # This is the default and can be omitted
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)

import os
import pickle
import json
import numpy as np
import voyageai
from typing import List, Dict, Any
from tqdm import tqdm

class VectorDB:
    def __init__(self, name: str, api_key = None):
        if api_key is None:
            api_key = os.getenv("VOYAGE_API_KEY")
        self.client = voyageai.Client(api_key=api_key)
        self.name = name
        self.embeddings = []
        self.metadata = []
        self.query_cache = {}
        self.db_path = f"./data/{name}/vector_db.pkl"

    def load_data(self, dataset: List[Dict[str, Any]]):
        if self.embeddings and self.metadata:
            print("Vector database is already loaded. Skipping data loading.")
            return
        if os.path.exists(self.db_path):
            print("Loading vector database from disk.")
            self.load_db()
            return

        texts_to_embed = []
        metadata = []
        total_chunks = sum(len(doc['chunks']) for doc in dataset)
        
        with tqdm(total=total_chunks, desc="Processing chunks") as pbar:
            for doc in dataset:
                for chunk in doc['chunks']:
                    texts_to_embed.append(chunk['content'])
                    metadata.append({
                        'doc_id': doc['doc_id'],
                        'original_uuid': doc['original_uuid'],
                        'chunk_id': chunk['chunk_id'],
                        'original_index': chunk['original_index'],
                        'content': chunk['content']
                    })
                    pbar.update(1)

        self._embed_and_store(texts_to_embed, metadata)
        self.save_db()
        
        print(f"Vector database loaded and saved. Total chunks processed: {len(texts_to_embed)}")

    def _embed_and_store(self, texts: List[str], data: List[Dict[str, Any]]):
        batch_size = 128
        with tqdm(total=len(texts), desc="Embedding chunks") as pbar:
            result = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                batch_result = self.client.embed(batch, model="voyage-2").embeddings
                result.extend(batch_result)
                pbar.update(len(batch))
        
        self.embeddings = result
        self.metadata = data

    def search(self, query: str, k: int = 20) -> List[Dict[str, Any]]:
        if query in self.query_cache:
            query_embedding = self.query_cache[query]
        else:
            query_embedding = self.client.embed([query], model="voyage-2").embeddings[0]
            self.query_cache[query] = query_embedding

        if not self.embeddings:
            raise ValueError("No data loaded in the vector database.")

        similarities = np.dot(self.embeddings, query_embedding)
        top_indices = np.argsort(similarities)[::-1][:k]
        
        top_results = []
        for idx in top_indices:
            result = {
                "metadata": self.metadata[idx],
                "similarity": float(similarities[idx]),
            }
            top_results.append(result)
        
        return top_results

    def save_db(self):
        data = {
            "embeddings": self.embeddings,
            "metadata": self.metadata,
            "query_cache": json.dumps(self.query_cache),
        }
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, "wb") as file:
            pickle.dump(data, file)

    def load_db(self):
        if not os.path.exists(self.db_path):
            raise ValueError("Vector database file not found. Use load_data to create a new database.")
        with open(self.db_path, "rb") as file:
            data = pickle.load(file)
        self.embeddings = data["embeddings"]
        self.metadata = data["metadata"]
        self.query_cache = json.loads(data["query_cache"])

    def validate_embedded_chunks(self):
        unique_contents = set()
        for meta in self.metadata:
            unique_contents.add(meta['content'])
    
        print(f"Validation results:")
        print(f"Total embedded chunks: {len(self.metadata)}")
        print(f"Unique embedded contents: {len(unique_contents)}")
    
        if len(self.metadata) != len(unique_contents):
            print("Warning: There may be duplicate chunks in the embedded data.")
        else:
            print("All embedded chunks are unique.")

# Load your transformed dataset
with open('data/codebase_chunks.json', 'r') as f:
    transformed_dataset = json.load(f)

# Initialize the VectorDB
base_db = VectorDB("base_db")

# Load and process the data
base_db.load_data(transformed_dataset)




'''
Basic RAG
'''

import json
from typing import List, Dict, Any, Callable, Union
from tqdm import tqdm

def load_jsonl(file_path: str) -> List[Dict[str, Any]]:
    """Load JSONL file and return a list of dictionaries."""
    with open(file_path, 'r') as file:
        return [json.loads(line) for line in file]

def evaluate_retrieval(queries: List[Dict[str, Any]], retrieval_function: Callable, db, k: int = 20) -> Dict[str, float]:
    total_score = 0
    total_queries = len(queries)
    
    for query_item in tqdm(queries, desc="Evaluating retrieval"):
        query = query_item['query']
        golden_chunk_uuids = query_item['golden_chunk_uuids']
        
        # Find all golden chunk contents
        golden_contents = []
        for doc_uuid, chunk_index in golden_chunk_uuids:
            golden_doc = next((doc for doc in query_item['golden_documents'] if doc['uuid'] == doc_uuid), None)
            if not golden_doc:
                print(f"Warning: Golden document not found for UUID {doc_uuid}")
                continue
            
            golden_chunk = next((chunk for chunk in golden_doc['chunks'] if chunk['index'] == chunk_index), None)
            if not golden_chunk:
                print(f"Warning: Golden chunk not found for index {chunk_index} in document {doc_uuid}")
                continue
            
            golden_contents.append(golden_chunk['content'].strip())
        
        if not golden_contents:
            print(f"Warning: No golden contents found for query: {query}")
            continue
        
        retrieved_docs = retrieval_function(query, db, k=k)
        
        # Count how many golden chunks are in the top k retrieved documents
        chunks_found = 0
        for golden_content in golden_contents:
            for doc in retrieved_docs[:k]:
                retrieved_content = doc['metadata'].get('original_content', doc['metadata'].get('content', '')).strip()
                if retrieved_content == golden_content:
                    chunks_found += 1
                    break
        
        query_score = chunks_found / len(golden_contents)
        total_score += query_score
    
    average_score = total_score / total_queries
    pass_at_n = average_score * 100
    return {
        "pass_at_n": pass_at_n,
        "average_score": average_score,
        "total_queries": total_queries
    }

def retrieve_base(query: str, db, k: int = 20) -> List[Dict[str, Any]]:
    """
    Retrieve relevant documents using either VectorDB or ContextualVectorDB.
    
    :param query: The query string
    :param db: The VectorDB or ContextualVectorDB instance
    :param k: Number of top results to retrieve
    :return: List of retrieved documents
    """
    return db.search(query, k=k)

def evaluate_db(db, original_jsonl_path: str, k):
    # Load the original JSONL data for queries and ground truth
    original_data = load_jsonl(original_jsonl_path)
    
    # Evaluate retrieval
    results = evaluate_retrieval(original_data, retrieve_base, db, k)
    print(f"Pass@{k}: {results['pass_at_n']:.2f}%")
    print(f"Total Score: {results['average_score']}")
    print(f"Total queries: {results['total_queries']}")

results5 = evaluate_db(base_db, 'data/evaluation_set.jsonl', 5)
results10 = evaluate_db(base_db, 'data/evaluation_set.jsonl', 10)
results20 = evaluate_db(base_db, 'data/evaluation_set.jsonl', 20)


DOCUMENT_CONTEXT_PROMPT = """
<document>
{doc_content}
</document>
"""

CHUNK_CONTEXT_PROMPT = """
Here is the chunk we want to situate within the whole document
<chunk>
{chunk_content}
</chunk>

Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk.
Answer only with the succinct context and nothing else.
"""

def situate_context(doc: str, chunk: str) -> str:
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1024,
        temperature=0.0,
        messages=[
            {
                "role": "user", 
                "content": [
                    {
                        "type": "text",
                        "text": DOCUMENT_CONTEXT_PROMPT.format(doc_content=doc),
                        "cache_control": {"type": "ephemeral"}
                    },
                    {
                        "type": "text",
                        "text": CHUNK_CONTEXT_PROMPT.format(chunk_content=chunk),
                    }
                ]
            }
        ],
        extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
    )
    return response


jsonl_data = load_jsonl('data/evaluation_set.jsonl')
# Example usage
doc_content = jsonl_data[0]['golden_documents'][0]['content']
chunk_content = jsonl_data[0]['golden_chunks'][0]['content']

response = situate_context(doc_content, chunk_content)
print(f"Situated context: {response.content[0].text}")

# Print cache performance metrics
print(f"Input tokens: {response.usage.input_tokens}")
print(f"Output tokens: {response.usage.output_tokens}")
print(f"Cache creation input tokens: {response.usage.cache_creation_input_tokens}")
print(f"Cache read input tokens: {response.usage.cache_read_input_tokens}")

import os
import pickle
import json
import numpy as np
import voyageai
from typing import List, Dict, Any
from tqdm import tqdm
import anthropic
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class ContextualVectorDB:
    def __init__(self, name: str, voyage_api_key=None, anthropic_api_key=None):
        if voyage_api_key is None:
            voyage_api_key = os.getenv("VOYAGE_API_KEY")
        if anthropic_api_key is None:
            anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        self.voyage_client = voyageai.Client(api_key=voyage_api_key)
        self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.name = name
        self.embeddings = []
        self.metadata = []
        self.query_cache = {}
        self.db_path = f"./data/{name}/contextual_vector_db.pkl"

        self.token_counts = {
            'input': 0,
            'output': 0,
            'cache_read': 0,
            'cache_creation': 0
        }
        self.token_lock = threading.Lock()

    def situate_context(self, doc: str, chunk: str) -> tuple[str, Any]:
        DOCUMENT_CONTEXT_PROMPT = """
        <document>
        {doc_content}
        </document>
        """

        CHUNK_CONTEXT_PROMPT = """
        Here is the chunk we want to situate within the whole document
        <chunk>
        {chunk_content}
        </chunk>

        Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk.
        Answer only with the succinct context and nothing else.
        """

        response = self.anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            temperature=0.0,
            messages=[
                {
                    "role": "user", 
                    "content": [
                        {
                            "type": "text",
                            "text": DOCUMENT_CONTEXT_PROMPT.format(doc_content=doc),
                            "cache_control": {"type": "ephemeral"} #we will make use of prompt caching for the full documents
                        },
                        {
                            "type": "text",
                            "text": CHUNK_CONTEXT_PROMPT.format(chunk_content=chunk),
                        },
                    ]
                },
            ],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )
        return response.content[0].text, response.usage

    def load_data(self, dataset: List[Dict[str, Any]], parallel_threads: int = 1):
        if self.embeddings and self.metadata:
            print("Vector database is already loaded. Skipping data loading.")
            return
        if os.path.exists(self.db_path):
            print("Loading vector database from disk.")
            self.load_db()
            return

        texts_to_embed = []
        metadata = []
        total_chunks = sum(len(doc['chunks']) for doc in dataset)

        def process_chunk(doc, chunk):
            #for each chunk, produce the context
            contextualized_text, usage = self.situate_context(doc['content'], chunk['content'])
            with self.token_lock:
                self.token_counts['input'] += usage.input_tokens
                self.token_counts['output'] += usage.output_tokens
                self.token_counts['cache_read'] += usage.cache_read_input_tokens
                self.token_counts['cache_creation'] += usage.cache_creation_input_tokens
            
            return {
                #append the context to the original text chunk
                'text_to_embed': f"{chunk['content']}\n\n{contextualized_text}",
                'metadata': {
                    'doc_id': doc['doc_id'],
                    'original_uuid': doc['original_uuid'],
                    'chunk_id': chunk['chunk_id'],
                    'original_index': chunk['original_index'],
                    'original_content': chunk['content'],
                    'contextualized_content': contextualized_text
                }
            }

        print(f"Processing {total_chunks} chunks with {parallel_threads} threads")
        with ThreadPoolExecutor(max_workers=parallel_threads) as executor:
            futures = []
            for doc in dataset:
                for chunk in doc['chunks']:
                    futures.append(executor.submit(process_chunk, doc, chunk))
            
            for future in tqdm(as_completed(futures), total=total_chunks, desc="Processing chunks"):
                result = future.result()
                texts_to_embed.append(result['text_to_embed'])
                metadata.append(result['metadata'])

        self._embed_and_store(texts_to_embed, metadata)
        self.save_db()

        #logging token usage
        print(f"Contextual Vector database loaded and saved. Total chunks processed: {len(texts_to_embed)}")
        print(f"Total input tokens without caching: {self.token_counts['input']}")
        print(f"Total output tokens: {self.token_counts['output']}")
        print(f"Total input tokens written to cache: {self.token_counts['cache_creation']}")
        print(f"Total input tokens read from cache: {self.token_counts['cache_read']}")
        
        total_tokens = self.token_counts['input'] + self.token_counts['cache_read'] + self.token_counts['cache_creation']
        savings_percentage = (self.token_counts['cache_read'] / total_tokens) * 100 if total_tokens > 0 else 0
        print(f"Total input token savings from prompt caching: {savings_percentage:.2f}% of all input tokens used were read from cache.")
        print("Tokens read from cache come at a 90 percent discount!")

    #we use voyage AI here for embeddings. Read more here: https://docs.voyageai.com/docs/embeddings
    def _embed_and_store(self, texts: List[str], data: List[Dict[str, Any]]):
        batch_size = 128
        result = [
            self.voyage_client.embed(
                texts[i : i + batch_size],
                model="voyage-2"
            ).embeddings
            for i in range(0, len(texts), batch_size)
        ]
        self.embeddings = [embedding for batch in result for embedding in batch]
        self.metadata = data

    def search(self, query: str, k: int = 20) -> List[Dict[str, Any]]:
        if query in self.query_cache:
            query_embedding = self.query_cache[query]
        else:
            query_embedding = self.voyage_client.embed([query], model="voyage-2").embeddings[0]
            self.query_cache[query] = query_embedding

        if not self.embeddings:
            raise ValueError("No data loaded in the vector database.")

        similarities = np.dot(self.embeddings, query_embedding)
        top_indices = np.argsort(similarities)[::-1][:k]
        
        top_results = []
        for idx in top_indices:
            result = {
                "metadata": self.metadata[idx],
                "similarity": float(similarities[idx]),
            }
            top_results.append(result)
        return top_results

    def save_db(self):
        data = {
            "embeddings": self.embeddings,
            "metadata": self.metadata,
            "query_cache": json.dumps(self.query_cache),
        }
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with open(self.db_path, "wb") as file:
            pickle.dump(data, file)

    def load_db(self):
        if not os.path.exists(self.db_path):
            raise ValueError("Vector database file not found. Use load_data to create a new database.")
        with open(self.db_path, "rb") as file:
            data = pickle.load(file)
        self.embeddings = data["embeddings"]
        self.metadata = data["metadata"]
        self.query_cache = json.loads(data["query_cache"])


# Load the transformed dataset
with open('data/codebase_chunks.json', 'r') as f:
    transformed_dataset = json.load(f)

# Initialize the ContextualVectorDB
contextual_db = ContextualVectorDB("my_contextual_db")

# Load and process the data
#note: consider increasing the number of parallel threads to run this faster, or reducing the number of parallel threads if concerned about hitting your API rate limit
contextual_db.load_data(transformed_dataset, parallel_threads=1)


r5 = evaluate_db(contextual_db, 'data/evaluation_set.jsonl', 5)
r10 = evaluate_db(contextual_db, 'data/evaluation_set.jsonl', 10)
r20 = evaluate_db(contextual_db, 'data/evaluation_set.jsonl', 20)




