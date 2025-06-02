import asyncio
from kg.models.graph_manager import KnowledgeGraphManager
from loguru import logger

async def diagnose_agent_capabilities():
    """Diagnose agent capabilities using knowledge graph queries."""
    logger.info("Initializing knowledge graph...")
    kg = KnowledgeGraphManager()
    kg.initialize_namespaces()
    
    # Query 1: Get all agents and their capabilities
    logger.info("Querying agent capabilities...")
    agent_capabilities_query = """
    PREFIX core: <http://example.org/core#>
    SELECT ?agent ?capability WHERE {
        ?agent a core:Agent ;
               core:hasCapability ?capability .
    }
    """
    results = await kg.query_graph(agent_capabilities_query)
    logger.info(f"Found {len(results)} agent-capability pairs")
    
    # Query 2: Get capability distribution
    logger.info("Analyzing capability distribution...")
    capability_dist_query = """
    PREFIX core: <http://example.org/core#>
    SELECT ?capability (COUNT(?agent) as ?count) WHERE {
        ?agent a core:Agent ;
               core:hasCapability ?capability .
    }
    GROUP BY ?capability
    """
    dist_results = await kg.query_graph(capability_dist_query)
    logger.info("Capability distribution:")
    for result in dist_results:
        logger.info(f"Capability: {result['capability']}, Count: {result['count']}")
    
    # Query 3: Find agents with missing required capabilities
    logger.info("Checking for missing required capabilities...")
    required_capabilities = [
        "http://example.org/core#CAP_A",
        "http://example.org/core#CAP_B",
        "http://example.org/core#CAP_C"
    ]
    
    missing_caps_query = """
    PREFIX core: <http://example.org/core#>
    SELECT ?agent ?required_cap WHERE {
        VALUES ?required_cap { %s }
        ?agent a core:Agent .
        FILTER NOT EXISTS {
            ?agent core:hasCapability ?cap .
            ?cap core:type ?required_cap .
        }
    }
    """ % " ".join(f"<{cap}>" for cap in required_capabilities)
    
    missing_results = await kg.query_graph(missing_caps_query)
    logger.info(f"Found {len(missing_results)} missing capability instances")
    
    # Query 4: Check for capability conflicts
    logger.info("Checking for capability conflicts...")
    conflict_query = """
    PREFIX core: <http://example.org/core#>
    SELECT ?capability ?agent1 ?agent2 WHERE {
        ?agent1 a core:Agent ;
                core:hasCapability ?cap1 .
        ?agent2 a core:Agent ;
                core:hasCapability ?cap2 .
        ?cap1 core:type ?capability .
        ?cap2 core:type ?capability .
        FILTER(?agent1 != ?agent2)
    }
    """
    conflict_results = await kg.query_graph(conflict_query)
    logger.info(f"Found {len(conflict_results)} potential capability conflicts")
    
    return {
        "agent_capabilities": results,
        "capability_distribution": dist_results,
        "missing_capabilities": missing_results,
        "capability_conflicts": conflict_results
    }

async def main():
    """Run the diagnosis."""
    try:
        results = await diagnose_agent_capabilities()
        logger.info("Diagnosis complete!")
        return results
    except Exception as e:
        logger.error(f"Error during diagnosis: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 