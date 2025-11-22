#!/usr/bin/env python3
"""
Comparison: What happens WITH vs WITHOUT the mock client
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.brainrot.ai_pairing import AIPairingEngine
from unittest.mock import AsyncMock

async def test_with_mock():
    """Test WITH mock client (current test approach)"""
    print("\n" + "="*70)
    print("TEST 1: WITH Mock Client (Current Test Approach)")
    print("="*70)
    
    engine = AIPairingEngine()
    mock_client = AsyncMock()
    engine.vertex_client = mock_client
    
    print(f"\nvertex_client before call: {type(engine.vertex_client).__name__}")
    print("Calling with empty tokens...")
    
    results = await engine.select_best_combinations([], [], num_combinations=5)
    
    print(f"Results: {results}")
    print(f"Mock initialize() called? {mock_client.initialize.called if hasattr(mock_client, 'initialize') else 'N/A'}")
    print("✅ SUCCESS: Returns [] without calling initialize()")

async def test_without_mock():
    """Test WITHOUT mock client (would fail)"""
    print("\n" + "="*70)
    print("TEST 2: WITHOUT Mock Client (Would Try to Initialize)")
    print("="*70)
    
    engine = AIPairingEngine()
    
    print(f"\nvertex_client before call: {engine.vertex_client}")
    print("Calling with empty tokens...")
    print("⚠️  This would try to call await self.initialize()")
    print("⚠️  Which would try to connect to Vertex AI (needs credentials)")
    
    try:
        # This would fail if credentials aren't available
        results = await engine.select_best_combinations([], [], num_combinations=5)
        print(f"Results: {results}")
        print("✅ Still works, but would have tried to initialize Vertex AI")
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        print("   This is why we use a mock - to avoid needing real credentials")

async def main():
    await test_with_mock()
    print("\n")
    await test_without_mock()
    print("\n" + "="*70)
    print("SUMMARY:")
    print("="*70)
    print("WITH mock:    ✅ Fast, no external calls, tests logic only")
    print("WITHOUT mock: ⚠️  Slow, needs credentials, tests integration")
    print("\nThe test uses mock to test the LOGIC (empty check) without")
    print("needing actual Vertex AI credentials or making real API calls.")
    print()

if __name__ == "__main__":
    asyncio.run(main())

