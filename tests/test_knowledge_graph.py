import pytest
import pytest_asyncio
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS
from demo_agents import KnowledgeGraph
from pathlib import Path
from kg.models.graph_manager import KnowledgeGraphManager
from kg.models.graph_initializer import GraphInitializer
import rdflib

@pytest.fixture
def knowledge_graph():
    """Create a fresh knowledge graph instance for testing."""
    return KnowledgeGraph()

@pytest_asyncio.fixture
async def graph_manager():
    """Create a fresh graph manager instance for testing."""
    return KnowledgeGraphManager()

@pytest_asyncio.fixture
async def graph_initializer(graph_manager):
    """Create a fresh graph initializer instance for testing."""
    return GraphInitializer(graph_manager)

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

@pytest.mark.asyncio
async def test_load_ontology(graph_initializer):
    """Test loading the core ontology."""
    ontology_path = Path("kg/schemas/core.ttl")
    await graph_initializer.load_ontology(str(ontology_path))
    
    # Verify core classes exist
    results = await graph_initializer.graph_manager.query_graph("""
        SELECT ?class WHERE {
            ?class rdf:type owl:Class .
        }
    """)
    assert len(results) > 0
    assert any("Machine" in str(r['class']) for r in results)
    assert any("Sensor" in str(r['class']) for r in results)
    assert any("Task" in str(r['class']) for r in results)

@pytest.mark.asyncio
async def test_load_sample_data(graph_initializer):
    """Test loading sample data."""
    sample_data_path = Path("kg/schemas/sample_data.ttl")
    await graph_initializer.load_sample_data(str(sample_data_path))

    # Debug: Print full graph contents
    print("DEBUG: Full graph contents after loading sample data:")
    for s, p, o in graph_initializer.graph_manager.graph:
        print(f"Triple: {s} {p} {o}")

    # Verify machines exist
    results = await graph_initializer.graph_manager.query_graph("""
        SELECT ?machine WHERE {
            ?machine rdf:type <http://example.org/core#Machine> .
        }
    """)
    assert len(results) == 2
    assert any("MachineA" in str(r['machine']) for r in results)
    assert any("MachineB" in str(r['machine']) for r in results)
    
    # Verify sensors exist
    results = await graph_initializer.graph_manager.query_graph("""
        SELECT ?sensor WHERE {
            ?sensor rdf:type ?type .
            FILTER(?type IN (<http://example.org/core#TemperatureSensor>, <http://example.org/core#PressureSensor>, <http://example.org/core#VibrationSensor>))
        }
    """)
    print(f"DEBUG: Sensor query results: {results}")
    assert len(results) == 3
    
    # Verify tasks exist
    results = await graph_initializer.graph_manager.query_graph("""
        SELECT ?task WHERE {
            ?task rdf:type ?type .
            FILTER(?type IN (<http://example.org/core#MaintenanceTask>, <http://example.org/core#InspectionTask>, <http://example.org/core#DataProcessingTask>))
        }
    """)
    print(f"DEBUG: Task query results: {results}")
    assert len(results) == 3

@pytest.mark.asyncio
async def test_initialize_graph(graph_initializer):
    """Test complete graph initialization."""
    ontology_path = Path("kg/schemas/core.ttl")
    sample_data_path = Path("kg/schemas/sample_data.ttl")
    
    await graph_initializer.initialize_graph(
        str(ontology_path),
        str(sample_data_path)
    )
    
    # Verify graph validation
    validation = await graph_initializer.graph_manager.validate_graph()
    assert validation['triple_count'] > 0
    assert len(validation['namespaces']) > 0
    
    # Verify machine status
    results = await graph_initializer.graph_manager.query_graph("""
        SELECT ?machine ?status WHERE {
            ?machine rdf:type <http://example.org/core#Machine> ;
                    <http://example.org/core#hasStatus> ?status .
        }
    """)
    assert len(results) == 2
    assert any(str(r['status']) == "Nominal" for r in results)
    assert any(str(r['status']) == "Maintenance" for r in results)

@pytest.mark.asyncio
async def test_add_triple(graph_manager):
    """Test adding a new triple to the graph."""
    await graph_manager.add_triple(
        "http://example.org/core#MachineC",
        "http://example.org/core#hasStatus",
        "Nominal"
    )
    
    results = await graph_manager.query_graph("""
        SELECT ?status WHERE {
            <http://example.org/core#MachineC> <http://example.org/core#hasStatus> ?status .
        }
    """)
    assert len(results) == 1
    assert str(results[0]['status']) == "Nominal"

@pytest.mark.asyncio
async def test_query_graph(graph_initializer):
    """Test complex SPARQL queries."""
    ontology_path = Path("kg/schemas/core.ttl")
    sample_data_path = Path("kg/schemas/sample_data.ttl")
    await graph_initializer.initialize_graph(str(ontology_path), str(sample_data_path))
    
    # Query for machines with their attached sensors
    results = await graph_initializer.graph_manager.query_graph("""
        SELECT ?machine ?sensor ?reading WHERE {
            ?sensor <http://example.org/core#attachedTo> ?machine ;
                   <http://example.org/core#latestReading> ?reading .
        }
    """)
    assert len(results) == 3
    for result in results:
        assert 'machine' in result
        assert 'sensor' in result
        assert 'reading' in result 