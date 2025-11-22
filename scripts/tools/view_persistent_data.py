#!/usr/bin/env python3
"""
Simple script to view persistent RDF data from the Knowledge Graph
"""
import asyncio
import json
from kg.models.graph_manager import KnowledgeGraphManager

async def view_persistent_data():
    print("🎯 VIEWING PERSISTENT RDF DATA")
    print("=" * 50)
    
    # Load persistent KG
    kg = KnowledgeGraphManager(persistent_storage=True)
    print(f"✅ Loaded {len(kg.graph)} triples from persistent storage")
    print(f"📁 Storage file: {kg._persistent_file}")
    print()
    
    # 1. Task Status Overview
    print("📊 1. TASK STATUS OVERVIEW")
    print("-" * 30)
    status_query = '''
    PREFIX : <http://example.org/core#>
    
    SELECT ?status (COUNT(?status) AS ?count) WHERE {
      ?toolCall :relatedTo ?task ; :name "mj.import_job" .
      ?task :status ?status .
    }
    GROUP BY ?status ORDER BY DESC(?count)
    '''
    
    try:
        status_results = await kg.query_graph(status_query)
        for result in status_results:
            print(f"   • {result.get('status', 'unknown')}: {result.get('count', 0)} tasks")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # 2. Recent Activity
    print("🕒 2. RECENT ACTIVITY (Last 5)")
    print("-" * 30)
    recent_query = '''
    PREFIX : <http://example.org/core#>
    
    SELECT ?taskId ?timestamp ?status WHERE {
      ?toolCall :relatedTo ?task ; :name "mj.import_job" ; :timestamp ?timestamp .
      ?task :status ?status .
      BIND(REPLACE(STR(?task), ".*Task/", "") AS ?taskId)
    }
    ORDER BY DESC(?timestamp)
    LIMIT 5
    '''
    
    try:
        recent_results = await kg.query_graph(recent_query)
        for i, result in enumerate(recent_results, 1):
            task_id = result.get('taskId', 'unknown')[:12]
            status = result.get('status', 'unknown')
            timestamp = result.get('timestamp', 'unknown')
            print(f"   {i}. {task_id}... - {status} at {timestamp}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # 3. Sample Tool Call Details
    print("🔧 3. SAMPLE TOOL CALL DETAILS")
    print("-" * 30)
    detail_query = '''
    PREFIX : <http://example.org/core#>
    PREFIX ns1: <http://example.org/midjourney#>
    
    SELECT ?taskId ?toolCall WHERE {
      ?toolCall :relatedTo ?task ; :name "mj.import_job" .
      BIND(REPLACE(STR(?task), ".*Task/", "") AS ?taskId)
    }
    LIMIT 3
    '''
    
    try:
        detail_results = await kg.query_graph(detail_query)
        for i, result in enumerate(detail_results, 1):
            task_id = result.get('taskId', 'unknown')[:12]
            tool_call = result.get('toolCall', 'unknown').split('/')[-1]
            print(f"   {i}. Task: {task_id}... Tool: {tool_call}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    print("🎉 PERSISTENT DATA VIEW COMPLETE!")
    print("   • Data survives server restarts")
    print("   • Real-time queries supported")
    print("   • Rich temporal tracking available")

if __name__ == "__main__":
    asyncio.run(view_persistent_data())
