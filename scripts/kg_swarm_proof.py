import asyncio
from kg.models.graph_manager import KnowledgeGraphManager
from loguru import logger

def print_section(title):
    print("\n" + "="*len(title))
    print(title)
    print("="*len(title))

async def load_sample_data(kg):
    """Load sample data into the knowledge graph."""
    logger.info("Loading sample data...")
    # Add sample agent
    agent_uri = "http://example.org/core#Agent1"
    await kg.add_triple(agent_uri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/core#Agent")
    logger.info(f"Added sample agent: {agent_uri}")
    # Add sample capabilities
    capabilities = [
        ("http://example.org/core#CAP_A", "1.0"),
        ("http://example.org/core#CAP_B", "1.0")
    ]
    for cap_uri, version in capabilities:
        await kg.add_triple(cap_uri, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "http://example.org/core#Capability")
        await kg.add_triple(agent_uri, "http://example.org/core#hasCapability", cap_uri)
        await kg.add_triple(cap_uri, "http://example.org/core#hasVersion", version)
        logger.info(f"Added capability {cap_uri} with version {version}")
    logger.info("Sample data loading complete!")

async def run_diagnostic_queries(kg):
    """Run all diagnostic queries on the knowledge graph."""
    # 0. Raw triple inspection
    print_section("0. All Triples in the Graph (Raw Inspection)")
    q0 = '''SELECT ?s ?p ?o WHERE { ?s ?p ?o }'''
    results = await kg.query_graph(q0)
    if results:
        for r in results:
            print(f"s: {r['s']}")
            print(f"p: {r['p']}")
            print(f"o: {r['o']}")
            print("---")
    else:
        print("No triples found in the graph.")

    # 1. Agent-Capability Relationships
    print_section("1. Agents and Their Capabilities")
    q1 = '''
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX core: <http://example.org/core#>
    SELECT ?agent ?capability WHERE {
      ?agent rdf:type core:Agent .
      ?agent core:hasCapability ?capability .
    }
    '''
    results = await kg.query_graph(q1)
    if results:
        for r in results:
            print(f"Agent: {r['agent']}")
            print(f"Capability: {r['capability']}")
    else:
        print("No agents with capabilities found.")

    # 2. Empty Capability Detection
    print_section("2. Agents with No Capabilities")
    q2 = '''
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX core: <http://example.org/core#>
    SELECT ?agent WHERE {
      ?agent rdf:type core:Agent .
      FILTER NOT EXISTS { ?agent core:hasCapability ?capability }
    }
    '''
    results = await kg.query_graph(q2)
    if results:
        for r in results:
            print(f"Agent with no capabilities: {r['agent']}")
    else:
        print("All agents have at least one capability.")

    # 3. Capability Type Validation
    print_section("3. Capabilities with Wrong Type")
    q3 = '''
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX core: <http://example.org/core#>
    SELECT ?capability WHERE {
      ?capability rdf:type ?type .
      FILTER(?type != core:Capability)
    }
    '''
    results = await kg.query_graph(q3)
    if results:
        for r in results:
            print(f"Capability with wrong type: {r['capability']}")
    else:
        print("All capabilities have correct type.")

    # 4. Duplicate Capability Check
    print_section("4. Duplicate Capability Assignments")
    q4 = '''
    PREFIX core: <http://example.org/core#>
    SELECT ?agent ?capability (COUNT(?capability) AS ?count) WHERE {
      ?agent core:hasCapability ?capability .
    }
    GROUP BY ?agent ?capability
    HAVING (?count > 1)
    '''
    results = await kg.query_graph(q4)
    if results:
        for r in results:
            print(f"Duplicate capability assignment: Agent {r['agent']}, Capability {r['capability']}, Count: {r['count']}")
    else:
        print("No duplicate capability assignments found.")

    # 5. Event Propagation Check
    print_section("5. Capability Change Events")
    q5 = '''
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX core: <http://example.org/core#>
    SELECT ?event ?agent ?capability WHERE {
      ?event rdf:type core:CapabilityChangeEvent .
      ?event core:affectedAgent ?agent .
      ?event core:affectedCapability ?capability .
    }
    '''
    results = await kg.query_graph(q5)
    if results:
        for r in results:
            print(f"Event: {r['event']}")
            print(f"Affected Agent: {r['agent']}")
            print(f"Affected Capability: {r['capability']}")
    else:
        print("No capability change events found.")

async def main():
    """Main function to load sample data and run diagnostic queries."""
    kg = KnowledgeGraphManager()
    kg.initialize_namespaces()
    await load_sample_data(kg)
    await run_diagnostic_queries(kg)

if __name__ == "__main__":
    asyncio.run(main()) 