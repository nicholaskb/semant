import asyncio
from rdflib import Graph, Namespace, Literal, URIRef
from agents.core.reasoner import KnowledgeGraphReasoner

def setup_demo_graph():
    """Create a demo knowledge graph with sample research data."""
    g = Graph()
    # Define namespaces
    dMaster = Namespace("http://example.org/dMaster/")
    g.bind("dMaster", dMaster)
    
    # Sample research papers
    papers = [
        {
            "id": "paper1",
            "title": "AI in Healthcare: Current Trends",
            "author": "Prof. James Wilson",
            "year": 2023,
            "topic": "ai healthcare",
            "insights": "AI can improve diagnosis accuracy by 30%."
        },
        {
            "id": "paper2",
            "title": "Blockchain in Supply Chain: Current State and Future Directions",
            "author": "Dr. Sarah Lee",
            "year": 2024,
            "topic": "blockchain supply chain",
            "insights": "Blockchain reduces fraud by 40% in supply chains."
        }
    ]
    
    # Add papers to graph
    for paper in papers:
        paper_uri = dMaster[paper["id"]]
        g.add((paper_uri, dMaster.title, Literal(paper["title"])))
        g.add((paper_uri, dMaster.author, Literal(paper["author"])))
        g.add((paper_uri, dMaster.year, Literal(paper["year"])))
        g.add((paper_uri, dMaster.topic, Literal(paper["topic"])))
        g.add((paper_uri, dMaster.insights, Literal(paper["insights"])))
    
    return g

async def run_demo():
    """Run the research investigation demo."""
    print("\n=== Research Investigation Demo ===\n")
    
    # Setup the knowledge graph
    print("Setting up demo knowledge graph...")
    graph = setup_demo_graph()
    reasoner = KnowledgeGraphReasoner(graph)
    
    # Demo 1: Investigate ai healthcare (lowercase, matches data)
    print("\n1. Investigating 'ai healthcare'...")
    findings = await reasoner.investigate_research_topic("ai healthcare")
    print(f"\nFindings for 'ai healthcare':")
    print(f"- Confidence Score: {findings['confidence']:.2f}")
    print("\nKey Insights:")
    for insight in findings['key_insights']:
        print(f"- {insight}")
    print("\nRelated Papers:")
    for paper in findings['sources']:
        print(f"- {paper['title']} ({paper['year']}) by {paper['author']}")
    print("\nRelated Concepts (from diary entries):")
    for entry in findings['related_concepts']:
        print(f"- {entry['agent']} at {entry['timestamp']}: {entry['message']}")
    
    # Demo 2: Traverse Knowledge Graph
    print("\n2. Traversing Knowledge Graph...")
    traversal = await reasoner.traverse_knowledge_graph(
        "http://example.org/dMaster/paper1",
        max_depth=2
    )
    print("\nGraph Traversal Results:")
    print(f"Starting from: {traversal['start_node']}")
    print(f"Depth: {traversal['depth']}")
    print("\nPaths found:")
    for path in traversal['paths']:
        print(f"- {path['from']} --[{path['relationship']}]--> {path['to']}")
    
    # Demo 3: Find Related Concepts
    print("\n3. Finding Related Concepts...")
    concepts = await reasoner.find_related_concepts(
        "http://example.org/dMaster/paper1",
        similarity_threshold=0.7
    )
    print("\nRelated Concepts:")
    for concept in concepts:
        print(f"- {concept['concept']} (similarity: {concept['similarity']:.2f})")
    
    print("\n=== Demo Complete ===")

if __name__ == "__main__":
    asyncio.run(run_demo()) 