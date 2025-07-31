"""
Main Module

Entry point for the resume query system.
"""

from resume_query.database import ResumeVectorDB
from resume_query.interactive import interactive_resume_query_loop
from resume_query.config import DEFAULT_RESUME_FILE, get_db_name_from_file


def main():
    """Main function to initialize and run the resume search interface."""
    try:
        print("🚀 Initializing Resume Search System...")
        print("=" * 50)
        
        # Generate database name based on resume file
        db_name = get_db_name_from_file(DEFAULT_RESUME_FILE)
        print(f"📁 Using database: {db_name}")
        
        # Initialize ResumeVectorDB
        print("🗄️ Initializing Resume Database...")
        resume_db = ResumeVectorDB(db_name)
        
        # Load and process resume data
        print("⚡ Loading and processing resume data...")
        resume_db.load_data(DEFAULT_RESUME_FILE)
        
        print(f"✅ Resume database ready with {len(resume_db.metadata)} searchable chunks!")
        
        # Start interactive query loop
        interactive_resume_query_loop(resume_db)
        
    except FileNotFoundError as e:
        print(f"❌ Error: Required resume file not found: {e}")
        print(f"💡 Make sure '{DEFAULT_RESUME_FILE}' exists in your directory.")
    except Exception as e:
        print(f"❌ Error initializing system: {e}")
        print("💡 Check your API keys and resume data file.")


if __name__ == "__main__":
    main()