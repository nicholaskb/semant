import asyncio
from kg.models.graph_manager import KnowledgeGraphManager
from loguru import logger
from agents.core.capability_types import Capability, CapabilityType

async def load_sample_data():
    """Load sample data into the knowledge graph."""
    kg = KnowledgeGraphManager()
    kg.initialize_namespaces()
    logger.info("Initializing knowledge graph...")
    
    try:
        # Add sample agent
        agent_uri = "http://example.org/core#Agent1"
        logger.info(f"Adding sample agent: {agent_uri}")
        
        # Add agent type
        await kg.add_triple(
            agent_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/core#Agent"
        )
        
        # Add sample capabilities
        capabilities = [
            ("http://example.org/core#CAP_A", "1.0"),
            ("http://example.org/core#CAP_B", "1.0")
        ]
        
        logger.info("Adding sample capabilities...")
        for cap_uri, version in capabilities:
            # Add capability type
            await kg.add_triple(
                cap_uri,
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                "http://example.org/core#Capability"
            )
            
            # Add capability version
            await kg.add_triple(
                cap_uri,
                "http://example.org/core#hasVersion",
                version
            )
            
            # Link capability to agent
            await kg.add_triple(
                agent_uri,
                "http://example.org/core#hasCapability",
                cap_uri
            )
            
            logger.info(f"Added capability {cap_uri} with version {version}")
        
        # Verify data
        logger.info("Verifying data...")
        results = await kg.query_graph("""
            SELECT ?agent ?capability ?version WHERE {
                ?agent rdf:type <http://example.org/core#Agent> .
                ?agent <http://example.org/core#hasCapability> ?capability .
                ?capability <http://example.org/core#hasVersion> ?version .
            }
        """)
        
        logger.info(f"Found {len(results)} capability records:")
        for result in results:
            logger.info(f"Agent: {result['agent']}")
            logger.info(f"Capability: {result['capability']}")
            logger.info(f"Version: {result['version']}")
            
    except Exception as e:
        logger.error(f"Error loading sample data: {str(e)}")
        raise

async def main():
    try:
        await load_sample_data()
        logger.info("Sample data loading complete!")
    except Exception as e:
        logger.error(f"Failed to load sample data: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 