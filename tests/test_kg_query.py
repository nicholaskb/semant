import asyncio
from kg.models.graph_manager import KnowledgeGraphManager

async def test():
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    # Query all tasks
    query = """
    PREFIX core: <http://example.org/core#>
    SELECT ?task ?status ?assigned WHERE {
        ?task a core:Task ;
              core:status ?status .
        OPTIONAL { ?task core:assignedTo ?assigned }
    }
    ORDER BY DESC(?task)
    LIMIT 5
    """
    
    results = await kg.query_graph(query)
    print(f"Found {len(results)} tasks:")
    for r in results:
        print(f"  Task: {r['task'].split('/')[-1][:8]}...")
        print(f"    Status: {r['status']}")
        print(f"    Assigned: {r.get('assigned', 'None')}")
        
asyncio.run(test())
