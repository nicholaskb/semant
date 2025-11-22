#!/usr/bin/env python3
"""
REAL EXECUTION TEST - Shows actual code behavior with detailed logging
No mocks, no assumptions - just real execution traces
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up detailed logging
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler('tests/brainrot_execution_log.txt', mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

from scripts.brainrot.ai_pairing import AIPairingEngine
from loguru import logger

# Also capture loguru output
logger.remove()
logger.add('tests/brainrot_execution_log.txt', level='DEBUG', format='{time} | {level:8} | {message}')
logger.add(sys.stdout, level='INFO', format='{time:HH:mm:ss} | {level:8} | {message}')

def log_step(step_num, description, data=None):
    """Log a step with data"""
    print(f"\n{'='*80}")
    print(f"STEP {step_num}: {description}")
    print(f"{'='*80}")
    if data:
        print(f"Data: {json.dumps(data, indent=2, default=str)}")

async def test_real_execution_empty_tokens():
    """Real execution test with empty tokens - NO MOCKS"""
    log_file = Path('tests/brainrot_execution_log.txt')
    if log_file.exists():
        log_file.unlink()
    
    print("\n" + "🔬"*40)
    print("REAL EXECUTION TEST - EMPTY TOKENS")
    print("🔬"*40)
    print(f"Log file: {log_file.absolute()}")
    
    log_step(1, "Creating AIPairingEngine instance")
    engine = AIPairingEngine()
    print(f"✓ Engine object created: {type(engine).__name__}")
    print(f"✓ Engine ID: {id(engine)}")
    print(f"✓ vertex_client value: {engine.vertex_client}")
    print(f"✓ vertex_client type: {type(engine.vertex_client)}")
    print(f"✓ vertex_client is None: {engine.vertex_client is None}")
    
    log_step(2, "Preparing to call select_best_combinations with EMPTY tokens")
    american_tokens = []
    italian_tokens = []
    num_combinations = 5
    
    print(f"✓ american_tokens: {american_tokens} (length: {len(american_tokens)})")
    print(f"✓ italian_tokens: {italian_tokens} (length: {len(italian_tokens)})")
    print(f"✓ num_combinations: {num_combinations}")
    print(f"✓ bool(american_tokens): {bool(american_tokens)}")
    print(f"✓ bool(italian_tokens): {bool(italian_tokens)}")
    print(f"✓ 'not american_tokens': {not american_tokens}")
    print(f"✓ 'not italian_tokens': {not italian_tokens}")
    print(f"✓ 'not american_tokens or not italian_tokens': {not american_tokens or not italian_tokens}")
    
    log_step(3, "BEFORE CALL - Checking state")
    print(f"✓ vertex_client before call: {engine.vertex_client}")
    print(f"✓ vertex_client is None: {engine.vertex_client is None}")
    
    # Check if initialize method exists
    print(f"✓ hasattr(engine, 'initialize'): {hasattr(engine, 'initialize')}")
    if hasattr(engine, 'initialize'):
        print(f"✓ initialize method: {engine.initialize}")
    
    log_step(4, "CALLING select_best_combinations([], [], 5)")
    print("Executing: results = await engine.select_best_combinations([], [], 5)")
    
    try:
        results = await engine.select_best_combinations(american_tokens, italian_tokens, num_combinations)
        print("✓ Call completed without exception")
    except Exception as e:
        print(f"✗ EXCEPTION RAISED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    log_step(5, "AFTER CALL - Checking results and state")
    print(f"✓ Results returned: {results}")
    print(f"✓ Results type: {type(results)}")
    print(f"✓ Results length: {len(results)}")
    print(f"✓ Results == []: {results == []}")
    print(f"✓ Results is []: {results is []}")
    print(f"✓ vertex_client after call: {engine.vertex_client}")
    print(f"✓ vertex_client is None: {engine.vertex_client is None}")
    print(f"✓ vertex_client type: {type(engine.vertex_client)}")
    
    log_step(6, "VERIFICATION")
    checks = {
        "Returns empty list": results == [],
        "Results is list type": isinstance(results, list),
        "Results length is 0": len(results) == 0,
        "vertex_client still None": engine.vertex_client is None,
    }
    
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check_name}: {result}")
    
    all_passed = all(checks.values())
    
    print(f"\n{'='*80}")
    if all_passed:
        print("✅ ALL CHECKS PASSED - CODE WORKS CORRECTLY")
    else:
        print("❌ SOME CHECKS FAILED - CODE HAS ISSUES")
    print(f"{'='*80}")
    
    # Read and show log file
    if log_file.exists():
        print(f"\n📄 LOG FILE CONTENTS ({log_file}):")
        print("-"*80)
        with open(log_file, 'r') as f:
            log_content = f.read()
            print(log_content[-2000:] if len(log_content) > 2000 else log_content)
        print("-"*80)
    
    return all_passed

async def test_real_execution_with_tokens():
    """Real execution test with actual tokens - NO MOCKS"""
    print("\n" + "🔬"*40)
    print("REAL EXECUTION TEST - WITH TOKENS")
    print("🔬"*40)
    
    log_step(1, "Creating AIPairingEngine instance")
    engine = AIPairingEngine()
    print(f"✓ vertex_client: {engine.vertex_client}")
    
    log_step(2, "Preparing tokens")
    american_tokens = [{"word": "iPhone", "pos": "NOUN"}]
    italian_tokens = [{"word": "mamma", "pos": "NOUN"}]
    
    print(f"✓ american_tokens: {american_tokens}")
    print(f"✓ italian_tokens: {italian_tokens}")
    print(f"✓ 'not american_tokens or not italian_tokens': {not american_tokens or not italian_tokens}")
    
    log_step(3, "BEFORE CALL")
    print(f"✓ vertex_client: {engine.vertex_client}")
    
    log_step(4, "CALLING select_best_combinations with tokens")
    try:
        results = await engine.select_best_combinations(american_tokens, italian_tokens, 1)
        print(f"✓ Call completed")
        print(f"✓ Results: {results}")
        print(f"✓ Results type: {type(results)}")
        print(f"✓ Results length: {len(results)}")
        print(f"✓ vertex_client after: {type(engine.vertex_client).__name__ if engine.vertex_client else None}")
    except Exception as e:
        print(f"✗ EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

async def main():
    print(f"\n{'='*80}")
    print("REAL EXECUTION TEST SUITE")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*80}")
    
    # Test 1: Empty tokens
    result1 = await test_real_execution_empty_tokens()
    
    # Test 2: With tokens (may fail due to credentials, but shows behavior)
    await test_real_execution_with_tokens()
    
    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"Empty tokens test: {'✅ PASSED' if result1 else '❌ FAILED'}")
    print(f"\nCheck log file: tests/brainrot_execution_log.txt")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(main())

