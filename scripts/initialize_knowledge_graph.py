#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from kg.models.graph_initializer import GraphInitializer
from loguru import logger

async def main():
    """Initialize the knowledge graph with ontology and sample data."""
    try:
        # Create graph initializer
        initializer = GraphInitializer()
        
        # Get paths to ontology and sample data
        ontology_path = project_root / "kg" / "schemas" / "core.ttl"
        sample_data_path = project_root / "kg" / "schemas" / "sample_data.ttl"
        
        # Initialize the graph
        logger.info("Initializing knowledge graph...")
        await initializer.initialize_graph(
            str(ontology_path),
            str(sample_data_path)
        )
        
        # Export the graph to verify
        graph_data = await initializer.graph_manager.export_graph(format='turtle')
        logger.info("Graph initialized successfully. Sample of graph data:")
        logger.info("\n" + graph_data[:500] + "...\n")
        
        # Run some example queries
        logger.info("Running example queries...")
        
        # Query 1: List all machines and their status
        results = await initializer.graph_manager.query_graph("""
            SELECT ?machine ?status WHERE {
                ?machine rdf:type :Machine ;
                        :hasStatus ?status .
            }
        """)
        logger.info("\nMachines and their status:")
        for result in results:
            logger.info(f"{result['machine']}: {result['status']}")
            
        # Query 2: List all sensors and their readings
        results = await initializer.graph_manager.query_graph("""
            SELECT ?sensor ?reading WHERE {
                ?sensor rdf:type :Sensor ;
                        :latestReading ?reading .
            }
        """)
        logger.info("\nSensors and their readings:")
        for result in results:
            logger.info(f"{result['sensor']}: {result['reading']}")
            
        # Query 3: List all tasks and their status
        results = await initializer.graph_manager.query_graph("""
            SELECT ?task ?status WHERE {
                ?task rdf:type :Task ;
                      :hasStatus ?status .
            }
        """)
        logger.info("\nTasks and their status:")
        for result in results:
            logger.info(f"{result['task']}: {result['status']}")
            
    except Exception as e:
        logger.error(f"Error initializing knowledge graph: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 