"""Tests for GraphDB integration."""

import pytest
from utils.graphdb_utils import GraphDBUtils
from agents.core.reasoner import KnowledgeGraphReasoner
from config.graphdb_config import SPARQL_ENDPOINT

@pytest.fixture
def graphdb():
    """Create a GraphDBUtils instance for testing."""
    return GraphDBUtils()

@pytest.fixture
def reasoner():
    """Create a KnowledgeGraphReasoner instance for testing."""
    return KnowledgeGraphReasoner(sparql_endpoint=SPARQL_ENDPOINT)

@pytest.mark.asyncio
async def test_graphdb_connection(graphdb):
    """Test basic GraphDB connection."""
    # Test a simple query
    query = """
    SELECT ?s ?p ?o
    WHERE {
        ?s ?p ?o
    }
    LIMIT 1
    """
    results = graphdb.query(query)
    assert isinstance(results, list)

@pytest.mark.asyncio
async def test_add_and_query_triple(graphdb):
    """Test adding and querying a triple."""
    # Add a test triple
    subject = "<http://example.org/test/subject>"
    predicate = "<http://example.org/test/predicate>"
    object_ = "<http://example.org/test/object>"
    
    success = graphdb.add_triple(subject, predicate, object_)
    assert success
    
    # Query for the triple
    query = f"""
    SELECT ?s ?p ?o
    WHERE {{
        {subject} {predicate} {object_} .
    }}
    """
    results = graphdb.query(query)
    assert len(results) > 0
    
    # Clean up
    graphdb.delete_triple(subject, predicate, object_)

@pytest.mark.asyncio
async def test_reasoner_with_graphdb(reasoner):
    """Test KnowledgeGraphReasoner with GraphDB."""
    # Add some test data
    graphdb = GraphDBUtils()
    test_data = [
        {
            'subject': '<http://example.org/test/paper1>',
            'predicate': '<http://example.org/dMaster/hasTopic>',
            'object': '"AI in Healthcare"'
        },
        {
            'subject': '<http://example.org/test/paper1>',
            'predicate': '<http://example.org/dMaster/hasInsight>',
            'object': '"AI can improve diagnosis accuracy"'
        }
    ]
    graphdb.add_triples(test_data)
    
    # Test investigation
    findings = await reasoner.investigate_research_topic("AI in Healthcare")
    assert findings['topic'] == "AI in Healthcare"
    assert len(findings['sources']) > 0
    assert len(findings['key_insights']) > 0
    
    # Clean up
    for triple in test_data:
        graphdb.delete_triple(
            triple['subject'],
            triple['predicate'],
            triple['object']
        )

@pytest.mark.asyncio
async def test_traverse_knowledge_graph(reasoner):
    """Test graph traversal with GraphDB."""
    # Add test data
    graphdb = GraphDBUtils()
    test_data = [
        {
            'subject': 'http://example.org/test/node1',
            'predicate': 'http://example.org/test/relatesTo',
            'object': 'http://example.org/test/node2'
        },
        {
            'subject': 'http://example.org/test/node2',
            'predicate': 'http://example.org/test/relatesTo',
            'object': 'http://example.org/test/node3'
        }
    ]
    graphdb.add_triples(test_data)
    
    # Test traversal
    traversal = await reasoner.traverse_knowledge_graph(
        'http://example.org/test/node1',
        max_depth=2
    )
    assert traversal['start_node'] == 'http://example.org/test/node1'
    assert len(traversal['nodes']) > 0
    assert len(traversal['relationships']) > 0
    
    # Clean up
    for triple in test_data:
        graphdb.delete_triple(
            triple['subject'],
            triple['predicate'],
            triple['object']
        ) 