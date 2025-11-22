import asyncio
from agents.domain.test_swarm_coordinator import TestSwarmCoordinator
from kg.models.graph_manager import KnowledgeGraphManager
from loguru import logger
import os
import json
from datetime import datetime

async def main():
    kg = None
    try:
        # Initialize knowledge graph
        kg = KnowledgeGraphManager()
        await kg.initialize()
        
        # Initialize test swarm coordinator
        config = {
            'consensus_threshold': 0.75,
            'min_reviewers': 2
        }
        coordinator = TestSwarmCoordinator(config=config)
        coordinator.knowledge_graph = kg
        await coordinator.initialize()
        
        # Directory containing tests
        test_dir = "tests"
        
        print(f"\n{'='*50}")
        print(f"Starting test fix swarm at {datetime.now().isoformat()}")
        print(f"Test directory: {test_dir}")
        print(f"{'='*50}\n")
        
        try:
            # Start fixing tests
            result = await coordinator.fix_all_tests(test_dir)
            
            # Print results
            print(f"\n{'='*50}")
            print("Test Fix Results:")
            print(f"{'='*50}")
            
            progress = result['progress']
            print(f"\nProgress:")
            print(f"- Total tests: {progress['total_tests']}")
            print(f"- Fixed tests: {progress['fixed_tests']}")
            print(f"- Failed tests: {progress['failed_tests']}")
            print(f"- Start time: {progress['start_time']}")
            print(f"- End time: {progress['end_time']}")
            
            # Print detailed results
            print(f"\nDetailed Results:")
            for test_result in result['results']:
                if isinstance(test_result, Exception):
                    print(f"- Error: {str(test_result)}")
                else:
                    print(f"- File: {test_result['file']}")
                    print(f"  Status: {test_result['status']}")
                    if test_result['status'] == 'error':
                        print(f"  Error: {test_result['error']}")
                    elif test_result['status'] == 'needs_fix':
                        print("  Review findings:")
                        for finding in test_result['review']['findings']:
                            print(f"    - [{finding['severity'].upper()}] {finding['message']}")
                            if 'recommendation' in finding:
                                print(f"      Recommendation: {finding['recommendation']}")
            
            # Query knowledge graph for final progress
            print(f"\nKnowledge Graph Progress:")
            sparql = """
            SELECT ?p ?o WHERE {
                swarm:test_fix_progress ?p ?o .
            }
            """
            kg_result = await kg.query_graph(sparql)
            for row in kg_result:
                print(f"- {row['p']}: {row['o']}")
                
        except Exception as e:
            print(f"\nError running test swarm: {str(e)}")
            logger.exception("Test swarm error")
    finally:
        if kg:
            await kg.shutdown()
        
if __name__ == "__main__":
    asyncio.run(main()) 