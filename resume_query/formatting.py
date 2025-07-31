"""
Formatting Module

Handles result display and formatting functions.
"""

from typing import List, Dict, Any
import textwrap


def format_resume_results(results: List[Dict[str, Any]], query: str, show_full_content: bool = False) -> None:
    """
    Format and display resume search results.
    
    Args:
        results: List of search results
        query: Original search query
        show_full_content: Whether to show full content or preview
    """
    print(f"\n🔍 Resume Search: '{query}'")
    print(f"👥 Found {len(results)} matching candidates/positions:")
    print("=" * 80)
    
    for i, result in enumerate(results, 1):
        metadata = result['metadata']
        similarity = result.get('similarity', result.get('score', 0))
        content = result['content']
        content_length = len(content)
        
        # Show either full content or preview
        if show_full_content or content_length <= 300:
            content_display = content
        else:
            content_display = content[:300] + "..."
        
        # Different display based on chunk type
        if metadata['chunk_type'] == 'candidate_summary':
            print(f"\n{i}. 👤 CANDIDATE PROFILE")
            print(f"   📧 {metadata['name']} ({metadata['email']})")
            print(f"   📍 {metadata['location']}")
            print(f"   🎯 Stage: {metadata['stage']}")
            print(f"   🔗 Similarity: {similarity:.4f}")
        else:  # position
            print(f"\n{i}. 💼 JOB EXPERIENCE")
            print(f"   👤 {metadata['name']} ({metadata['email']})")
            print(f"   🏢 {metadata['company']} - {metadata['title']}")
            print(f"   📅 {metadata['start_date']} - {metadata['end_date']}")
            print(f"   🔗 Similarity: {similarity:.4f}")
        
        print(f"   📏 Content Length: {content_length} characters")
        print(f"   📝 Details:")
        
        # Format content with proper wrapping
        wrapped_content = textwrap.fill(content_display, width=76, initial_indent="      ", subsequent_indent="      ")
        print(wrapped_content)
        
        if not show_full_content and content_length > 300:
            print(f"      ... ({content_length - 300} more characters)")
        
        print("-" * 80)


def show_full_resume_result(results: List[Dict[str, Any]], result_number: int) -> None:
    """
    Show the full details of a specific resume result.
    
    Args:
        results: List of search results
        result_number: 1-based index of result to show
    """
    if 1 <= result_number <= len(results):
        result = results[result_number - 1]
        metadata = result['metadata']
        content = result['content']
        similarity = result.get('similarity', result.get('score', 0))
        
        print(f"\n📖 Full Details for Result #{result_number}:")
        print("=" * 80)
        
        if metadata['chunk_type'] == 'candidate_summary':
            print(f"👤 CANDIDATE: {metadata['name']}")
            print(f"📧 Email: {metadata['email']}")
            print(f"📍 Location: {metadata['location']}")
            print(f"🎯 Stage: {metadata['stage']}")
            print(f"🔗 Similarity: {similarity:.4f}")
            print(f"\n💼 Professional Summary:")
            print(f"{metadata['headline']}")
        else:
            print(f"💼 JOB EXPERIENCE")
            print(f"👤 Candidate: {metadata['name']} ({metadata['email']})")
            print(f"🏢 Company: {metadata['company']}")
            print(f"📋 Title: {metadata['title']}")
            print(f"📅 Duration: {metadata['start_date']} - {metadata['end_date']}")
            print(f"📍 Location: {metadata['location']}")
            print(f"🔗 Similarity: {similarity:.4f}")
            print(f"\n📝 Experience Details:")
            print("-" * 40)
            wrapped_summary = textwrap.fill(metadata['summary'], width=76)
            print(wrapped_summary)
        
        print("=" * 80)
    else:
        print(f"❌ Invalid result number. Please choose between 1 and {len(results)}.")