#!/usr/bin/env python3
"""Quick test to verify API connection."""
import asyncio
import httpx
import sys

async def test():
    url = "http://localhost:8000"
    print(f"Testing connection to {url}...")
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Test docs endpoint (most reliable)
        try:
            response = await client.get(f"{url}/docs")
            print(f"✓ /docs returned: {response.status_code}")
            if response.status_code == 200:
                print("✅ API server is running!")
                return True
        except httpx.ConnectError as e:
            print(f"✗ Connection error: {e}")
            return False
        except Exception as e:
            print(f"✗ Error: {e}")
            return False
    
    return False

if __name__ == "__main__":
    result = asyncio.run(test())
    sys.exit(0 if result else 1)

