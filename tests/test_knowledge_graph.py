import pytest
import pytest_asyncio
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD
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
    """Test loading sample data into the graph."""
    ontology_path = Path("kg/schemas/core.ttl")
    sample_data_path = Path("kg/schemas/sample_data.ttl")
    await graph_initializer.initialize_graph(str(ontology_path), str(sample_data_path))
    
    # Query for all sensors
    results = await graph_initializer.graph_manager.query_graph("""
        PREFIX core: <http://example.org/core#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?sensor WHERE {
            ?sensor rdf:type/rdfs:subClassOf* core:Sensor .
        }
    """)
    assert len(results) == 3  # Should have 3 sensors in sample data
    
    # Query for machine statuses
    results = await graph_initializer.graph_manager.query_graph("""
        PREFIX core: <http://example.org/core#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?machine ?status WHERE {
            ?machine rdf:type/rdfs:subClassOf* core:Machine ;
                    core:hasStatus ?status .
        }
    """)
    assert len(results) > 0
    for result in results:
        assert 'machine' in result
        assert 'status' in result
        assert result['status'] in ["Nominal", "Maintenance", "Error"]

    # Query for tasks
    results = await graph_initializer.graph_manager.query_graph("""
        PREFIX core: <http://example.org/core#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?task WHERE {
            ?task rdf:type/rdfs:subClassOf* core:Task .
        }
    """)
    assert len(results) > 0

    # Query for agents
    results = await graph_initializer.graph_manager.query_graph("""
        PREFIX core: <http://example.org/core#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?agent WHERE {
            ?agent rdf:type/rdfs:subClassOf* core:Agent .
        }
    """)
    assert len(results) > 0

    # Query for events
    results = await graph_initializer.graph_manager.query_graph("""
        PREFIX core: <http://example.org/core#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?event WHERE {
            ?event rdf:type/rdfs:subClassOf* core:Event .
        }
    """)
    assert len(results) > 0

    # Query for alerts
    results = await graph_initializer.graph_manager.query_graph("""
        PREFIX core: <http://example.org/core#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?alert WHERE {
            ?alert rdf:type/rdfs:subClassOf* core:Alert .
        }
    """)
    assert len(results) > 0

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
    assert results[0]['status'] == "Nominal"

@pytest.mark.asyncio
async def test_query_graph(graph_initializer):
    """Test complex SPARQL queries."""
    ontology_path = Path("kg/schemas/core.ttl")
    sample_data_path = Path("kg/schemas/sample_data.ttl")
    await graph_initializer.initialize_graph(str(ontology_path), str(sample_data_path))
    
    # Query for machines with their attached sensors
    results = await graph_initializer.graph_manager.query_graph("""
        PREFIX core: <http://example.org/core#>
        SELECT ?machine ?sensor ?reading WHERE {
            ?sensor core:attachedTo ?machine ;
                   core:latestReading ?reading .
        }
    """)
    assert len(results) == 3
    for result in results:
        assert 'machine' in result
        assert 'sensor' in result
        assert 'reading' in result
        # Verify reading is a float
        assert isinstance(float(result['reading']), float)

@pytest.mark.asyncio
async def test_performance_metrics(graph_manager):
    """Test performance metrics tracking."""
    # Execute some queries
    await graph_manager.query_graph("""
        SELECT ?s ?p ?o WHERE {
            ?s ?p ?o .
        } LIMIT 1
    """)
    
    # Get stats
    stats = graph_manager.get_stats()
    metrics = stats['metrics']
    
    # Verify metrics
    assert metrics['query_count'] > 0
    assert metrics['total_query_time'] > 0
    assert metrics['key_conversion_time'] >= 0
    assert metrics['cache_hits'] >= 0
    assert metrics['cache_misses'] >= 0

@pytest.mark.asyncio
async def test_type_conversion(graph_manager):
    """Test type conversion in query results."""
    from rdflib import Literal
    from rdflib.namespace import XSD, Namespace
    # Add test namespace
    graph_manager.namespaces['test'] = Namespace('http://example.org/test/')
    graph_manager.graph.bind('test', graph_manager.namespaces['test'])
    test_ns = graph_manager.namespaces['test']

    # Add test data with correct datatypes and fully qualified URIs
    await graph_manager.add_triple(
        str(test_ns['entity1']),
        str(test_ns['hasString']),
        "string value"
    )
    await graph_manager.add_triple(
        str(test_ns['entity1']),
        str(test_ns['hasInteger']),
        Literal(42, datatype=XSD.integer)
    )
    await graph_manager.add_triple(
        str(test_ns['entity1']),
        str(test_ns['hasFloat']),
        Literal(3.14, datatype=XSD.float)
    )
    await graph_manager.add_triple(
        str(test_ns['entity1']),
        str(test_ns['hasBoolean']),
        Literal(True, datatype=XSD.boolean)
    )

    # Query and verify types
    results = await graph_manager.query_graph("""
        PREFIX test: <http://example.org/test/>
        SELECT ?string ?integer ?float ?boolean WHERE {
            ?entity test:hasString ?string ;
                   test:hasInteger ?integer ;
                   test:hasFloat ?float ;
                   test:hasBoolean ?boolean .
        }
    """)

    assert len(results) == 1
    result = results[0]

    # Verify types
    assert isinstance(result['string'], str)
    assert isinstance(result['integer'], int)
    assert isinstance(result['float'], float)
    assert isinstance(result['boolean'], bool)

    # Verify values
    assert result['string'] == "string value"
    assert result['integer'] == 42
    assert result['float'] == 3.14
    assert result['boolean'] is True

@pytest.mark.asyncio
async def test_cache_metrics(graph_manager):
    """Test cache hit/miss metrics."""
    # First query (cache miss)
    await graph_manager.query_graph("""
        SELECT ?s ?p ?o WHERE {
            ?s ?p ?o .
        } LIMIT 1
    """)
    
    # Same query again (cache hit)
    await graph_manager.query_graph("""
        SELECT ?s ?p ?o WHERE {
            ?s ?p ?o .
        } LIMIT 1
    """)
    
    # Get stats
    stats = graph_manager.get_stats()
    metrics = stats['metrics']
    
    # Verify cache metrics
    assert metrics['cache_hits'] == 1
    assert metrics['cache_misses'] == 1

@pytest.mark.asyncio
async def test_clear_metrics(graph_manager):
    """Test metrics clearing."""
    # Execute some queries
    await graph_manager.query_graph("""
        SELECT ?s ?p ?o WHERE {
            ?s ?p ?o .
        } LIMIT 1
    """)
    
    # Clear graph
    await graph_manager.clear()
    
    # Get stats
    stats = graph_manager.get_stats()
    metrics = stats['metrics']
    
    # Verify metrics are reset
    assert metrics['query_count'] == 0
    assert metrics['cache_hits'] == 0
    assert metrics['cache_misses'] == 0
    assert metrics['key_conversion_time'] == 0.0
    assert metrics['total_query_time'] == 0.0

@pytest.mark.asyncio
async def test_subclass_reasoning_sensors(graph_initializer):
    """Test that all sensors, including subclasses, are returned."""
    ontology_path = Path("kg/schemas/core.ttl")
    sample_data_path = Path("kg/schemas/sample_data.ttl")
    await graph_initializer.initialize_graph(str(ontology_path), str(sample_data_path))
    results = await graph_initializer.graph_manager.query_graph("""
        PREFIX core: <http://example.org/core#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?sensor ?type WHERE {
            ?sensor rdf:type/rdfs:subClassOf* core:Sensor .
            ?sensor rdf:type ?type .
        }
    """)
    sensor_uris = {r['sensor'] for r in results}
    assert len(sensor_uris) == 3
    types = {r['type'] for r in results}
    assert any("TemperatureSensor" in t or "PressureSensor" in t or "VibrationSensor" in t for t in types)

@pytest.mark.asyncio
async def test_average_sensor_reading_per_machine(graph_initializer):
    """Test aggregation: average sensor reading per machine."""
    ontology_path = Path("kg/schemas/core.ttl")
    sample_data_path = Path("kg/schemas/sample_data.ttl")
    await graph_initializer.initialize_graph(str(ontology_path), str(sample_data_path))
    results = await graph_initializer.graph_manager.query_graph("""
        PREFIX core: <http://example.org/core#>
        SELECT ?machine (AVG(?reading) as ?avg_reading) WHERE {
            ?sensor core:attachedTo ?machine ;
                   core:latestReading ?reading .
        }
        GROUP BY ?machine
    """)
    assert len(results) >= 1
    for r in results:
        assert 'machine' in r and 'avg_reading' in r
        assert isinstance(float(r['avg_reading']), float)

@pytest.mark.asyncio
async def test_high_alert_sensors(graph_initializer):
    """Test filtering: sensors with readings above a threshold."""
    ontology_path = Path("kg/schemas/core.ttl")
    sample_data_path = Path("kg/schemas/sample_data.ttl")
    await graph_initializer.initialize_graph(str(ontology_path), str(sample_data_path))
    results = await graph_initializer.graph_manager.query_graph("""
        PREFIX core: <http://example.org/core#>
        SELECT ?sensor ?reading WHERE {
            ?sensor core:latestReading ?reading .
            FILTER(xsd:float(?reading) > 50)
        }
    """)
    assert any(float(r['reading']) > 50 for r in results)

@pytest.mark.asyncio
async def test_machine_status_summary(graph_initializer):
    """Test machine status summary: all machines and their statuses."""
    ontology_path = Path("kg/schemas/core.ttl")
    sample_data_path = Path("kg/schemas/sample_data.ttl")
    await graph_initializer.initialize_graph(str(ontology_path), str(sample_data_path))
    results = await graph_initializer.graph_manager.query_graph("""
        PREFIX core: <http://example.org/core#>
        SELECT ?machine ?status WHERE {
            ?machine rdf:type/rdfs:subClassOf* core:Machine ;
                    core:hasStatus ?status .
        }
    """)
    statuses = {r['status'] for r in results}
    assert "Nominal" in statuses or "Maintenance" in statuses

@pytest.mark.asyncio
async def test_query_no_data(graph_initializer):
    """Test edge case: query for a type that does not exist."""
    ontology_path = Path("kg/schemas/core.ttl")
    sample_data_path = Path("kg/schemas/sample_data.ttl")
    await graph_initializer.initialize_graph(str(ontology_path), str(sample_data_path))
    results = await graph_initializer.graph_manager.query_graph("""
        PREFIX core: <http://example.org/core#>
        SELECT ?ghost WHERE {
            ?ghost rdf:type core:GhostEntity .
        }
    """)
    assert results == []

@pytest.mark.asyncio
async def test_high_risk_machines(graph_initializer):
    """Test identifying high-risk machines based on sensor readings and status."""
    ontology_path = Path("kg/schemas/core.ttl")
    sample_data_path = Path("kg/schemas/sample_data.ttl")
    await graph_initializer.initialize_graph(str(ontology_path), str(sample_data_path))
    
    # Query for machines with high-risk sensors and their status
    results = await graph_initializer.graph_manager.query_graph("""
        PREFIX core: <http://example.org/core#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?machine ?status ?sensor ?reading ?sensor_type WHERE {
            ?sensor rdf:type/rdfs:subClassOf* core:Sensor ;
                   core:attachedTo ?machine ;
                   core:latestReading ?reading ;
                   rdf:type ?sensor_type .
            ?machine rdf:type/rdfs:subClassOf* core:Machine ;
                    core:hasStatus ?status .
            FILTER(xsd:float(?reading) > 50)
        }
    """)
    
    # Verify results
    assert len(results) > 0
    for result in results:
        assert all(key in result for key in ['machine', 'status', 'sensor', 'reading', 'sensor_type'])
        assert float(result['reading']) > 50
        assert result['status'] in ["Nominal", "Maintenance", "Error"]
        assert "Sensor" in result['sensor_type']

@pytest.mark.asyncio
async def test_machine_risk_scoring(graph_initializer):
    """Test machine risk scoring based on multiple factors (RDFLib-compatible subquery join)."""
    ontology_path = Path("kg/schemas/core.ttl")
    sample_data_path = Path("kg/schemas/sample_data.ttl")
    await graph_initializer.initialize_graph(str(ontology_path), str(sample_data_path))
    
    # Query for machine risk assessment
    results = await graph_initializer.graph_manager.query_graph("""
        PREFIX core: <http://example.org/core#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        SELECT ?machine ?status ?risk_score ?high_risk_sensors ?avg_reading WHERE {
            ?machine rdf:type/rdfs:subClassOf* core:Machine ;
                    core:hasStatus ?status .
            
            # Join with sensor aggregates
            {
                SELECT ?machine (COUNT(?sensor) AS ?high_risk_sensors) (AVG(xsd:float(?reading)) AS ?avg_reading) WHERE {
                    ?sensor rdf:type/rdfs:subClassOf* core:Sensor ;
                            core:attachedTo ?machine ;
                            core:latestReading ?reading .
                } GROUP BY ?machine
            }
            BIND(COALESCE(?high_risk_sensors, 0) AS ?hrs)
            BIND(COALESCE(?avg_reading, 0.0) AS ?avg)
            BIND(
                (IF(?status = "Error", 1.0,
                   IF(?status = "Maintenance", 0.7,
                      IF(?status = "Nominal", 0.3, 0.5)))) * 
                (1.0 + (xsd:float(?hrs) * 0.2)) * 
                (1.0 + IF(xsd:float(?avg) > 50, 0.3, 0.0))
                AS ?risk_score
            )
        }
    """)
    
    # Verify results
    assert len(results) > 0
    for result in results:
        assert all(key in result for key in ['machine', 'status', 'risk_score', 'high_risk_sensors', 'avg_reading'])
        assert float(result['risk_score']) >= 0.0
        assert float(result['risk_score']) <= 2.0  # Maximum theoretical score
        assert int(result['high_risk_sensors']) >= 0
        assert float(result['avg_reading']) >= 0.0
        assert result['status'] in ["Nominal", "Maintenance", "Error"]

@pytest.mark.asyncio
async def test_graph_versioning(graph_manager):
    """Test graph versioning functionality."""
    # Add initial triples
    await graph_manager.add_triple("test:subject1", "test:predicate1", "test:object1")
    await graph_manager.add_triple("test:subject2", "test:predicate2", "test:object2")
    
    # Get initial version
    initial_version = graph_manager.version_tracker.get_current_version()
    
    # Add more triples
    await graph_manager.add_triple("test:subject3", "test:predicate3", "test:object3")
    
    # Verify version was created
    assert graph_manager.version_tracker.get_current_version() > initial_version
    
    # Rollback to initial version
    await graph_manager.rollback(initial_version)
    
    # Verify rollback
    results = await graph_manager.query_graph("""
        SELECT ?subject ?predicate ?object WHERE {
            ?subject ?predicate ?object .
        }
    """)
    assert len(results) == 2
    assert any(r['object'] == 'test:object1' for r in results)
    assert any(r['object'] == 'test:object2' for r in results)
    assert not any(r['object'] == 'test:object3' for r in results)

@pytest.mark.asyncio
async def test_graph_security(graph_manager):
    """Test graph security functionality."""
    # Add security rule
    graph_manager.security.add_access_rule(
        "test:subject1",
        "test:predicate1",
        "test:object1",
        ["admin"]
    )
    
    # Test authorized access
    await graph_manager.add_triple(
        "test:subject1",
        "test:predicate1",
        "test:object1",
        role="admin"
    )
    
    # Test unauthorized access
    with pytest.raises(PermissionError):
        await graph_manager.add_triple(
            "test:subject1",
            "test:predicate1",
            "test:object1",
            role="user"
        )
    
    # Verify audit log
    audit_log = graph_manager.security.get_audit_log()
    assert len(audit_log) == 2
    assert audit_log[0]['success'] is True
    assert audit_log[1]['success'] is False
    assert audit_log[0]['role'] == 'admin'
    assert audit_log[1]['role'] == 'user'

@pytest.mark.asyncio
async def test_graph_validation(graph_manager):
    """Test graph validation functionality."""
    # Add validation rule
    graph_manager.add_validation_rule({
        'type': 'sparql',
        'query': """
            SELECT ?machine WHERE {
                ?machine rdf:type <http://example.org/core#Machine> .
                ?machine <http://example.org/core#hasStatus> ?status .
                FILTER(?status = "Nominal")
            }
        """
    })
    
    # Add data that should pass validation
    await graph_manager.add_triple(
        "test:machine1",
        "rdf:type",
        "http://example.org/core#Machine"
    )
    await graph_manager.add_triple(
        "test:machine1",
        "http://example.org/core#hasStatus",
        "Nominal"
    )
    
    # Validate graph
    validation_results = await graph_manager.validate_graph()
    assert len(validation_results['validation_errors']) == 0
    
    # Add data that should fail validation
    await graph_manager.add_triple(
        "test:machine2",
        "rdf:type",
        "http://example.org/core#Machine"
    )
    await graph_manager.add_triple(
        "test:machine2",
        "http://example.org/core#hasStatus",
        "Warning"
    )
    
    # Validate graph again
    validation_results = await graph_manager.validate_graph()
    assert len(validation_results['validation_errors']) > 0

@pytest.mark.asyncio
async def test_selective_cache_invalidation(graph_manager):
    """Test selective cache invalidation."""
    # Add initial data
    await graph_manager.add_triple("test:subject1", "test:predicate1", "test:object1")
    
    # Query and cache result
    query1 = """
        SELECT ?object WHERE {
            test:subject1 test:predicate1 ?object .
        }
    """
    results1 = await graph_manager.query_graph(query1)
    assert len(results1) == 1
    
    # Add unrelated data
    await graph_manager.add_triple("test:subject2", "test:predicate2", "test:object2")
    
    # Query again - should use cache
    results2 = await graph_manager.query_graph(query1)
    assert len(results2) == 1
    assert graph_manager.metrics['cache_hits'] > 0
    
    # Add related data
    await graph_manager.add_triple("test:subject1", "test:predicate1", "test:object3")
    
    # Query again - should not use cache
    results3 = await graph_manager.query_graph(query1)
    assert len(results3) == 1
    assert results3[0]['object'] == 'test:object3'

@pytest.mark.asyncio
async def test_enhanced_metrics(graph_manager):
    """Test enhanced metrics collection."""
    # Add data with validation
    graph_manager.add_validation_rule({
        'type': 'pattern',
        'subject': 'test:subject1',
        'predicate': 'test:predicate1',
        'object': 'test:object1'
    })
    
    await graph_manager.add_triple("test:subject1", "test:predicate1", "test:object1")
    
    # Add data with security
    graph_manager.security.add_access_rule(
        "test:subject2",
        "test:predicate2",
        "test:object2",
        ["admin"]
    )
    
    try:
        await graph_manager.add_triple(
            "test:subject2",
            "test:predicate2",
            "test:object2",
            role="user"
        )
    except PermissionError:
        pass
    
    # Get stats
    stats = graph_manager.get_stats()
    
    # Verify metrics
    assert stats['version_count'] > 0
    assert stats['security_stats']['access_rules'] == 1
    assert stats['security_stats']['audit_log_entries'] > 0
    assert stats['security_stats']['security_violations'] > 0
    assert 'validation_errors' in stats['metrics'] 