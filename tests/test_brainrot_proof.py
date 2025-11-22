#!/usr/bin/env python3
"""
PROOF: Demonstrating the fix works correctly
Shows actual code execution with real output
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.brainrot.ai_pairing import AIPairingEngine
from loguru import logger

# Configure logger to show all output clearly
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level:8} | {message}", colorize=True)

async def proof_test_1_empty_tokens():
    """PROOF TEST 1: Empty tokens - should return [] WITHOUT initializing"""
    print("\n" + "="*80)
    print("PROOF TEST 1: Empty Tokens (Should NOT Initialize)")
    print("="*80)
    
    engine = AIPairingEngine()
    print(f"\n✓ Engine created")
    print(f"✓ vertex_client = {engine.vertex_client}")
    
    print("\n📞 Calling: select_best_combinations([], [], num_combinations=5)")
    print("\n🔍 Expected behavior:")
    print("   1. Check: if not american_tokens or not italian_tokens")
    print("   2. Return [] immediately")
    print("   3. NEVER call initialize()")
    
    print("\n📊 Actual execution:")
    results = await engine.select_best_combinations([], [], num_combinations=5)
    
    print(f"\n✅ RESULTS: {results}")
    print(f"✅ Type: {type(results)}")
    print(f"✅ Length: {len(results)}")
    print(f"✅ Is empty list: {results == []}")
    print(f"✅ vertex_client after call: {engine.vertex_client}")
    
    if results == [] and engine.vertex_client is None:
        print("\n🎉 SUCCESS: Empty tokens returned [] WITHOUT initializing!")
        return True
    else:
        print("\n❌ FAILURE: Something went wrong!")
        return False

async def proof_test_2_with_mock():
    """PROOF TEST 2: With mock - should work same way"""
    print("\n" + "="*80)
    print("PROOF TEST 2: Empty Tokens WITH Mock (Test Scenario)")
    print("="*80)
    
    engine = AIPairingEngine()
    mock_client = AsyncMock()
    engine.vertex_client = mock_client
    
    print(f"\n✓ Engine created")
    print(f"✓ vertex_client = Mock (set for test)")
    
    print("\n📞 Calling: select_best_combinations([], [], num_combinations=5)")
    
    results = await engine.select_best_combinations([], [], num_combinations=5)
    
    print(f"\n✅ RESULTS: {results}")
    print(f"✅ Mock initialize() called? {hasattr(mock_client, 'initialize') and mock_client.initialize.called if hasattr(mock_client, 'initialize') else 'N/A'}")
    
    if results == []:
        print("\n🎉 SUCCESS: Returns [] correctly (mock doesn't matter - empty check happens first!)")
        return True
    else:
        print("\n❌ FAILURE!")
        return False

async def proof_test_3_with_real_tokens():
    """PROOF TEST 3: With real tokens - should initialize"""
    print("\n" + "="*80)
    print("PROOF TEST 3: Real Tokens (Should Initialize)")
    print("="*80)
    
    engine = AIPairingEngine()
    print(f"\n✓ Engine created")
    print(f"✓ vertex_client = {engine.vertex_client}")
    
    # Use mock to avoid actual API call but show initialization attempt
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.success = False
    mock_response.error_message = "Mocked for demonstration"
    mock_client.generate_text = AsyncMock(return_value=mock_response)
    
    # Override initialize to show it would be called
    original_init = engine.initialize
    init_called = []
    
    async def tracked_init():
        init_called.append(True)
        engine.vertex_client = mock_client
        print("   🔧 initialize() CALLED (would connect to Vertex AI)")
    
    engine.initialize = tracked_init
    
    print("\n📞 Calling: select_best_combinations([{'word': 'test'}], [{'word': 'test'}])")
    print("\n🔍 Expected behavior:")
    print("   1. Check: if not american_tokens or not italian_tokens → FALSE (has tokens)")
    print("   2. Check: if not vertex_client → TRUE (needs init)")
    print("   3. Call initialize()")
    print("   4. Process tokens")
    
    print("\n📊 Actual execution:")
    results = await engine.select_best_combinations(
        [{"word": "test", "pos": "NOUN"}],
        [{"word": "test", "pos": "NOUN"}],
        num_combinations=1
    )
    
    print(f"\n✅ RESULTS: {results}")
    print(f"✅ initialize() called? {len(init_called) > 0}")
    print(f"✅ vertex_client after call: {type(engine.vertex_client).__name__}")
    
    if len(init_called) > 0:
        print("\n🎉 SUCCESS: With real tokens, initialize() IS called!")
        return True
    else:
        print("\n❌ FAILURE: initialize() should have been called!")
        return False

async def main():
    print("\n" + "🔬"*40)
    print("COMPREHENSIVE PROOF: Empty Token Check Happens FIRST")
    print("🔬"*40)
    
    results = []
    
    # Test 1: Empty tokens, no mock
    result1 = await proof_test_1_empty_tokens()
    results.append(("Empty tokens (no mock)", result1))
    
    # Test 2: Empty tokens, with mock
    result2 = await proof_test_2_with_mock()
    results.append(("Empty tokens (with mock)", result2))
    
    # Test 3: Real tokens
    result3 = await proof_test_3_with_real_tokens()
    results.append(("Real tokens", result3))
    
    # Summary
    print("\n" + "="*80)
    print("FINAL VERIFICATION SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {test_name}")
    
    all_passed = all(r[1] for r in results)
    
    print("\n" + "="*80)
    if all_passed:
        print("🎉 ALL TESTS PASSED - CODE IS WORKING CORRECTLY!")
        print("="*80)
        print("\nKEY FINDINGS:")
        print("  ✓ Empty tokens → Returns [] immediately (NO initialization)")
        print("  ✓ Real tokens → Initializes first, then processes")
        print("  ✓ Empty check happens BEFORE initialization check")
        print("  ✓ Fix is working as expected!")
    else:
        print("❌ SOME TESTS FAILED - NEEDS INVESTIGATION")
        print("="*80)
    
    print()

if __name__ == "__main__":
    asyncio.run(main())

