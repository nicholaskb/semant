import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from rdflib import Graph, RDF, Literal
from kg.models.graph_manager import KnowledgeGraphManager
from kg.models.cache import AsyncLRUCache
from kg.models.indexing import TripleIndex

@pytest_asyncio.fixture
async def graph_manager():
    manager = KnowledgeGraphManager()
    return manager

@pytest_asyncio.fixture
async def cache():
    cache = AsyncLRUCache(maxsize=1000)
    return cache

@pytest_asyncio.fixture
async def triple_index():
    index = TripleIndex()
    return index

@pytest.mark.asyncio
async def test_knowledge_graph_manager_add_triple(graph_manager):
    # Test adding a triple
    subject = "http://example.org/core#Agent1"
    predicate = "http://example.org/core#hasStatus"
    object = "idle"
    
    await graph_manager.add_triple(subject, predicate, object)
    
    # Verify triple was added
    query = f"""
    SELECT ?status WHERE {{
        <{subject}> <{predicate}> ?status .
    }}
    """
    results = await graph_manager.query_graph(query)
    assert len(results) == 1
    assert results[0]['status'] == object

@pytest.mark.asyncio
async def test_knowledge_graph_manager_timestamp_tracking(graph_manager):
    # Test timestamp tracking
    subject = "http://example.org/core#Agent1"
    predicate = "http://example.org/core#hasStatus"
    object = "idle"
    
    await graph_manager.add_triple(subject, predicate, object)
    
    # Verify timestamp was recorded
    timestamps = graph_manager.timestamp_tracker.get_timestamps(subject)
    assert len(timestamps) == 1
    assert isinstance(timestamps[0], str)  # ISO format timestamp

@pytest.mark.asyncio
async def test_async_lru_cache(cache):
    # Test cache operations
    key = "test_query"
    value = {"result": "test"}

    # Test set
    await cache.set(key, value)

    # Test get (increases access frequency)
    result = await cache.get(key)
    assert result == value

    # Test enhanced eviction (frequency-based)
    # Add many keys to exceed maxsize, but don't access the first key again
    for i in range(1001):  # Exceed maxsize
        await cache.set(f"key_{i}", f"value_{i}")
        # Access some keys multiple times to increase their frequency
        if i % 100 == 0:
            await cache.get(f"key_{i}")

    # With enhanced cache, the first key may not be evicted due to higher frequency
    # Instead, test that cache size is properly managed
    cache_stats = cache.get_stats()
    assert cache_stats['size'] <= cache.maxsize

    # Test that we can still retrieve some values
    result = await cache.get("key_100")  # This should exist
    assert result == "value_100"

@pytest.mark.asyncio
async def test_triple_indexing(triple_index):
    # Test indexing operations
    subject = "http://example.org/core#Agent1"
    predicate = "http://example.org/core#hasStatus"
    object = "idle"
    
    # Test predicate indexing
    await triple_index.index_triple(subject, predicate, object)
    assert predicate in triple_index.predicate_index
    assert (subject, object) in triple_index.predicate_index[predicate]
    
    # Test type indexing
    type_predicate = str(RDF.type)  # Convert RDF.type to string
    type_object = "http://example.org/core#Agent"
    await triple_index.index_triple(subject, type_predicate, type_object)
    assert type_object in triple_index.type_index
    assert subject in triple_index.type_index[type_object]
    
    # Test relationship indexing
    rel_predicate = "http://example.org/core#participatesIn"
    rel_object = "http://example.org/core#Workflow1"
    await triple_index.index_triple(subject, rel_predicate, rel_object)
    assert rel_predicate in triple_index.relationship_index
    assert rel_object in triple_index.relationship_index[rel_predicate]
    assert subject in triple_index.relationship_index[rel_predicate][rel_object]

@pytest.mark.asyncio
async def test_concurrent_operations(graph_manager):
    # Test concurrent operations
    async def add_triples():
        for i in range(10):
            subject = f"http://example.org/core#Agent{i}"
            predicate = "http://example.org/core#hasStatus"
            object = "idle"
            await graph_manager.add_triple(subject, predicate, object)

    # Run concurrent operations
    await asyncio.gather(*[add_triples() for _ in range(5)])

    # Verify all triples were added
    query = """
    SELECT ?agent ?status WHERE {
        ?agent <http://example.org/core#hasStatus> ?status .
    }
    """
    results = await graph_manager.query_graph(query)
    # Only 10 unique agent URIs, so only 10 triples should exist
    assert len(results) == 10

@pytest.mark.asyncio
async def test_cache_invalidation(graph_manager):
    # Ensure cache/index clear before test
    if hasattr(graph_manager, '_simple_cache'):
        graph_manager._simple_cache.clear()

    # Test cache invalidation on updates
    subject = "http://example.org/core#Agent1"
    predicate = "http://example.org/core#hasStatus"
    object1 = "idle"
    object2 = "active"
    
    # Add initial triple
    await graph_manager.add_triple(subject, predicate, object1)
    
    # Query and cache result
    query = f"""
    SELECT ?status WHERE {{
        <{subject}> <{predicate}> ?status .
    }}
    """
    results1 = await graph_manager.query_graph(query)
    assert results1[0]['status'] == object1
    
    # Update triple
    await graph_manager.add_triple(subject, predicate, object2)
    
    # Query again
    results2 = await graph_manager.query_graph(query)
    assert results2[0]['status'] == object2  # Should get new value, not cached 