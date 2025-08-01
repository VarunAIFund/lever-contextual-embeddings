#!/usr/bin/env python3
"""
Test the updated EducationVectorDB with custom JSON file
"""

from resume_query.education_database import EducationVectorDB

def test_with_custom_json():
    """Test education database with custom JSON file."""
    
    # Method 1: Specify JSON file in constructor (auto-loads)
    print("Method 1: Auto-load JSON file in constructor")
    print("=" * 50)
    
    edu_db1 = EducationVectorDB(
        name="custom_education_db",
        json_file="candidates_with_parsed_resumes.json"  # Your custom JSON file here
    )
    
    # Database is already loaded at this point
    stats1 = edu_db1.get_stats()
    print(f"✅ Auto-loaded {stats1['total_records']} education records")
    print(f"📚 From {stats1['unique_schools']} unique schools")
    
    # Test search
    results1 = edu_db1.search("Computer Science", k=3)
    print(f"🔍 Found {len(results1)} Computer Science results")
    for i, result in enumerate(results1, 1):
        meta = result['metadata']
        print(f"  {i}. {meta['name']} - {meta['school_name']}")
        print(f"     Degree: {meta['degree']}")
    
    print("\n" + "=" * 50)
    
    # Method 2: Specify different JSON file manually
    print("Method 2: Load different JSON file manually")
    print("=" * 50)
    
    edu_db2 = EducationVectorDB(name="another_education_db")
    edu_db2.load_data("10000_candidates_with_parsed_resumes.json")  # Different file
    
    stats2 = edu_db2.get_stats()
    print(f"✅ Manually loaded {stats2['total_records']} education records")
    print(f"📚 From {stats2['unique_schools']} unique schools")
    
    # Test search
    results2 = edu_db2.search("Stanford", k=3)
    print(f"🔍 Found {len(results2)} Stanford results")
    for i, result in enumerate(results2, 1):
        meta = result['metadata']
        print(f"  {i}. {meta['name']} - {meta['school_name']}")
        print(f"     Degree: {meta['degree']}")

def test_with_different_files():
    """Test with multiple different JSON files."""
    
    json_files = [
        "candidates_with_parsed_resumes.json",
        "10000_candidates_with_parsed_resumes.json",
        # Add your custom JSON files here:
        # "your_custom_file.json",
        # "another_dataset.json"
    ]
    
    print("\nTesting with different JSON files:")
    print("=" * 50)
    
    for i, json_file in enumerate(json_files, 1):
        try:
            print(f"\n{i}. Testing with: {json_file}")
            
            # Create database with custom JSON file
            edu_db = EducationVectorDB(
                name=f"test_db_{i}",
                json_file=json_file
            )
            
            stats = edu_db.get_stats()
            print(f"   ✅ Success: {stats['total_records']} records, {stats['unique_schools']} schools")
            
            # Quick search test
            results = edu_db.search("Harvard", k=2)
            print(f"   🔍 Harvard search: {len(results)} results")
            
        except FileNotFoundError:
            print(f"   ❌ File not found: {json_file}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    print("🎓 Testing Custom Education Database")
    print("=" * 50)
    
    test_with_custom_json()
    test_with_different_files()
    
    print("\n" + "=" * 50)
    print("💡 Usage Examples:")
    print("# Auto-load JSON file:")
    print("edu_db = EducationVectorDB(name='my_db', json_file='your_file.json')")
    print()
    print("# Or load manually:")
    print("edu_db = EducationVectorDB(name='my_db')")
    print("edu_db.load_data('your_file.json')")