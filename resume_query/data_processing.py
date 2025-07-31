"""
Resume Data Processing Module

Handles parsing, chunking, and formatting of resume data.
"""

from typing import List, Dict, Any
from datetime import datetime
from tqdm import tqdm


def format_date(date_dict: Dict) -> str:
    """
    Format date dictionary to readable string.
    
    Args:
        date_dict: Dictionary with 'year' and optionally 'month' keys
        
    Returns:
        Formatted date string (e.g., "Jan 2020")
    """
    if not date_dict:
        return ""
    
    year = date_dict.get('year', '')
    month = date_dict.get('month', '')
    
    if year and month:
        try:
            return f"{datetime(year, month, 1).strftime('%b %Y')}"
        except:
            return f"{month}/{year}"
    elif year:
        return str(year)
    else:
        return ""


def process_resume_data(resume_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process resume JSON data into searchable chunks.
    
    Args:
        resume_data: List of candidate dictionaries from JSON
        
    Returns:
        List of processed chunks with metadata
    """
    chunks = []
    
    for candidate in tqdm(resume_data, desc="Processing candidates"):
        candidate_id = candidate.get('candidate_id', 'unknown')
        name = candidate.get('name', 'Unknown')
        email = candidate.get('email', '')
        location = candidate.get('location', '')
        headline = candidate.get('headline', '')
        stage = candidate.get('stage', '')
        
        # Create candidate summary chunk (focus on professionally relevant content)
        candidate_summary = f"""
        Location: {location}
        """.strip()
        
        chunks.append({
            'content': candidate_summary,
            'metadata': {
                'chunk_type': 'candidate_summary',
                'candidate_id': candidate_id,
                'name': name,
                'email': email,
                'location': location,
                'headline': headline,
                'stage': stage
            }
        })
        
        # Process individual positions
        parsed_resume = candidate.get('parsed_resume', {})
        positions = parsed_resume.get('positions', [])
        
        for i, position in enumerate(positions):
            org = position.get('org', '')
            title = position.get('title', '')
            summary = position.get('summary', '')
            location_pos = position.get('location', '')
            start = position.get('start', {})
            end = position.get('end', {})
            
            # Format dates
            start_date = format_date(start)
            end_date = format_date(end) if end else "Present"
            
            position_text = f"""
            Company: {org}
            Title: {title}
            Duration: {start_date} - {end_date}
            Location: {location_pos}
            
            Experience Details:
            {summary}
            """.strip()
            
            chunks.append({
                'content': position_text,
                'metadata': {
                    'chunk_type': 'position',
                    'candidate_id': candidate_id,
                    'name': name,
                    'email': email,
                    'position_index': i,
                    'company': org,
                    'title': title,
                    'start_date': start_date,
                    'end_date': end_date,
                    'location': location_pos,
                    'summary': summary
                }
            })
    
    return chunks


def get_content_from_metadata(metadata: Dict[str, Any]) -> str:
    """
    Reconstruct content from metadata for display.
    
    Args:
        metadata: Chunk metadata dictionary
        
    Returns:
        Reconstructed content string
    """
    if metadata['chunk_type'] == 'candidate_summary':
        return f"""Location: {metadata['location']}"""
    else:  # position
        return f"""Company: {metadata['company']}
Title: {metadata['title']}
Duration: {metadata['start_date']} - {metadata['end_date']}
Location: {metadata['location']}

Experience Details:
{metadata['summary']}"""