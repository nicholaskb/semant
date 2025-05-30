import asyncio
from rdflib import Graph, Namespace, Literal, URIRef
from agents.core.reasoner import KnowledgeGraphReasoner

async def setup_demo_graph():
    """Create a demo knowledge graph with sample research data."""
    graph = Graph()
    dm = Namespace('http://example.org/dMaster/')
    
    # Add research papers
    papers = [
        {
            'id': 'paper1',
            'title': 'AI in Healthcare: A Comprehensive Review',
            'author': 'Dr. Sarah Chen',
            'year': '2024',
            'topic': 'ai healthcare',
            'insights': [
                'AI can improve diagnosis accuracy by 30%',
                'Machine learning models show promise in early disease detection',
                'Data quality is critical for AI healthcare success'
            ]
        },
        {
            'id': 'paper2',
            'title': 'Blockchain in Supply Chain: Current State and Future Directions',
            'author': 'Prof. James Wilson',
            'year': '2023',
            'topic': 'blockchain supply chain',
            'insights': [
                'Blockchain can reduce supply chain costs by 20%',
                'Smart contracts improve transparency in logistics'
            ]
        },
        {
            'id': 'paper3',
            'title': 'AI for Medical Imaging',
            'author': 'Dr. Maria Rodriguez',
            'year': '2022',
            'topic': 'ai healthcare',
            'insights': [
                'AI can improve diagnosis accuracy by 30%',
                'AI models require large annotated datasets'
            ]
        }
    ]
    
    # Add diary entries
    entries = [
        {
            'agent': 'strategy_lead',
            'message': 'Researching ai healthcare applications in diagnostics',
            'timestamp': '2024-05-30',
            'insights': ['AI shows potential for reducing diagnostic errors', 'Data quality is critical for AI healthcare success']
        },
        {
            'agent': 'implementation_lead',
            'message': 'Analyzing blockchain implementation in supply chain',
            'timestamp': '2024-05-29',
            'insights': ['Blockchain integration requires significant process changes']
        },
        {
            'agent': 'analyst',
            'message': 'ai healthcare is transforming medical imaging',
            'timestamp': '2024-05-28',
            'insights': ['AI can improve diagnosis accuracy by 30%']
        }
    ]
    
    # Add papers to graph
    for paper in papers:
        paper_uri = dm[paper['id']]
        graph.add((paper_uri, dm.title, Literal(paper['title'])))
        graph.add((paper_uri, dm.author, Literal(paper['author'])))
        graph.add((paper_uri, dm.year, Literal(paper['year'])))
        graph.add((paper_uri, dm.hasTopic, Literal(paper['topic'])))
        
        for insight in paper['insights']:
            graph.add((paper_uri, dm.hasInsight, Literal(insight)))
    
    # Add diary entries to graph
    for i, entry in enumerate(entries, 1):
        entry_uri = dm[f'entry{i}']
        agent_uri = dm[entry['agent']]
        graph.add((agent_uri, dm.hasDiaryEntry, entry_uri))
        graph.add((entry_uri, dm.message, Literal(entry['message'])))
        graph.add((entry_uri, dm.timestamp, Literal(entry['timestamp'])))
        
        for insight in entry['insights']:
            graph.add((entry_uri, dm.hasInsight, Literal(insight)))
    
    return graph

async def run_demo():
    """Run the research investigation demo."""
    print("\n=== Research Investigation Demo ===\n")
    
    # Setup the knowledge graph
    print("Setting up demo knowledge graph...")
    graph = await setup_demo_graph()
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