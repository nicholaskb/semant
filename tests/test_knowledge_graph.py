import pytest
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS
from demo_agents import KnowledgeGraph

@pytest.fixture
def knowledge_graph():
    """Create a fresh knowledge graph instance for testing."""
    return KnowledgeGraph()

@pytest.mark.asyncio
async def test_knowledge_graph_initialization(knowledge_graph):
    """Test knowledge graph initialization and namespace binding."""
    # Verify graph is initialized
    assert isinstance(knowledge_graph.graph, Graph)
    
    # Verify namespaces are bound
    namespaces = dict(knowledge_graph.graph.namespaces())
    assert "dm" in namespaces
    assert "task" in namespaces
    assert "agent" in namespaces
    assert "analysis" in namespaces

@pytest.mark.asyncio
async def test_triple_addition(knowledge_graph):
    """Test adding triples to the knowledge graph."""
    # Add test triple
    await knowledge_graph.add_triple(
        "test:subject",
        "test:predicate",
        "test:object"
    )
    
    # Verify triple was added
    triples = list(knowledge_graph.graph.triples((
        URIRef("test:subject"),
        URIRef("test:predicate"),
        URIRef("test:object")
    )))
    assert len(triples) == 1

@pytest.mark.asyncio
async def test_graph_update(knowledge_graph):
    """Test updating the graph with structured data."""
    # Test data
    test_data = {
        "test:entity1": {
            "test:property1": "value1",
            "test:property2": "value2"
        },
        "test:entity2": {
            "test:property3": "value3"
        }
    }
    
    # Update graph
    await knowledge_graph.update_graph(test_data)
    
    # Verify updates
    for entity, properties in test_data.items():
        for prop, value in properties.items():
            triples = list(knowledge_graph.graph.triples((
                URIRef(entity),
                URIRef(prop),
                Literal(value)
            )))
            assert len(triples) == 1

@pytest.mark.asyncio
async def test_graph_query(knowledge_graph):
    """Test querying the knowledge graph."""
    # Add test data
    test_data = {
        "test:entity1": {
            "test:property1": "value1",
            "test:property2": "value2"
        }
    }
    await knowledge_graph.update_graph(test_data)
    
    # Query graph
    results = await knowledge_graph.query({})
    
    # Verify results
    assert "test:entity1" in results
    assert "test:property1" in results["test:entity1"]
    assert "test:property2" in results["test:entity1"]
    assert results["test:entity1"]["test:property1"] == "value1"
    assert results["test:entity1"]["test:property2"] == "value2"

@pytest.mark.asyncio
async def test_semantic_relationships(knowledge_graph):
    """Test semantic relationship handling in the knowledge graph."""
    # Add test data with semantic relationships
    test_data = {
        "test:engagement1": {
            str(RDF.type): "test:Engagement",
            str(RDFS.subClassOf): "test:Project",
            "test:hasClient": "test:client1",
            "test:hasStrategy": "test:strategy1"
        },
        "test:strategy1": {
            str(RDF.type): "test:Strategy",
            str(RDFS.subClassOf): "test:Plan",
            "test:hasPillar": ["test:pillar1", "test:pillar2"]
        }
    }
    
    # Update graph
    await knowledge_graph.update_graph(test_data)
    
    # Query and verify semantic relationships
    results = await knowledge_graph.query({})
    
    # Verify type relationships
    assert str(RDF.type) in results["test:engagement1"]
    assert results["test:engagement1"][str(RDF.type)] == "test:Engagement"
    
    # Verify subclass relationships
    assert str(RDFS.subClassOf) in results["test:engagement1"]
    assert results["test:engagement1"][str(RDFS.subClassOf)] == "test:Project"
    
    # Verify object properties
    assert "test:hasClient" in results["test:engagement1"]
    assert "test:hasStrategy" in results["test:engagement1"]
    
    # Verify strategy relationships
    assert "test:strategy1" in results
    assert str(RDF.type) in results["test:strategy1"]
    assert results["test:strategy1"][str(RDF.type)] == "test:Strategy"

@pytest.mark.asyncio
async def test_complex_query_patterns(knowledge_graph):
    """Test complex query patterns in the knowledge graph."""
    # Add test data with complex relationships
    test_data = {
        "test:engagement1": {
            str(RDF.type): "test:Engagement",
            "test:hasPhase": ["test:phase1", "test:phase2"],
            "test:hasMetric": ["test:metric1", "test:metric2"]
        },
        "test:phase1": {
            str(RDF.type): "test:Phase",
            "test:hasActivity": ["test:activity1", "test:activity2"],
            "test:hasDuration": "3 months"
        },
        "test:metric1": {
            str(RDF.type): "test:Metric",
            "test:hasTarget": "90%",
            "test:hasFrequency": "Monthly"
        }
    }
    
    # Update graph
    await knowledge_graph.update_graph(test_data)
    
    # Query and verify complex patterns
    results = await knowledge_graph.query({})
    
    # Verify engagement structure
    assert "test:engagement1" in results
    assert "test:hasPhase" in results["test:engagement1"]
    assert "test:hasMetric" in results["test:engagement1"]
    
    # Verify phase details
    assert "test:phase1" in results
    assert str(RDF.type) in results["test:phase1"]
    assert "test:hasActivity" in results["test:phase1"]
    assert "test:hasDuration" in results["test:phase1"]
    
    # Verify metric details
    assert "test:metric1" in results
    assert str(RDF.type) in results["test:metric1"]
    assert "test:hasTarget" in results["test:metric1"]
    assert "test:hasFrequency" in results["test:metric1"] 