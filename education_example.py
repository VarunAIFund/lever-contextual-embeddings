#!/usr/bin/env python3
"""
Example: How to use EducationVectorDB with different JSON files
"""

from resume_query.education_database import EducationVectorDB

def example_with_specific_file():
    """Example showing how to load a specific JSON file."""
    
    # Method 1: Specify file directly
    edu_db = EducationVectorDB(name="my_education_db")
    
    # Load your specific JSON file - replace with your actual filename
    json_file = "candidates_with_parsed_resumes.json"  # Change this to your file
    
    print(f"Loading education data from: {json_file}")
    edu_db.load_data(json_file)
    
    # Get statistics
    stats = edu_db.get_stats()
    print(f"Loaded {stats['total_records']} education records")
    print(f"From {stats['unique_candidates']} candidates")
    print(f"Covering {stats['unique_schools']} unique schools")
    
    # Search example
    results = edu_db.search("Computer Science", k=5)
    print(f"\nFound {len(results)} Computer Science results:")
    for i, result in enumerate(results[:3], 1):
        meta = result['metadata']
        print(f"{i}. {meta['name']} - {meta['school_name']}")
        print(f"   Degree: {meta['degree']}")
        print(f"   Similarity: {result['similarity']:.3f}")

def example_with_different_files():
    """Example showing how to use different JSON files."""
    
    files_to_try = [
        "candidates_with_parsed_resumes.json",      # Smaller dataset
        "10000_candidates_with_parsed_resumes.json", # Larger dataset
        # "your_custom_file.json"                   # Your custom file
    ]
    
    for json_file in files_to_try:
        try:
            print(f"\n{'='*50}")
            print(f"Testing with: {json_file}")
            print(f"{'='*50}")
            
            # Create new database instance for each file
            edu_db = EducationVectorDB(name=f"test_{json_file.replace('.json', '')}")
            edu_db.load_data(json_file)
            
            stats = edu_db.get_stats()
            print(f"✅ Success: {stats['total_records']} education records loaded")
            
            # Quick search test
            results = edu_db.search("Stanford", k=3)
            print(f"Stanford search found {len(results)} results")
            
        except FileNotFoundError:
            print(f"❌ File not found: {json_file}")
        except Exception as e:
            print(f"❌ Error with {json_file}: {e}")

if __name__ == "__main__":
    print("🎓 Education Database Examples")
    print("="*40)
    
    # Run the examples
    example_with_specific_file()
    example_with_different_files()
    
    print("\n" + "="*40)
    print("💡 To use your own JSON file:")
    print("1. Replace 'json_file' variable with your filename")
    print("2. Or run: python test_education_db.py your_file.json")
    print("3. Or modify this script with your specific file path")