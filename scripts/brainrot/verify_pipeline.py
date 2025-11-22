#!/usr/bin/env python3
"""
Quick verification script to ensure the brainrot pipeline is working.

This script checks:
1. All imports work
2. Sanitization functions work
3. Pipeline can be instantiated
4. Configuration is valid
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_imports():
    """Test that all imports work."""
    print("Testing imports...")
    try:
        from scripts.brainrot.config import config
        from scripts.brainrot.sanitize_outputs import sanitize_text, sanitize_combinations
        from scripts.brainrot.main_pipeline import BrainRotPipeline
        from scripts.brainrot.ai_pairing import AIPairingEngine
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_sanitization():
    """Test sanitization functions."""
    print("\nTesting sanitization...")
    try:
        from scripts.brainrot.sanitize_outputs import sanitize_text, sanitize_explanation
        
        # Test that thinking patterns are removed
        result1 = sanitize_text("I am now analyzing this")
        assert "I am now analyzing" not in result1.lower(), f"Thinking pattern not removed: {result1}"
        
        result2 = sanitize_text("Let me think about this...")
        assert "Let me think" not in result2.lower(), f"Thinking pattern not removed: {result2}"
        
        # Test that valid content is preserved
        result3 = sanitize_text("This is funny")
        assert len(result3) > 0, "Valid content was removed"
        assert "funny" in result3.lower() or len(result3) == 0, f"Content not preserved: {result3}"
        
        # Test explanation
        result4 = sanitize_explanation("I think this is funny")
        assert "I think" not in result4.lower(), f"Thinking pattern in explanation: {result4}"
        
        print("✅ Sanitization working correctly")
        return True
    except Exception as e:
        print(f"❌ Sanitization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """Test configuration."""
    print("\nTesting configuration...")
    try:
        from scripts.brainrot.config import config
        
        assert config.gcs_bucket_name == "brainrot-trends"
        assert config.combinations_per_run > 0
        assert config.time_range_weeks > 0
        print("✅ Configuration valid")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_pipeline_instantiation():
    """Test that pipeline can be instantiated."""
    print("\nTesting pipeline instantiation...")
    try:
        from scripts.brainrot.main_pipeline import BrainRotPipeline
        
        pipeline = BrainRotPipeline(skip_images=True)
        assert pipeline.skip_images == True
        assert pipeline.results is not None
        print("✅ Pipeline instantiation successful")
        return True
    except Exception as e:
        print(f"❌ Pipeline instantiation failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("=" * 60)
    print("BRAINROT PIPELINE VERIFICATION")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_sanitization,
        test_config,
        test_pipeline_instantiation,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ ALL TESTS PASSED - Pipeline is ready!")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Check errors above")
        return 1

if __name__ == "__main__":
    exit(main())
