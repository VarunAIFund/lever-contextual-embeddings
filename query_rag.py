#!/usr/bin/env python3
"""
Interactive RAG Query Interface

This script provides an interactive command-line interface to query the RAG system
built in setup.py. It reuses the same VectorDB and data loading logic.
"""

# Import all the setup from setup.py
import os
import pickle  
import json
import numpy as np
import voyageai
from typing import List, Dict, Any
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# VectorDB class (same as setup.py)
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

def format_results(results: List[Dict[str, Any]], query: str, show_full_content: bool = False) -> None:
    """Format and display search results in a user-friendly way."""
    print(f"\n🔍 Query: '{query}'")
    print(f"📊 Found {len(results)} results:")
    print("=" * 80)
    
    for i, result in enumerate(results, 1):
        metadata = result['metadata']
        similarity = result['similarity']
        content = metadata['content']
        content_length = len(content)
        
        # Show either full content or preview
        if show_full_content or content_length <= 200:
            content_display = content
        else:
            content_display = content[:200] + "..."
        
        print(f"\n{i}. 📄 Document: {metadata['doc_id']}")
        print(f"   🎯 Similarity: {similarity:.4f}")
        print(f"   🆔 Chunk ID: {metadata['chunk_id']}")
        print(f"   📏 Content Length: {content_length} characters")
        print(f"   📝 Content:")
        
        # Format content with proper wrapping
        import textwrap
        wrapped_content = textwrap.fill(content_display, width=76, initial_indent="      ", subsequent_indent="      ")
        print(wrapped_content)
        
        if not show_full_content and content_length > 200:
            print(f"      ... ({content_length - 200} more characters)")
        
        print("-" * 80)

def show_full_result(results: List[Dict[str, Any]], result_number: int) -> None:
    """Show the full content of a specific result."""
    if 1 <= result_number <= len(results):
        result = results[result_number - 1]
        metadata = result['metadata']
        content = metadata['content']
        
        print(f"\n📖 Full Content for Result #{result_number}:")
        print("=" * 80)
        print(f"📄 Document: {metadata['doc_id']}")
        print(f"🆔 Chunk ID: {metadata['chunk_id']}")
        print(f"🎯 Similarity: {result['similarity']:.4f}")
        print(f"📏 Length: {len(content)} characters")
        print("\n📝 Full Content:")
        print("-" * 80)
        
        # Format with proper wrapping
        import textwrap
        wrapped_content = textwrap.fill(content, width=76)
        print(wrapped_content)
        print("-" * 80)
    else:
        print(f"❌ Invalid result number. Please choose between 1 and {len(results)}.")

def interactive_query_loop(db: VectorDB) -> None:
    """Main interactive query loop."""
    print("\n🚀 RAG Query Interface Ready!")
    print("💡 Tips:")
    print("   - Type your question and press Enter")
    print("   - Type 'quit', 'exit', or 'q' to exit")
    print("   - Add ':N' after your query to get N results (e.g., 'your query:10')")
    print("   - Add 'full:' before your query to see full content (e.g., 'full:your query')")
    print("   - Type a number (1-N) to see full content of that result")
    print("   - Default is 5 results with content preview")
    
    current_results = []
    last_query = ""
    
    while True:
        try:
            # Get user input
            user_input = input("\n❓ Enter your query (or result number for full content): ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'q', '']:
                print("👋 Goodbye!")
                break
            
            # Check if user wants to see full content of a specific result
            if user_input.isdigit() and current_results:
                result_num = int(user_input)
                show_full_result(current_results, result_num)
                continue
            
            # Check for full content mode
            show_full = False
            if user_input.lower().startswith('full:'):
                show_full = True
                user_input = user_input[5:].strip()
            
            # Parse query and optional result count
            if ':' in user_input and user_input.split(':')[-1].isdigit():
                query, k_str = user_input.rsplit(':', 1)
                k = int(k_str)
                query = query.strip()
            else:
                query = user_input
                k = 5
            
            # Validate inputs
            if not query:
                print("⚠️ Please enter a valid query.")
                continue
                
            if k > 20:
                print("⚠️ Maximum 20 results allowed. Setting to 20.")
                k = 20
            elif k < 1:
                print("⚠️ Minimum 1 result required. Setting to 1.")
                k = 1
            
            # Perform search
            print(f"🔎 Searching for '{query}' (top {k} results)...")
            if show_full:
                print("📖 Showing full content for all results...")
            
            results = db.search(query, k=k)
            current_results = results
            last_query = query
            
            # Display results
            if results:
                format_results(results, query, show_full_content=show_full)
                if not show_full and any(len(r['metadata']['content']) > 200 for r in results):
                    print(f"\n💡 Tip: Type a number (1-{len(results)}) to see full content of that result")
                    print("💡 Or use 'full:your query' to see all full content at once")
            else:
                print("❌ No results found.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error occurred: {e}")
            print("Please try again.")

def main():
    """Main function to initialize and run the interactive query interface."""
    try:
        print("🚀 Initializing RAG Query System...")
        print("=" * 50)
        
        # Load dataset (same as setup.py)
        print("📂 Loading dataset...")
        with open('data/codebase_chunks.json', 'r') as f:
            transformed_dataset = json.load(f)
        
        # Initialize VectorDB (same as setup.py)
        print("🗄️ Initializing Vector Database...")
        base_db = VectorDB("base_db")
        
        # Load and process data (same as setup.py)
        print("⚡ Loading and processing data...")
        base_db.load_data(transformed_dataset)
        
        print(f"✅ Database ready with {len(base_db.metadata)} chunks!")
        
        # Start interactive query loop
        interactive_query_loop(base_db)
        
    except FileNotFoundError as e:
        print(f"❌ Error: Required data file not found: {e}")
        print("💡 Make sure 'data/codebase_chunks.json' exists in your directory.")
    except Exception as e:
        print(f"❌ Error initializing system: {e}")
        print("💡 Check your API keys and data files.")

if __name__ == "__main__":
    main()