#!/usr/bin/env python3
"""
Chunk Viewer

This script shows you exactly what chunks get created from your resume data
without running the full RAG system. Useful for debugging and understanding
the data processing pipeline.
"""

import json
import argparse
from resume_query.data_processing import process_resume_data


def view_chunks(resume_file: str, max_candidates: int = 3, max_chunks_per_candidate: int = 5):
    """
    Load resume data and show the chunks that would be created.
    
    Args:
        resume_file: Path to resume JSON file
        max_candidates: How many candidates to process
        max_chunks_per_candidate: Max chunks to show per candidate
    """
    
    print("🔍 Resume Chunk Viewer")
    print("=" * 60)
    
    try:
        # Load resume data
        print(f"📄 Loading resume data from: {resume_file}")
        with open(resume_file, 'r') as f:
            resume_data = json.load(f)
        
        print(f"✅ Loaded {len(resume_data)} total candidates")
        
        # Limit to first N candidates for viewing
        candidates_to_process = resume_data[:max_candidates]
        print(f"🎯 Processing first {len(candidates_to_process)} candidates for preview")
        print()
        
        # Process into chunks
        chunks = process_resume_data(candidates_to_process)
        
        print(f"📊 CHUNK STATISTICS:")
        print(f"   Total chunks created: {len(chunks)}")
        
        # Count chunk types
        candidate_summaries = sum(1 for c in chunks if c['metadata']['chunk_type'] == 'candidate_summary')
        position_chunks = sum(1 for c in chunks if c['metadata']['chunk_type'] == 'position')
        
        print(f"   Candidate summary chunks: {candidate_summaries}")
        print(f"   Position chunks: {position_chunks}")
        print(f"   Average chunks per candidate: {len(chunks) / len(candidates_to_process):.1f}")
        print()
        
        # Display chunks by candidate
        current_candidate = None
        chunks_shown_for_candidate = 0
        
        for i, chunk in enumerate(chunks):
            metadata = chunk['metadata']
            candidate_id = metadata['candidate_id']
            candidate_name = metadata['name']
            
            # New candidate
            if candidate_id != current_candidate:
                current_candidate = candidate_id
                chunks_shown_for_candidate = 0
                
                print("=" * 60)
                print(f"👤 CANDIDATE: {candidate_name} (ID: {candidate_id})")
                print("=" * 60)
            
            # Skip if we've shown enough chunks for this candidate
            chunks_shown_for_candidate += 1
            if chunks_shown_for_candidate > max_chunks_per_candidate:
                continue
            
            # Display chunk
            chunk_type = metadata['chunk_type']
            chunk_icon = "📋" if chunk_type == 'candidate_summary' else "💼"
            
            print(f"\n{chunk_icon} CHUNK {i+1}: {chunk_type.upper()}")
            print("-" * 40)
            
            # Show searchable content
            print("🔍 SEARCHABLE CONTENT:")
            content = chunk['content']
            if content.strip():
                for line in content.split('\n'):
                    if line.strip():
                        print(f"   {line}")
            else:
                print("   (Empty content)")
            
            # Show key metadata
            print(f"\n📝 KEY METADATA:")
            if chunk_type == 'candidate_summary':
                print(f"   Candidate: {metadata.get('name', 'Unknown')}")
                print(f"   Email: {metadata.get('email', 'No email')}")
                print(f"   Location: {metadata.get('location', 'No location')}")
                print(f"   Stage: {metadata.get('stage', 'No stage')}")
            else:  # position
                print(f"   Candidate: {metadata.get('name', 'Unknown')}")
                print(f"   Company: {metadata.get('company', 'Unknown')}")
                print(f"   Title: {metadata.get('title', 'Unknown')}")
                print(f"   Duration: {metadata.get('start_date', '')} - {metadata.get('end_date', '')}")
                print(f"   Position Index: {metadata.get('position_index', 'N/A')}")
            
            print(f"   Chunk Type: {chunk_type}")
            print(f"   Candidate ID: {candidate_id}")
        
        print("\n" + "=" * 60)
        print("🎯 SUMMARY")
        print("=" * 60)
        print(f"✅ Successfully processed {len(candidates_to_process)} candidates")
        print(f"📦 Created {len(chunks)} total searchable chunks")
        print(f"🔍 Each chunk's 'content' field gets embedded and searched")
        print(f"📝 Each chunk's 'metadata' field provides context for display")
        print()
        print("💡 This is exactly what your RAG system will search through!")
        
    except FileNotFoundError:
        print(f"❌ Error: File '{resume_file}' not found")
        print("💡 Make sure the file path is correct")
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in '{resume_file}': {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def main():
    """Main function with command line arguments."""
    parser = argparse.ArgumentParser(description='View resume chunks without running full RAG system')
    parser.add_argument('--file', default='candidates_with_parsed_resumes.json',
                       help='Resume JSON file to process (default: candidates_with_parsed_resumes.json)')
    parser.add_argument('--candidates', type=int, default=3,
                       help='Number of candidates to process (default: 3)')
    parser.add_argument('--chunks-per-candidate', type=int, default=5,
                       help='Max chunks to show per candidate (default: 5)')
    
    args = parser.parse_args()
    
    view_chunks(
        resume_file=args.file,
        max_candidates=args.candidates,
        max_chunks_per_candidate=args.chunks_per_candidate
    )


if __name__ == "__main__":
    main()