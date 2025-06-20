import asyncio
from kg.models.graph_manager import KnowledgeGraphManager

async def test_query():
    # Initialize the knowledge graph manager
    kg = KnowledgeGraphManager()
    
    # Add 100 test agents
    print("Adding 100 test agents...")
    for i in range(100):
        await kg.add_triple(
            f"http://example.org/core#Agent{i}",
            "http://example.org/core#hasStatus",
            "idle"
        )
        await kg.add_triple(
            f"http://example.org/core#Agent{i}",
            "http://example.org/core#hasCapability",
            f"capability_{i%5}"
        )
    
    # Query to get all triples
    query = """
    SELECT ?subject ?predicate ?object WHERE {
        ?subject ?predicate ?object .
    }
    """
    
    # Execute the query
    results = await kg.query_graph(query)
    
    # Print results
    print(f"\nFound {len(results)} triples in the graph:")
    for result in results:
        print(f"Subject: {result['subject']}")
        print(f"Predicate: {result['predicate']}")
        print(f"Object: {result['object']}")
        print("---")

if __name__ == "__main__":
    asyncio.run(test_query()) 