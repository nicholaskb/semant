import pytest
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL
from agents.core.reasoner import KnowledgeGraphReasoner
from config.graphdb_config import NAMESPACES

@pytest.fixture
def sample_graph():
    """Create a sample knowledge graph for testing."""
    graph = Graph()
    
    # Bind all required namespaces
    for prefix, uri in NAMESPACES.items():
        graph.bind(prefix, Namespace(uri))
    
    # Get the dm namespace for use in the test data
    dm = Namespace(NAMESPACES['dm'])
    
    # Add some test data
    graph.add((dm.agent1, dm.hasDiaryEntry, dm.entry1))
    graph.add((dm.entry1, dm.message, Literal("ai healthcare research")))
    graph.add((dm.entry1, dm.timestamp, Literal("2024-05-30")))
    
    graph.add((dm.paper1, dm.title, Literal("ai in healthcare: a review")))
    graph.add((dm.paper1, dm.author, Literal("dr. smith")))
    graph.add((dm.paper1, dm.year, Literal("2024")))
    graph.add((dm.paper1, dm.hasTopic, Literal("ai healthcare")))
    
    graph.add((dm.paper1, dm.hasInsight, Literal("ai can improve diagnosis accuracy")))
    
    print("DEBUG: Triples in sample_graph:")
    for s, p, o in graph:
        print(f"  {s} {p} {o}")
    
    return graph

@pytest.fixture
def reasoner(sample_graph):
    """Create a reasoner instance with the sample graph."""
    return KnowledgeGraphReasoner(graph=sample_graph)

@pytest.mark.asyncio
async def test_investigate_research_topic(reasoner):
    """Test investigating a research topic."""
    findings = await reasoner.investigate_research_topic("AI healthcare")
    
    assert findings['topic'] == "AI healthcare"
    assert len(findings['related_concepts']) > 0
    assert len(findings['sources']) > 0
    assert len(findings['key_insights']) > 0
    assert 0 <= findings['confidence'] <= 1

@pytest.mark.asyncio
async def test_find_topic_entries(reasoner):
    """Test finding diary entries related to a topic."""
    entries = await reasoner._find_topic_entries("ai healthcare")
    print(f"DEBUG: test_find_topic_entries results: {entries}")
    assert len(entries) > 0
    assert all('message' in entry for entry in entries)
    assert all('timestamp' in entry for entry in entries)

@pytest.mark.asyncio
async def test_find_related_papers(reasoner):
    """Test finding research papers related to a topic."""
    papers = await reasoner._find_related_papers("ai healthcare")
    print(f"DEBUG: test_find_related_papers results: {papers}")
    assert len(papers) > 0
    assert all('paper' in paper for paper in papers)
    assert all('topic' in paper for paper in papers)
    assert all('insight' in paper for paper in papers)

@pytest.mark.asyncio
async def test_extract_key_insights(reasoner):
    """Test extracting key insights from research."""
    insights = await reasoner._extract_key_insights("ai healthcare")
    print(f"DEBUG: test_extract_key_insights results: {insights}")
    assert len(insights) > 0
    assert all(isinstance(insight, str) for insight in insights)

@pytest.mark.asyncio
async def test_calculate_confidence(reasoner):
    """Test calculating confidence score."""
    findings = {
        'sources': [{'paper': 'Test Paper'}],
        'key_insights': ['Test Insight'],
        'related_concepts': [{'message': 'Test Entry'}]
    }
    
    confidence = await reasoner._calculate_confidence(findings)
    assert 0 <= confidence <= 1

@pytest.mark.asyncio
async def test_traverse_knowledge_graph(reasoner):
    """Test traversing the knowledge graph."""
    traversal = await reasoner.traverse_knowledge_graph(
        "http://example.org/dMaster/agent1",
        max_depth=2
    )
    
    assert traversal['start_node'] == "http://example.org/dMaster/agent1"
    assert traversal['depth'] == 2
    assert len(traversal['nodes']) >= 0
    assert len(traversal['relationships']) >= 0
    assert len(traversal['paths']) >= 0

@pytest.mark.asyncio
async def test_find_related_concepts(reasoner):
    """Test finding related concepts."""
    concepts = await reasoner.find_related_concepts(
        "http://example.org/dMaster/concept1",
        similarity_threshold=0.7
    )
    
    assert all('concept' in concept for concept in concepts)
    assert all('similarity' in concept for concept in concepts)
    assert all(0 <= concept['similarity'] <= 1 for concept in concepts) 