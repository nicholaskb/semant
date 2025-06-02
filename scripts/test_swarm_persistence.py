#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from kg.models.graph_manager import KnowledgeGraphManager
from loguru import logger

async def test_persistence():
    """Test that swarm ontology data persists across graph manager instances."""
    try:
        # First instance - load and verify data
        logger.info("Testing data persistence...")
        graph_manager1 = KnowledgeGraphManager()
        
        # Load swarm ontology
        ontology_path = project_root / "kg" / "schemas" / "swarm_ontology.ttl"
        logger.info("Loading swarm ontology into first instance...")
        await graph_manager1.import_graph(ontology_path.read_text(), format='turtle')
        
        # Verify initial data
        results = await graph_manager1.query_graph("""
            SELECT (COUNT(?agent) as ?agentCount) 
                   (COUNT(?role) as ?roleCount)
                   (COUNT(?capability) as ?capabilityCount)
            WHERE {
                { ?agent rdf:type ?type . 
                  FILTER(?type IN (swarm:HumanAgent, swarm:SoftwareAgent)) }
                UNION
                { ?role rdf:type swarm:Role }
                UNION
                { ?capability rdf:type swarm:Capability }
            }
        """)
        
        initial_counts = results[0]
        logger.info("\nInitial data counts:")
        logger.info(f"Agents: {initial_counts['agentCount']}")
        logger.info(f"Roles: {initial_counts['roleCount']}")
        logger.info(f"Capabilities: {initial_counts['capabilityCount']}")
        
        # Export the graph
        exported_data = await graph_manager1.export_graph(format='turtle')
        await graph_manager1.shutdown()
        
        # Second instance - load exported data and verify
        logger.info("\nCreating second instance and loading exported data...")
        graph_manager2 = KnowledgeGraphManager()
        await graph_manager2.import_graph(exported_data, format='turtle')
        
        # Verify data in second instance
        results = await graph_manager2.query_graph("""
            SELECT (COUNT(?agent) as ?agentCount) 
                   (COUNT(?role) as ?roleCount)
                   (COUNT(?capability) as ?capabilityCount)
            WHERE {
                { ?agent rdf:type ?type . 
                  FILTER(?type IN (swarm:HumanAgent, swarm:SoftwareAgent)) }
                UNION
                { ?role rdf:type swarm:Role }
                UNION
                { ?capability rdf:type swarm:Capability }
            }
        """)
        
        final_counts = results[0]
        logger.info("\nFinal data counts:")
        logger.info(f"Agents: {final_counts['agentCount']}")
        logger.info(f"Roles: {final_counts['roleCount']}")
        logger.info(f"Capabilities: {final_counts['capabilityCount']}")
        
        # Verify counts match
        assert initial_counts['agentCount'] == final_counts['agentCount'], "Agent count mismatch"
        assert initial_counts['roleCount'] == final_counts['roleCount'], "Role count mismatch"
        assert initial_counts['capabilityCount'] == final_counts['capabilityCount'], "Capability count mismatch"
        
        # Verify specific relationships
        logger.info("\nVerifying specific relationships...")
        
        # Check agent roles
        results = await graph_manager2.query_graph("""
            SELECT ?agent ?role WHERE {
                ?agent swarm:hasRole ?role .
            }
        """)
        logger.info(f"Found {len(results)} agent-role relationships")
        
        # Check workflow tasks
        results = await graph_manager2.query_graph("""
            SELECT ?workflow ?task WHERE {
                ?workflow swarm:hasTask ?task .
            }
        """)
        logger.info(f"Found {len(results)} workflow-task relationships")
        
        # Check event triggers
        results = await graph_manager2.query_graph("""
            SELECT ?event ?workflow WHERE {
                ?event swarm:triggers ?workflow .
            }
        """)
        logger.info(f"Found {len(results)} event-workflow relationships")
        
        logger.info("\nPersistence test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error testing persistence: {str(e)}")
        raise
    finally:
        if 'graph_manager2' in locals():
            await graph_manager2.shutdown()

if __name__ == "__main__":
    asyncio.run(test_persistence()) 