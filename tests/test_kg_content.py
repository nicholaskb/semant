import asyncio
from kg.models.graph_manager import KnowledgeGraphManager

async def test():
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    # Query everything
    query = """
    SELECT ?s ?p ?o WHERE {
        ?s ?p ?o .
    }
    LIMIT 20
    """
    
    results = await kg.query_graph(query)
    print(f"Found {len(results)} triples:")
    for r in results:
        s = str(r['s']).split('/')[-1] if '/' in str(r['s']) else str(r['s'])
        p = str(r['p']).split('#')[-1] if '#' in str(r['p']) else str(r['p']).split('/')[-1]
        o = str(r['o'])[:50] if len(str(r['o'])) > 50 else str(r['o'])
        print(f"  {s} -- {p} --> {o}")
        
asyncio.run(test())
