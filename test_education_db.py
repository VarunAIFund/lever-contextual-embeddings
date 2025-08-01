#!/usr/bin/env python3
"""
Test script for the Education Vector Database
"""

import json
import os
from resume_query.education_database import EducationVectorDB

def main():
    """Test the education database functionality."""
    
    import sys
    
    # Allow specifying custom JSON file as command line argument
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
        if not os.path.exists(data_file):
            print(f"Error: Specified file '{data_file}' not found.")
            return
    else:
        # Default file selection logic
        data_file = "candidates_with_parsed_resumes.json"
        if not os.path.exists(data_file):
            data_file = "10000_candidates_with_parsed_resumes.json"
            if not os.path.exists(data_file):
                print("Error: No resume data file found. Please ensure 'candidates_with_parsed_resumes.json' or '10000_candidates_with_parsed_resumes.json' exists.")
                print("Or specify a custom file: python test_education_db.py your_file.json")
                return
    
    print(f"Using data file: {data_file}")
    
    # Initialize education database
    edu_db = EducationVectorDB(name="education_test_db")
    
    # Load data
    print("Loading education data...")
    edu_db.load_data(data_file)
    
    # Get statistics
    stats = edu_db.get_stats()
    print(f"\nEducation Database Statistics:")
    print(f"- Total education records: {stats['total_records']}")
    print(f"- Unique candidates: {stats['unique_candidates']}")
    print(f"- Unique schools: {stats['unique_schools']}")
    
    if stats['degree_distribution']:
        print(f"\nTop degree types:")
        sorted_degrees = sorted(stats['degree_distribution'].items(), key=lambda x: x[1], reverse=True)
        for degree, count in sorted_degrees[:10]:
            if degree.strip():  # Only show non-empty degrees
                print(f"  {degree}: {count}")
    
    # Test searches
    test_queries = [
        "Stanford University",
        "Computer Science degree",
        "MBA",
        "Harvard",
        "Bachelor",
        "Engineering",
        "PhD"
    ]
    
    print(f"\n{'='*50}")
    print("Testing education searches:")
    print(f"{'='*50}")
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = edu_db.search(query, k=5)
        
        if results:
            print(f"Found {len(results)} results:")
            for i, result in enumerate(results[:3], 1):
                metadata = result['metadata']
                similarity = result['similarity']
                print(f"  {i}. {metadata['name']} - {metadata['school_name']}")
                print(f"     Degree: {metadata['degree']}")
                if metadata.get('field_of_study'):
                    print(f"     Field: {metadata['field_of_study']}")
                print(f"     Similarity: {similarity:.3f}")
        else:
            print("  No results found")
        print("-" * 30)

if __name__ == "__main__":
    main()