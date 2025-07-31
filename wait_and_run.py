#!/usr/bin/env python3
"""
Wait and Run Script

Monitors an existing JSON file for completion (when it stops being written to)
and then automatically launches the resume query system.
"""

import os
import time
import subprocess
import sys

def wait_for_file_completion(filepath, check_interval=30, stable_duration=60):
    """
    Wait for a file to stop being modified (indicating writing is complete).
    
    Args:
        filepath: Path to the file to monitor
        check_interval: How often to check file size (seconds)
        stable_duration: How long file size must remain stable (seconds)
    """
    if not os.path.exists(filepath):
        print(f"❌ Error: File {filepath} does not exist!")
        return False
    
    print(f"📄 Monitoring {filepath} for completion...")
    print(f"⏳ Waiting for file to stop growing (stable for {stable_duration} seconds)...")
    
    stable_checks_needed = stable_duration // check_interval
    last_size = -1
    stable_count = 0
    
    while stable_count < stable_checks_needed:
        current_size = os.path.getsize(filepath)
        
        # Display current status
        if current_size != last_size:
            print(f"📊 Current file size: {current_size:,} bytes (+{current_size - last_size:,})")
            stable_count = 0  # Reset stability counter
        else:
            stable_count += 1
            remaining_checks = stable_checks_needed - stable_count
            print(f"⏸️  File size stable: {current_size:,} bytes ({remaining_checks} more checks needed)")
        
        last_size = current_size
        time.sleep(check_interval)
    
    print(f"✅ File {filepath} appears to be complete!")
    print(f"📏 Final size: {current_size:,} bytes")
    return True

def run_resume_query():
    """Launch the resume query system."""
    print("\n🚀 Starting resume query system...")
    print("=" * 50)
    
    try:
        # Run the resume query system
        subprocess.run([sys.executable, "new_resume_query.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running resume query system: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
        return False
    
    return True

def main():
    """Main function to wait for file completion and launch resume query."""
    target_file = "10000_candidates_with_parsed_resumes.json"
    
    print("🎯 Resume Query Auto-Launcher")
    print("=" * 50)
    print(f"📁 Monitoring: {target_file}")
    print("⚙️  Will launch new_resume_query.py when file is complete")
    print("\n💡 Press Ctrl+C to cancel at any time")
    
    try:
        # Wait for file to be complete
        if wait_for_file_completion(target_file):
            # Small delay to ensure file is fully flushed
            print("⏱️  Waiting 5 seconds to ensure file is fully written...")
            time.sleep(5)
            
            # Launch resume query system
            run_resume_query()
        else:
            print("❌ Failed to detect file completion")
            
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()