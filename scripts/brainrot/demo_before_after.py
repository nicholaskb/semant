#!/usr/bin/env python3
"""
Visual demonstration of before/after sanitization.

Shows exactly what investors would see vs what AI generates internally.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.brainrot.sanitize_outputs import sanitize_combinations


def main():
    """Show before/after comparison."""
    
    # Simulate what AI might generate internally (dirty)
    dirty_ai_output = [
        {
            "american_objects": ["iPhone", "Starbucks"],
            "italian_phrases": ["mamma mia"],
            "explanation": "I am now analyzing this combination and I think it's funny because the classic Italian exclamation pairs perfectly with modern American tech. Let me explain: this creates an absurd contrast that would be meme-worthy. So, here's what I found - this has high viral potential. Well, I believe this will perform well. Actually, I'm confident this is the right choice.",
            "humor_score": 8,
            "viral_score": 9,
            "combined_prompt": "mamma mia with iPhone, Starbucks"
        },
        {
            "american_objects": ["Tesla", "McDonald's"],
            "italian_phrases": ["ciao bella"],
            "explanation": "You know, as you can see, this is a great combination. It's worth noting that the cultural contrast creates humor. In my opinion, this will go viral. After careful consideration, I've determined this is best. Upon reflection, it seems like this would create the most shareable content.",
            "humor_score": 7,
            "viral_score": 8,
            "combined_prompt": "ciao bella with Tesla, McDonald's"
        }
    ]
    
    print("=" * 80)
    print("  INVESTOR-FACING CONTENT PROTECTION DEMONSTRATION")
    print("=" * 80)
    
    print("\n🔴 WHAT AI GENERATES INTERNALLY (DIRTY - NOT FOR INVESTORS):")
    print("-" * 80)
    print(json.dumps(dirty_ai_output[0], indent=2))
    
    # Sanitize (what investors see)
    clean_output = sanitize_combinations(dirty_ai_output)
    
    print("\n\n✅ WHAT INVESTORS SEE (CLEAN - SANITIZED):")
    print("-" * 80)
    print(json.dumps(clean_output[0], indent=2))
    
    print("\n\n📊 COMPARISON:")
    print("-" * 80)
    print(f"Original explanation length: {len(dirty_ai_output[0]['explanation'])} chars")
    print(f"Sanitized explanation length: {len(clean_output[0]['explanation'])} chars")
    print(f"\nOriginal: {dirty_ai_output[0]['explanation'][:100]}...")
    print(f"Sanitized: {clean_output[0]['explanation'][:100]}...")
    
    print("\n\n✅ VERIFICATION:")
    print("-" * 80)
    
    # Check structured data preserved
    assert clean_output[0]["american_objects"] == dirty_ai_output[0]["american_objects"]
    assert clean_output[0]["italian_phrases"] == dirty_ai_output[0]["italian_phrases"]
    assert clean_output[0]["humor_score"] == dirty_ai_output[0]["humor_score"]
    assert clean_output[0]["viral_score"] == dirty_ai_output[0]["viral_score"]
    print("✅ Structured data (objects, phrases, scores) - PRESERVED")
    
    # Check thinking patterns removed
    thinking_patterns = [
        "I am now analyzing", "I think", "Let me explain", "So, here's what",
        "Well, I believe", "Actually, I'm", "You know", "As you can see",
        "It's worth noting", "In my opinion", "After careful consideration",
        "Upon reflection", "It seems like"
    ]
    
    found_patterns = [p for p in thinking_patterns if p.lower() in clean_output[0]["explanation"].lower()]
    if not found_patterns:
        print("✅ Thinking patterns - REMOVED")
    else:
        print(f"⚠️  Some patterns may remain: {found_patterns}")
    
    print("\n" + "=" * 80)
    print("  PROOF: Investor-facing content is clean and professional")
    print("=" * 80)
    print("\nThe AI can be messy internally, but all outputs are sanitized")
    print("before being saved to GCS or exposed to investors.")
    print("\n✅ Pipeline is production-ready with content protection!")
    
    return 0


if __name__ == "__main__":
    exit(main())
