#!/usr/bin/env python3
"""
Enhance Candidates with Links

This script fetches candidate links from the Lever API and adds them to the 
existing candidates JSON file as a "links" field for each candidate.
"""

import json
import requests
import time
import os
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
from resume_query.config import LEVER_API_BASE_URL, LEVER_API_KEY, DEFAULT_RESUME_FILE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhance_candidates.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LeverAPIClient:
    """Client for interacting with Lever API to fetch candidate details."""
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Lever API key is required. Set LEVER_API_KEY environment variable.")
        
        self.api_key = api_key
        self.base_url = LEVER_API_BASE_URL
        self.session = requests.Session()
        self.session.auth = (api_key, '')  # Lever uses basic auth with API key as username
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'ResumeQuery/1.0'
        })
        
        # Rate limiting
        self.requests_per_second = 10  # Lever's rate limit: 10 requests per second
        self.request_interval = 1.0 / self.requests_per_second  # 0.1 seconds between requests
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Ensure we don't exceed rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_interval:
            sleep_time = self.request_interval - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def get_candidate_details(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch candidate details from Lever API.
        
        Args:
            candidate_id: Lever candidate ID
            
        Returns:
            Candidate data dict or None if not found/error
        """
        self._rate_limit()
        
        try:
            url = f"{self.base_url}/candidates/{candidate_id}"
            logger.debug(f"Fetching candidate details for: {candidate_id}")
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"Candidate not found: {candidate_id}")
                return None
            elif response.status_code == 429:
                # Rate limited - wait longer
                logger.warning("Rate limited, waiting 60 seconds...")
                time.sleep(60)
                return self.get_candidate_details(candidate_id)  # Retry
            else:
                logger.error(f"API error for {candidate_id}: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error for {candidate_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {candidate_id}: {e}")
            return None
    
    def extract_links(self, candidate_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Extract and categorize links from candidate data.
        
        Args:
            candidate_data: Full candidate data from Lever API
            
        Returns:
            List of link dictionaries with url and type
        """
        links = []
        candidate_info = candidate_data.get('data', {})
        
        # Get links from the links field
        raw_links = candidate_info.get('links', [])
        
        for link in raw_links:
            if isinstance(link, str):
                url = link.strip()
            elif isinstance(link, dict):
                url = link.get('url', '').strip()
            else:
                continue
            
            if not url:
                continue
            
            # Categorize link type
            link_type = self._categorize_link(url)
            links.append({
                'url': url,
                'type': link_type
            })
        
        return links
    
    def _categorize_link(self, url: str) -> str:
        """Categorize a URL by type."""
        url_lower = url.lower()
        
        if 'linkedin.com' in url_lower:
            return 'linkedin'
        elif any(domain in url_lower for domain in ['github.com', 'gitlab.com', 'bitbucket.org']):
            return 'code_repository'
        elif any(domain in url_lower for domain in ['portfolio', 'personal', 'website', '.dev', '.io']):
            return 'portfolio'
        elif any(domain in url_lower for domain in ['twitter.com', 'x.com']):
            return 'twitter'
        elif 'instagram.com' in url_lower:
            return 'instagram'
        elif 'facebook.com' in url_lower:
            return 'facebook'
        else:
            return 'other'


def create_backup(file_path: str) -> str:
    """Create a backup of the original file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup_{timestamp}"
    shutil.copy2(file_path, backup_path)
    logger.info(f"Created backup: {backup_path}")
    return backup_path


def enhance_candidates_with_links(
    candidates_file: str,
    start_from: int = 0,
    max_candidates: Optional[int] = None
) -> None:
    """
    Enhance candidates JSON file with links from Lever API.
    
    Args:
        candidates_file: Path to candidates JSON file
        start_from: Index to start processing from (for resuming)
        max_candidates: Maximum number of candidates to process (for testing)
    """
    
    # Validate API key
    if not LEVER_API_KEY:
        logger.error("LEVER_API_KEY environment variable not set!")
        return
    
    # Load existing candidates
    logger.info(f"Loading candidates from: {candidates_file}")
    try:
        with open(candidates_file, 'r') as f:
            candidates = json.load(f)
    except FileNotFoundError:
        logger.error(f"Candidates file not found: {candidates_file}")
        return
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in candidates file: {e}")
        return
    
    logger.info(f"Loaded {len(candidates)} candidates")
    
    # Create backup
    backup_path = create_backup(candidates_file)
    
    # Initialize API client
    try:
        api_client = LeverAPIClient(LEVER_API_KEY)
        logger.info("Lever API client initialized")
    except ValueError as e:
        logger.error(f"Failed to initialize API client: {e}")
        return
    
    # Process candidates
    total_candidates = len(candidates)
    end_index = min(total_candidates, start_from + max_candidates) if max_candidates else total_candidates
    
    logger.info(f"Processing candidates {start_from} to {end_index-1} of {total_candidates}")
    
    enhanced_count = 0
    error_count = 0
    
    for i in range(start_from, end_index):
        candidate = candidates[i]
        candidate_id = candidate.get('candidate_id')
        
        if not candidate_id:
            logger.warning(f"Candidate {i} missing candidate_id, skipping")
            continue
        
        # Skip if links already exist
        if 'links' in candidate:
            logger.debug(f"Candidate {candidate_id} already has links, skipping")
            continue
        
        logger.info(f"Processing {i+1}/{end_index}: {candidate_id}")
        
        # Fetch candidate details from Lever API
        candidate_data = api_client.get_candidate_details(candidate_id)
        
        if candidate_data:
            # Extract links
            links = api_client.extract_links(candidate_data)
            candidate['links'] = links
            
            if links:
                logger.info(f"Added {len(links)} links for {candidate_id}")
                enhanced_count += 1
            else:
                logger.debug(f"No links found for {candidate_id}")
                candidate['links'] = []  # Empty array to indicate we checked
        else:
            logger.error(f"Failed to fetch data for {candidate_id}")
            candidate['links'] = []  # Empty array to indicate we tried
            error_count += 1
        
        # Save progress every 50 candidates
        if (i + 1) % 50 == 0:
            logger.info(f"Saving progress... (processed {i+1} candidates)")
            try:
                with open(candidates_file, 'w') as f:
                    json.dump(candidates, f, indent=2)
                logger.info("Progress saved successfully")
            except Exception as e:
                logger.error(f"Failed to save progress: {e}")
    
    # Final save
    logger.info("Saving final results...")
    try:
        with open(candidates_file, 'w') as f:
            json.dump(candidates, f, indent=2)
        logger.info("Final results saved successfully")
    except Exception as e:
        logger.error(f"Failed to save final results: {e}")
        logger.error(f"Backup is available at: {backup_path}")
        return
    
    # Summary
    logger.info("=" * 60)
    logger.info("ENHANCEMENT COMPLETE")
    logger.info(f"Total candidates processed: {end_index - start_from}")
    logger.info(f"Candidates with links added: {enhanced_count}")
    logger.info(f"Errors encountered: {error_count}")
    logger.info(f"Backup created: {backup_path}")
    logger.info("=" * 60)


def main():
    """Main function with command line argument handling."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhance candidates JSON with links from Lever API')
    parser.add_argument('--file', default=DEFAULT_RESUME_FILE, 
                       help=f'Candidates JSON file (default: {DEFAULT_RESUME_FILE})')
    parser.add_argument('--start-from', type=int, default=0, 
                       help='Index to start processing from (for resuming)')
    parser.add_argument('--max-candidates', type=int, 
                       help='Maximum number of candidates to process (for testing)')
    parser.add_argument('--test', action='store_true', 
                       help='Test mode: process only first 10 candidates')
    
    args = parser.parse_args()
    
    if args.test:
        args.max_candidates = 10
        logger.info("Running in TEST MODE - processing only 10 candidates")
    
    logger.info("Starting candidate enhancement with links...")
    logger.info(f"File: {args.file}")
    logger.info(f"Start from: {args.start_from}")
    
    if args.max_candidates:
        logger.info(f"Max candidates: {args.max_candidates}")
    
    enhance_candidates_with_links(
        candidates_file=args.file,
        start_from=args.start_from,
        max_candidates=args.max_candidates
    )


if __name__ == "__main__":
    main()