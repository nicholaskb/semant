import asyncio
from kg.models.graph_manager import KnowledgeGraphManager
from kg.models.graph_initializer import GraphInitializer

async def run_queries():
    # Initialize graph manager and load data
    graph_manager = KnowledgeGraphManager()
    initializer = GraphInitializer(graph_manager)
    
    # Load ontology and sample data
    await initializer.initialize_graph(
        'kg/schemas/core.ttl',
        'kg/schemas/sample_data.ttl'
    )
    
    # Query 1: Get all machines and their status
    print("\n1. Querying Machine Status:")
    results = await graph_manager.query_graph("""
        SELECT ?machine ?status WHERE {
            ?machine rdf:type <http://example.org/core#Machine> ;
                    <http://example.org/core#hasStatus> ?status .
        }
    """)
    for r in results:
        print(f"Machine: {r['machine']}, Status: {r['status']}")
    
    # Query 2: Get all sensors and their readings
    print("\n2. Querying Sensor Readings:")
    results = await graph_manager.query_graph("""
        SELECT ?sensor ?reading WHERE {
            ?sensor <http://example.org/core#latestReading> ?reading .
        }
    """)
    for r in results:
        print(f"Sensor: {r['sensor']}, Reading: {r['reading']}")
    
    # Query 3: Get machines with their attached sensors
    print("\n3. Querying Machines and Their Sensors:")
    results = await graph_manager.query_graph("""
        SELECT ?machine ?sensor WHERE {
            ?sensor <http://example.org/core#attachedTo> ?machine .
        }
    """)
    for r in results:
        print(f"Machine: {r['machine']}, Sensor: {r['sensor']}")
    
    # Query 4: Complex query with FILTER and OPTIONAL
    print("\n4. Complex Query: Machines with High Sensor Readings:")
    results = await graph_manager.query_graph("""
        SELECT ?machine ?sensor ?reading ?status WHERE {
            ?sensor <http://example.org/core#attachedTo> ?machine ;
                   <http://example.org/core#latestReading> ?reading .
            ?machine <http://example.org/core#hasStatus> ?status .
            FILTER(?reading > 50)
        }
    """)
    for r in results:
        print(f"Machine: {r['machine']}, Sensor: {r['sensor']}, Reading: {r['reading']}, Status: {r['status']}")
    
    # Query 5: Using UNION to find both machines and sensors
    print("\n5. UNION Query: All Machines and Sensors:")
    results = await graph_manager.query_graph("""
        SELECT ?entity ?type WHERE {
            {
                ?entity rdf:type <http://example.org/core#Machine> .
                BIND("Machine" as ?type)
            } UNION {
                ?entity rdf:type <http://example.org/core#Sensor> .
                BIND("Sensor" as ?type)
            }
        }
    """)
    for r in results:
        print(f"Entity: {r['entity']}, Type: {r['type']}")
    
    # Query 6: Using OPTIONAL to find machines with or without sensors
    print("\n6. OPTIONAL Query: Machines with Optional Sensor Info:")
    results = await graph_manager.query_graph("""
        SELECT ?machine ?status ?sensor ?reading WHERE {
            ?machine rdf:type <http://example.org/core#Machine> ;
                    <http://example.org/core#hasStatus> ?status .
            OPTIONAL {
                ?sensor <http://example.org/core#attachedTo> ?machine ;
                       <http://example.org/core#latestReading> ?reading .
            }
        }
    """)
    for r in results:
        sensor_info = f", Sensor: {r['sensor']}, Reading: {r['reading']}" if r.get('sensor') else ""
        print(f"Machine: {r['machine']}, Status: {r['status']}{sensor_info}")
    
    # Query 7: Using GROUP BY and aggregation
    print("\n7. Aggregation Query: Average Reading per Machine:")
    results = await graph_manager.query_graph("""
        SELECT ?machine (AVG(?reading) as ?avg_reading) WHERE {
            ?sensor <http://example.org/core#attachedTo> ?machine ;
                   <http://example.org/core#latestReading> ?reading .
        }
        GROUP BY ?machine
    """)
    for r in results:
        print(f"Machine: {r['machine']}, Average Reading: {r['avg_reading']}")
    
    # Query 8: Using FILTER with regex
    print("\n8. Regex Query: Find entities with specific patterns:")
    results = await graph_manager.query_graph("""
        SELECT ?entity ?type WHERE {
            ?entity rdf:type ?type .
            FILTER(REGEX(str(?entity), "Machine"))
        }
    """)
    for r in results:
        print(f"Entity: {r['entity']}, Type: {r['type']}")
    
    # Query 9: Get validation statistics
    print("\n9. Graph Validation Statistics:")
    validation = await graph_manager.validate_graph()
    print(f"Total triples: {validation['triple_count']}")
    print(f"Unique subjects: {validation['subjects']}")
    print(f"Unique predicates: {validation['predicates']}")
    print(f"Unique objects: {validation['objects']}")

if __name__ == "__main__":
    asyncio.run(run_queries()) 