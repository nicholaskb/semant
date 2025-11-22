#!/usr/bin/env python3
"""
Simple test of Midjourney + KG Integration
This version works with the existing infrastructure
"""
import asyncio
import os
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

async def test():
    print("🎯 MIDJOURNEY + KG SIMPLE TEST")
    print("=" * 60)
    
    # Check API token
    if not os.getenv('MIDJOURNEY_API_TOKEN'):
        print("❌ No API token")
        return
    print("✅ API token found")
    
    # Test 1: Midjourney client works
    from midjourney_integration.client import MidjourneyClient
    client = MidjourneyClient()
    print("✅ Midjourney client created")
    
    # Test 2: KG works
    from kg.models.graph_manager import KnowledgeGraphManager
    kg = KnowledgeGraphManager(persistent_storage=False)  # Use in-memory for testing
    await kg.initialize()
    print("✅ KG initialized (in-memory)")
    
    # Test 3: Add a simple triple
    await kg.add_triple(
        "http://example.org/test/task1",
        "http://example.org/test#type",
        "ImageGeneration"
    )
    print("✅ Added triple to KG")
    
    # Test 4: Query it back
    query = """
    SELECT ?s ?p ?o WHERE {
        ?s ?p ?o .
    }
    """
    results = await kg.query_graph(query)
    print(f"✅ Query returned {len(results)} results")
    
    # Test 5: Submit to Midjourney
    print("\n📸 Submitting to Midjourney...")
    result = await client.submit_imagine(
        prompt="a simple blue sphere",
        model_version="v6",
        aspect_ratio="1:1",
        process_mode="fast"
    )
    
    if result and result.get('data'):
        task_id = result['data'].get('task_id')
        print(f"✅ Submitted! Task ID: {task_id}")
        
        # Store in KG
        await kg.add_triple(
            f"http://example.org/midjourney/{task_id}",
            "http://example.org/midjourney#prompt",
            "a simple blue sphere"
        )
        await kg.add_triple(
            f"http://example.org/midjourney/{task_id}",
            "http://example.org/midjourney#status",
            "submitted"
        )
        print("✅ Stored in KG")
        
        # Query back
        mj_query = """
        PREFIX mj: <http://example.org/midjourney#>
        SELECT ?task ?prompt WHERE {
            ?task mj:prompt ?prompt .
        }
        """
        mj_results = await kg.query_graph(mj_query)
        print(f"✅ Found {len(mj_results)} Midjourney tasks in KG")
        
        if mj_results:
            for r in mj_results:
                print(f"   Task: {r['task'].split('/')[-1][:8]}...")
                print(f"   Prompt: {r['prompt']}")
                
        print("\n✨ Integration working!")
    else:
        print("❌ Failed to submit")
        
asyncio.run(test())
