import asyncio
from agents.domain.code_review_agent import CodeReviewAgent
from loguru import logger
import json
from kg.models.graph_manager import KnowledgeGraphManager

async def main():
    # Initialize the knowledge graph
    kg = KnowledgeGraphManager()
    await kg.initialize()
    
    # Initialize the code review agent with default configuration and knowledge graph
    config = {
        'consensus_threshold': 0.75,
        'min_reviewers': 2
    }
    agent = CodeReviewAgent(config=config)
    agent.knowledge_graph = kg
    await agent.initialize()
    
    # Example 1: Well-written code
    good_code = '''
def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.
    
    Args:
        n: The position in the Fibonacci sequence (0-based)
        
    Returns:
        The nth Fibonacci number
        
    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("Input must be non-negative")
    if n <= 1:
        return n
        
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
'''
    
    # Example 2: Code with issues
    problematic_code = '''
def processData(data):
    result = []
    for item in data:
        if item > 0:
            if item % 2 == 0:
                if item < 100:
                    if item not in result:
                        result.append(item)
    return result
'''
    
    # Example 3: Code with syntax error
    broken_code = '''
def broken_function(
    return 42
'''
    
    # Review each code example
    examples = [
        ("Good Code", good_code),
        ("Problematic Code", problematic_code),
        ("Broken Code", broken_code)
    ]
    
    for name, code in examples:
        print(f"\n{'='*50}")
        print(f"Reviewing {name}:")
        print(f"{'='*50}")
        review_id = name.lower().replace(' ', '_')
        try:
            result = await agent._perform_review({'code': code, 'id': review_id})
            
            if result.get('status') == 'error':
                print(f"\nError: {result.get('error')}")
                if result.get('recommendations'):
                    print("\nRecommendations:")
                    for rec in result['recommendations']:
                        print(f"- {rec}")
            else:
                # Print findings
                if result['findings']:
                    print("\nFindings:")
                    for finding in result['findings']:
                        print(f"- [{finding['severity'].upper()}] {finding['message']}")
                        print(f"  Location: {finding['location']}")
                        if 'recommendation' in finding:
                            print(f"  Recommendation: {finding['recommendation']}")
                else:
                    print("\nNo issues found!")
                    
                # Print metrics
                print("\nMetrics:")
                for metric, value in result['metrics'].items():
                    print(f"- {metric}: {value:.2f}")
                    
                # Print recommendations
                if result['recommendations']:
                    print("\nRecommendations:")
                    for rec in result['recommendations']:
                        print(f"- {rec}")
            # After review, show the review triple in the knowledge graph
            print("\nKnowledge Graph Review Triple:")
            sparql = f"""
            SELECT ?p ?o WHERE {{
                <review:{review_id}> ?p ?o .
            }}
            """
            kg_result = await kg.query_graph(sparql)
            for row in kg_result:
                print(f"- {row['p']}: {row['o']}")
        except Exception as e:
            print(f"\nError during review: {str(e)}")
            
if __name__ == "__main__":
    asyncio.run(main()) 