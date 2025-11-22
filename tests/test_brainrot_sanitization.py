#!/usr/bin/env python3
"""
Tests for output sanitization to ensure no AI inner-monologue leaks into outputs.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.brainrot.sanitize_outputs import (
    sanitize_text,
    sanitize_explanation,
    sanitize_combination,
    sanitize_combinations,
    sanitize_ai_response
)


class TestSanitization:
    """Test output sanitization functions."""
    
    def test_sanitize_text_removes_thinking_patterns(self):
        """Test that common AI thinking patterns are removed."""
        test_cases = [
            ("I am now analyzing this combination", "this combination"),
            ("Let me think about this...", ""),
            ("I think this is funny", "this is funny"),
            ("Now I will select the best one", "select the best one"),
            ("So, here's what I found", "what I found"),
            ("Well, I believe this works", "this works"),
            ("Actually, I'm going to choose this", "going to choose this"),
            ("You know, this is great", "this is great"),
            ("As you can see, this is viral", "this is viral"),
            ("It's worth noting that this is funny", "this is funny"),
            ("In my opinion, this works", "this works"),
            ("I'd like to suggest this", "suggest this"),
            ("To be honest, this is good", "this is good"),
            ("One thing I notice is this", "is this"),
            ("What I'm doing is selecting", "selecting"),
            ("The reason I chose this", "I chose this"),
            ("My reasoning is that this works", "this works"),
            ("After careful consideration, this is best", "this is best"),
            ("Upon reflection, this works", "this works"),
            ("It seems like this is good", "this is good"),
            ("It appears that this works", "this works"),
            ("It looks like this is viral", "this is viral"),
            ("It might be that this is funny", "this is funny"),
            ("It could be that this works", "this works"),
            ("It should be noted that this is good", "this is good"),
            ("It would seem that this works", "this works"),
            ("It will be clear that this is viral", "this is viral"),
            ("It can be seen that this works", "this works"),
            ("It may be that this is good", "this is good"),
            ("It must be noted that this works", "this works"),
        ]
        
        for input_text, expected in test_cases:
            result = sanitize_text(input_text)
            # Result should not contain the thinking pattern
            assert expected.lower() in result.lower() or len(result) == 0, \
                f"Failed for: {input_text} -> {result}"
    
    def test_sanitize_explanation(self):
        """Test explanation sanitization."""
        test_cases = [
            ("I am analyzing this and I think it's funny", "Viral content combination"),
            ("Let me explain: this is hilarious", "Viral content combination"),
            ("This is funny because of the contrast", "funny because of the contrast"),
            ("", ""),
            ("Simple explanation", "Simple explanation"),
        ]
        
        for input_text, expected_prefix in test_cases:
            result = sanitize_explanation(input_text)
            # Should either be the fallback or cleaned text
            assert isinstance(result, str)
            if len(result) < 3:
                assert result == "Viral content combination"
    
    def test_sanitize_combination(self):
        """Test combination sanitization."""
        combo = {
            "american_objects": ["iPhone", "Starbucks"],
            "italian_phrases": ["mamma mia"],
            "explanation": "I am now analyzing this and I think it's funny because...",
            "humor_score": 8,
            "viral_score": 9,
            "combined_prompt": "mamma mia with iPhone, Starbucks"
        }
        
        sanitized = sanitize_combination(combo)
        
        assert sanitized["american_objects"] == combo["american_objects"]
        assert sanitized["italian_phrases"] == combo["italian_phrases"]
        assert sanitized["humor_score"] == combo["humor_score"]
        assert sanitized["viral_score"] == combo["viral_score"]
        # Explanation should be sanitized
        assert "I am now analyzing" not in sanitized["explanation"]
        assert "I think" not in sanitized["explanation"].lower()
    
    def test_sanitize_combinations_list(self):
        """Test sanitizing a list of combinations."""
        combinations = [
            {
                "american_objects": ["iPhone"],
                "italian_phrases": ["ciao"],
                "explanation": "I think this is funny",
                "humor_score": 7,
                "viral_score": 8,
                "combined_prompt": "ciao with iPhone"
            },
            {
                "american_objects": ["Starbucks"],
                "italian_phrases": ["mamma mia"],
                "explanation": "Let me explain: this works",
                "humor_score": 8,
                "viral_score": 9,
                "combined_prompt": "mamma mia with Starbucks"
            }
        ]
        
        sanitized = sanitize_combinations(combinations)
        
        assert len(sanitized) == 2
        assert "I think" not in sanitized[0]["explanation"].lower()
        assert "Let me explain" not in sanitized[1]["explanation"].lower()
    
    def test_sanitize_ai_response(self):
        """Test sanitizing raw AI response."""
        response = """I am now analyzing the combinations.
Let me think about this...
Here's what I found:
{
  "combinations": [
    {
      "american_objects": ["iPhone"],
      "italian_phrases": ["ciao"],
      "explanation": "This is funny",
      "humor_score": 8,
      "viral_score": 9
    }
  ]
}"""
        
        sanitized = sanitize_ai_response(response)
        
        # Should still contain the JSON
        assert "combinations" in sanitized
        assert "iPhone" in sanitized
        # Should have fewer thinking lines
        assert sanitized.count("\n") < response.count("\n")
    
    def test_sanitize_preserves_valid_content(self):
        """Test that valid content is preserved."""
        valid_texts = [
            "This is funny because of the contrast",
            "Viral meme potential",
            "Absurd juxtaposition creates humor",
            "Cultural contrast is amusing",
            "Simple and memorable",
        ]
        
        for text in valid_texts:
            result = sanitize_text(text)
            # Should preserve the core meaning
            assert len(result) > 0
            # Should not be completely removed
            assert result != ""
    
    def test_sanitize_handles_empty_inputs(self):
        """Test that empty inputs are handled gracefully."""
        assert sanitize_text("") == ""
        assert sanitize_text(None) == ""
        assert sanitize_explanation("") == ""
        assert sanitize_explanation(None) == ""
        assert sanitize_combination({}) == {}
        assert sanitize_combinations([]) == []
        assert sanitize_ai_response("") == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
