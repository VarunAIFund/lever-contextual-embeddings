#!/usr/bin/env python3
"""
Lever API script to get 1000 candidate profiles with parsed resume data
"""

import os
import json
import requests
import time
from pathlib import Path
from typing import List, Dict, Optional

def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env_file()

class LeverAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.lever.co/v1"
        self.session = requests.Session()
        self.session.auth = (api_key, '')
        self.rate_limit_delay = 0.1

    def make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make API request with rate limiting and error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            time.sleep(self.rate_limit_delay)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error making request to {endpoint}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text[:500]}")
            return {}

    def get_candidate_resumes(self, candidate_id: str) -> List[Dict]:
        """Get resumes for a specific candidate"""
        endpoint = f"/opportunities/{candidate_id}/resumes"
        data = self.make_request(endpoint)
        return data.get('data', [])

def load_existing_candidates(output_file: Path) -> List[Dict]:
    """Load existing candidates from file to resume progress"""
    if output_file.exists():
        try:
            with open(output_file, 'r') as f:
                candidates = json.load(f)
            print(f"📂 Found existing file with {len(candidates)} candidates")
            return candidates
        except (json.JSONDecodeError, FileNotFoundError):
            print("📂 Starting fresh - no existing file found")
            return []
    return []

def fetch_and_save_1000_candidates_with_parsed_resumes() -> int:
    """
    Fetch 1000 candidates from Lever API with parsed resume data, save incrementally
    
    Returns:
        Number of candidates saved
    """
    lever_api_key = os.getenv('LEVER_API_KEY')
    if not lever_api_key:
        print("❌ Error: LEVER_API_KEY environment variable not set")
        return 0
    
    api = LeverAPI(lever_api_key)
    limit = 10000
    batch_size = 100
    next_token = None
    
    # Prepare output file and load existing progress
    output_file = Path("10000_candidates_with_parsed_resumes.json")
    candidates_with_resumes = load_existing_candidates(output_file)
    candidates_saved = len(candidates_with_resumes)
    
    # Create a set of existing candidate IDs to avoid duplicates
    existing_ids = {candidate['candidate_id'] for candidate in candidates_with_resumes}
    
    print(f"🔍 Searching for {limit} candidates with parsed resumes...")
    print(f"📊 Starting with {candidates_saved} existing candidates")
    
    if candidates_saved >= limit:
        print(f"✅ Already have {candidates_saved} candidates - target reached!")
        return candidates_saved
    
    # Test API connection first
    print("🔌 Testing API connection...")
    test_data = api.make_request("/opportunities", {"limit": 1})
    if not test_data:
        print("❌ Failed to connect to Lever API. Please check your API key and permissions.")
        return candidates_saved
    
    batch_count = 0
    processed_total = 0
    
    while candidates_saved < limit:
        batch_count += 1
        
        # Fetch candidates from API with cursor-based pagination
        if next_token:
            print(f"📄 Fetching batch {batch_count} with next token...")
        else:
            print(f"📄 Fetching first batch {batch_count}...")
        
        params = {"limit": batch_size}
        if next_token:
            params["offset"] = next_token
        
        candidates_data = api.make_request("/opportunities", params)
        
        if not candidates_data or 'data' not in candidates_data:
            print("❌ No more candidates data received")
            break
        
        candidates = candidates_data['data']
        print(f"📊 Processing {len(candidates)} candidates from batch {batch_count}")
        
        # If no more candidates, break
        if not candidates:
            print("⚠️  No more candidates available")
            break
        
        # Process candidates and check for parsed resume data
        batch_found = 0
        for candidate in candidates:
            processed_total += 1
            
            if candidates_saved >= limit:
                break
                
            candidate_id = candidate['id']
            
            # Skip if we already have this candidate
            if candidate_id in existing_ids:
                continue
            
            resumes = api.get_candidate_resumes(candidate_id)
            
            # Check if any resume has parsed data
            has_parsed_resume = False
            parsed_resume_data = None
            
            for resume in resumes:
                if 'parsedData' in resume and resume['parsedData']:
                    has_parsed_resume = True
                    parsed_resume_data = resume['parsedData']
                    break
            
            if has_parsed_resume:
                candidate_profile = {
                    'candidate_id': candidate_id,
                    'name': candidate.get('name', 'Unknown'),
                    'email': candidate.get('emails', [None])[0] if candidate.get('emails') else None,
                    'location': candidate.get('location', ''),
                    'headline': candidate.get('headline', ''),
                    'stage': candidate.get('stage', ''),
                    'origin': candidate.get('origin', ''),
                    'createdAt': candidate.get('createdAt', ''),
                    'updatedAt': candidate.get('updatedAt', ''),
                    'archived': candidate.get('archived', {}).get('archivedAt') is not None if candidate.get('archived') else False,
                    'applications': candidate.get('applications', []),
                    'parsed_resume': parsed_resume_data
                }
                candidates_with_resumes.append(candidate_profile)
                existing_ids.add(candidate_id)
                candidates_saved += 1
                batch_found += 1
                
                # Save every 10 candidates to preserve progress
                if candidates_saved % 10 == 0:
                    with open(output_file, 'w') as f:
                        json.dump(candidates_with_resumes, f, indent=2)
                
                print(f"✅ Saved {candidates_saved}/{limit}: {candidate.get('name', 'Unknown')}")
        
        print(f"📈 Batch {batch_count} results: {batch_found} new candidates found, {processed_total} total processed")
        
        # Save progress after each batch
        with open(output_file, 'w') as f:
            json.dump(candidates_with_resumes, f, indent=2)
        
        # Get next token for pagination
        next_token = candidates_data.get('next')
        
        # If no next token, we've reached the end
        if not next_token:
            print("⚠️  Reached end of candidates (no next token)")
            break
    
    # Final save
    with open(output_file, 'w') as f:
        json.dump(candidates_with_resumes, f, indent=2)
    
    print(f"🎯 Final result: {candidates_saved} candidates saved to {output_file}")
    print(f"📊 Total candidates processed: {processed_total}")
    return candidates_saved

def main():
    """Main function to fetch and save 1000 candidate profiles"""
    print("🚀 Fetching and Saving 1000 Candidate Profiles with Parsed Resumes from Lever API")
    print("=" * 80)
    
    start_time = time.time()
    
    # Fetch and save candidates
    candidates_saved = fetch_and_save_1000_candidates_with_parsed_resumes()
    
    elapsed_time = time.time() - start_time
    
    if candidates_saved == 0:
        print("❌ No candidates found with parsed resume data")
        return
    
    print(f"\n✅ Successfully saved {candidates_saved} candidates with parsed resume data")
    print(f"💾 Results saved to: 1000_candidates_with_parsed_resumes.json")
    print(f"⏱️  Total time: {elapsed_time:.1f} seconds")
    
    # Show a preview of the saved data
    output_file = Path("1000_candidates_with_parsed_resumes.json")
    if output_file.exists():
        with open(output_file, 'r') as f:
            saved_candidates = json.load(f)
        
        print(f"\n📋 Preview of saved candidates:")
        print("=" * 50)
        
        # Display first 3 candidates as examples
        for i, candidate in enumerate(saved_candidates[:3], 1):
            print(f"\n{i}. {candidate['name']}")
            print(f"   📧 Email: {candidate['email'] or 'Not available'}")
            print(f"   📍 Location: {candidate['location'] or 'Not specified'}")
            print(f"   💼 Headline: {candidate['headline'] or 'Not specified'}")
            print(f"   🎯 Stage: {candidate['stage'] or 'Not specified'}")
            print(f"   📄 Has parsed resume: ✅")
            
            # Show a snippet of parsed resume if available
            parsed_resume = candidate.get('parsed_resume')
            if parsed_resume and isinstance(parsed_resume, dict):
                # Show available fields in parsed resume
                fields = list(parsed_resume.keys())[:5]  # Show first 5 fields
                print(f"   📝 Parsed fields: {', '.join(fields)}")
            
            print("-" * 50)
        
        if len(saved_candidates) > 3:
            print(f"\n... and {len(saved_candidates) - 3} more candidates saved to file")
        
        print(f"\n📊 Final Statistics:")
        print(f"   🎯 Target: 1000 candidates")
        print(f"   ✅ Achieved: {len(saved_candidates)} candidates")
        print(f"   📈 Success rate: {(len(saved_candidates)/1000)*100:.1f}%")

if __name__ == "__main__":
    main()