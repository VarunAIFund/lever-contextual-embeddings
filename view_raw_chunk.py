#!/usr/bin/env python3
"""
Raw Chunk Viewer

Shows the raw chunk data structure for one candidate.
"""

import json
from resume_query.data_processing import process_resume_data


def view_raw_chunk(resume_file: str = 'candidates_with_parsed_resumes.json'):
    """Show raw chunk data for the first candidate."""
    
    try:
        # Load resume data
        with open(resume_file, 'r') as f:
            resume_data = json.load(f)
        
        # Process just the first candidate
        first_candidate = [resume_data[0]]
        chunks = process_resume_data(first_candidate)
        
        print("🔍 RAW CHUNKS FOR FIRST CANDIDATE")
        print("=" * 50)
        print(f"Candidate: {chunks[0]['metadata']['name']}")
        print(f"Total chunks created: {len(chunks)}")
        print()
        
        # Print each chunk as raw Python dict
        for i, chunk in enumerate(chunks):
            print(f"CHUNK {i+1}:")
            print(json.dumps(chunk, indent=2, ensure_ascii=False))
            print()
            print("-" * 50)
            print()
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    view_raw_chunk()