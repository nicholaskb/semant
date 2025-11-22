import asyncio
from kg.models.graph_initializer import GraphInitializer

async def main():
    gi = GraphInitializer()
    await gi.initialize_graph('kg/schemas/core.ttl', 'kg/schemas/sample_data.ttl')
    q = '''PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\nSELECT ?type (COUNT(?s) AS ?count) WHERE { ?s rdf:type ?type . } GROUP BY ?type'''
    results = await gi.graph_manager.query_graph(q)
    print('TYPE COUNTS:')
    for row in results:
        print(row)

if __name__ == '__main__':
    asyncio.run(main()) 