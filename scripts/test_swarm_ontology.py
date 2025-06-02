#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from kg.models.graph_manager import KnowledgeGraphManager
from loguru import logger

async def main():
    """Test loading and querying the swarm ontology."""
    try:
        # Create graph manager
        graph_manager = KnowledgeGraphManager()
        
        # Load swarm ontology
        ontology_path = project_root / "kg" / "schemas" / "swarm_ontology.ttl"
        logger.info("Loading swarm ontology...")
        await graph_manager.import_graph(ontology_path.read_text(), format='turtle')
        
        # Test queries
        logger.info("\nTesting swarm ontology queries...")
        
        # Query 1: List all agents and their types
        results = await graph_manager.query_graph("""
            SELECT ?agent ?type WHERE {
                ?agent rdf:type ?type .
                FILTER(?type IN (swarm:HumanAgent, swarm:SoftwareAgent))
            }
        """)
        logger.info("\nAgents and their types:")
        for result in results:
            logger.info(f"{result['agent']}: {result['type']}")
            
        # Query 2: List agents with their roles and capabilities
        results = await graph_manager.query_graph("""
            SELECT ?agent ?role ?capability WHERE {
                ?agent swarm:hasRole ?role ;
                       swarm:hasCapability ?capability .
            }
        """)
        logger.info("\nAgents with roles and capabilities:")
        for result in results:
            logger.info(f"{result['agent']} - Role: {result['role']}, Capability: {result['capability']}")
            
        # Query 3: List workflows and their tasks
        results = await graph_manager.query_graph("""
            SELECT ?workflow ?task WHERE {
                ?workflow swarm:hasTask ?task .
            }
        """)
        logger.info("\nWorkflows and their tasks:")
        for result in results:
            logger.info(f"{result['workflow']} - Task: {result['task']}")
            
        # Query 4: List events and their triggered workflows
        results = await graph_manager.query_graph("""
            SELECT ?event ?workflow WHERE {
                ?event swarm:triggers ?workflow .
            }
        """)
        logger.info("\nEvents and their triggered workflows:")
        for result in results:
            logger.info(f"{result['event']} -> {result['workflow']}")
            
        # Query 5: List knowledge graph entities
        results = await graph_manager.query_graph("""
            SELECT ?entity WHERE {
                ex:SwarmKG swarm:containsEntity ?entity .
            }
        """)
        logger.info("\nKnowledge graph entities:")
        for result in results:
            logger.info(f"{result['entity']}")
            
    except Exception as e:
        logger.error(f"Error testing swarm ontology: {str(e)}")
        raise
    finally:
        await graph_manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main()) 