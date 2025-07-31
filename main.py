#!/usr/bin/env python3
"""
Main execution script for Contextual Embeddings RAG Pipeline

This script runs setup.py which contains the complete pipeline implementation.
"""

import subprocess
import sys

def main():
    """Run the setup.py script which contains the full pipeline."""
    try:
        print("Running Contextual Embeddings RAG Pipeline...")
        print("=" * 50)
        
        # Run setup.py
        result = subprocess.run([sys.executable, "setup.py"], 
                              capture_output=False, 
                              text=True)
        
        if result.returncode == 0:
            print("\n" + "=" * 50)
            print("Pipeline completed successfully!")
        else:
            print("\n" + "=" * 50)
            print(f"Pipeline failed with return code: {result.returncode}")
            
    except Exception as e:
        print(f"Error running pipeline: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()