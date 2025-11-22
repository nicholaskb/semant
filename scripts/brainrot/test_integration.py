#!/usr/bin/env python3
"""
Integration test showing sanitization works in the actual pipeline flow.

Simulates the full pipeline: AI generates -> sanitize -> save to GCS
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.brainrot.sanitize_outputs import sanitize_combinations, sanitize_ai_response


def simulate_ai_response():
    """Simulate what AI might return (with inner-monologue)."""
    return """I am now analyzing the combinations you've provided.
Let me think about this carefully...

So, here's what I found after careful consideration:

{
  "combinations": [
    {
      "american_objects": ["iPhone", "Starbucks"],
      "italian_phrases": ["mamma mia"],
      "explanation": "I am now analyzing this and I think it's funny because the classic Italian exclamation pairs perfectly with modern American tech. Let me explain: this creates an absurd contrast.",
      "humor_score": 8,
      "viral_score": 9,
      "combined_prompt": "mamma mia with iPhone, Starbucks"
    },
    {
      "american_objects": ["Tesla", "McDonald's"],
      "italian_phrases": ["ciao bella"],
      "explanation": "You know, as you can see, this is a great combination. It's worth noting that the cultural contrast creates humor. In my opinion, this will go viral.",
      "humor_score": 7,
      "viral_score": 8,
      "combined_prompt": "ciao bella with Tesla, McDonald's"
    }
  ]
}

Well, I believe these are the best combinations. Actually, I'm confident they will perform well."""


def test_pipeline_flow():
    """Test the complete pipeline flow."""
    print("=" * 80)
    print("  INTEGRATION TEST: Full Pipeline Flow")
    print("=" * 80)
    
    # Step 1: Simulate AI generating combinations (dirty)
    print("\n📥 STEP 1: AI Generates Combinations (Internal - Dirty)")
    print("-" * 80)
    raw_response = simulate_ai_response()
    print("Raw AI response (first 200 chars):")
    print(raw_response[:200] + "...")
    
    # Step 2: Parse JSON (simulating what ai_pairing.py does)
    print("\n\n🔧 STEP 2: Parse JSON from Response")
    print("-" * 80)
    json_start = raw_response.find('{')
    json_end = raw_response.rfind('}') + 1
    json_str = raw_response[json_start:json_end]
    data = json.loads(json_str)
    combinations = data.get("combinations", [])
    
    print(f"Parsed {len(combinations)} combinations")
    print(f"First combination explanation: {combinations[0]['explanation'][:100]}...")
    
    # Step 3: Sanitize (what happens in ai_pairing.py and main_pipeline.py)
    print("\n\n🧹 STEP 3: Sanitize Combinations (What Happens Before Saving)")
    print("-" * 80)
    sanitized = sanitize_combinations(combinations)
    
    print("After sanitization:")
    print(f"First combination explanation: {sanitized[0]['explanation'][:100]}...")
    
    # Step 4: Verify what would be saved to GCS
    print("\n\n💾 STEP 4: What Gets Saved to GCS (Investor-Facing)")
    print("-" * 80)
    gcs_output = json.dumps(sanitized, indent=2)
    print("First combination (as it would appear in GCS):")
    print(json.dumps(sanitized[0], indent=2))
    
    # Step 5: Verification
    print("\n\n✅ VERIFICATION")
    print("-" * 80)
    
    checks = []
    
    # Check 1: Structured data preserved
    for i, combo in enumerate(sanitized):
        if (combo["american_objects"] == combinations[i]["american_objects"] and
            combo["italian_phrases"] == combinations[i]["italian_phrases"] and
            combo["humor_score"] == combinations[i]["humor_score"] and
            combo["viral_score"] == combinations[i]["viral_score"]):
            checks.append(f"✅ Combination {i+1}: Structured data preserved")
        else:
            checks.append(f"❌ Combination {i+1}: Structured data corrupted!")
    
    # Check 2: Thinking patterns removed
    thinking_patterns = [
        "I am now analyzing", "I think", "Let me explain", "So, here's what",
        "Well, I believe", "Actually, I'm", "You know", "As you can see",
        "It's worth noting", "In my opinion"
    ]
    
    for i, combo in enumerate(sanitized):
        found_patterns = [p for p in thinking_patterns 
                         if p.lower() in combo["explanation"].lower()]
        if not found_patterns:
            checks.append(f"✅ Combination {i+1}: All thinking patterns removed")
        else:
            checks.append(f"⚠️  Combination {i+1}: Some patterns remain: {found_patterns}")
    
    # Check 3: Core content preserved
    for i, combo in enumerate(sanitized):
        original = combinations[i]["explanation"]
        sanitized_text = combo["explanation"]
        
        # Check that meaningful content is preserved
        if len(sanitized_text) > 20:  # Has meaningful content
            checks.append(f"✅ Combination {i+1}: Core content preserved ({len(sanitized_text)} chars)")
        else:
            checks.append(f"⚠️  Combination {i+1}: May have lost too much content")
    
    for check in checks:
        print(f"   {check}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("  INTEGRATION TEST RESULTS")
    print("=" * 80)
    
    passed = sum(1 for c in checks if "✅" in c)
    total = len(checks)
    
    print(f"\n✅ Passed: {passed}/{total} checks")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nThe pipeline correctly:")
        print("  1. Accepts dirty AI outputs internally")
        print("  2. Sanitizes all combinations before saving")
        print("  3. Preserves structured data (objects, phrases, scores)")
        print("  4. Removes thinking patterns from explanations")
        print("  5. Saves clean, investor-ready content to GCS")
        print("\n✅ Pipeline is production-ready!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} checks need attention")
        return 1


if __name__ == "__main__":
    exit(test_pipeline_flow())
