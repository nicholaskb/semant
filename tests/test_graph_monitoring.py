import pytest
import asyncio
import time
from datetime import datetime
from rdflib import Graph, RDF, Literal
from kg.models.graph_manager import KnowledgeGraphManager
from kg.models.cache import AsyncLRUCache
from kg.models.indexing import TripleIndex
import pytest_asyncio

@pytest_asyncio.fixture
async def graph_manager():
    manager = KnowledgeGraphManager()
    yield manager
    await manager.clear()

@pytest.mark.asyncio
async def test_stats_collection(graph_manager):
    """Test collection of graph statistics."""
    # Add test data
    for i in range(100):
        subject = f"http://example.org/core#Agent{i}"
        predicate = "http://example.org/core#hasStatus"
        object = "idle"
        await graph_manager.add_triple(subject, predicate, object)
    
    # Get stats
    stats = graph_manager.get_stats()
    
    # Verify stats
    assert stats['triple_count'] == 100
    assert 'cache_stats' in stats
    assert 'index_stats' in stats
    assert 'timestamp_count' in stats
    
    # Verify cache stats
    cache_stats = stats['cache_stats']
    assert 'size' in cache_stats
    assert 'maxsize' in cache_stats
    assert 'hits' in cache_stats
    assert 'misses' in cache_stats
    
    # Verify index stats
    index_stats = stats['index_stats']
    assert 'predicate_count' in index_stats
    assert 'type_count' in index_stats
    assert 'relationship_count' in index_stats
    assert 'total_triples' in index_stats

@pytest.mark.asyncio
async def test_timestamp_tracking(graph_manager):
    """Test timestamp tracking for entity updates."""
    # Add test data with multiple updates
    subject = "http://example.org/core#Agent1"
    for status in ["idle", "active", "busy", "idle"]:
        await graph_manager.add_triple(
            subject,
            "http://example.org/core#hasStatus",
            status
        )
    
    # Get timestamps
    timestamps = graph_manager.timestamp_tracker.get_timestamps(subject)
    
    # Verify timestamps
    assert len(timestamps) == 4  # One for each update
    assert all(isinstance(ts, str) for ts in timestamps)  # All should be ISO format strings
    
    # Verify timestamp order
    timestamps_dt = [datetime.fromisoformat(ts) for ts in timestamps]
    assert all(timestamps_dt[i] <= timestamps_dt[i+1] for i in range(len(timestamps_dt)-1))

@pytest.mark.asyncio
async def test_cache_monitoring(graph_manager):
    """Test cache monitoring and statistics."""
    # Run some queries to populate cache
    for i in range(10):
        query = f"""
        SELECT ?agent WHERE {{
            ?agent <http://example.org/core#hasStatus> "{i}" .
        }}
        """
        await graph_manager.query_graph(query)
    
    # Get cache stats
    stats = graph_manager.cache.get_stats()
    
    # Verify cache stats
    assert stats['size'] > 0
    assert stats['maxsize'] == 1000
    assert stats['hits'] >= 0
    assert stats['misses'] >= 0
    
    # Test cache hit rate calculation
    hit_rate = stats['hits'] / (stats['hits'] + stats['misses']) if (stats['hits'] + stats['misses']) > 0 else 0
    assert 0 <= hit_rate <= 1

@pytest.mark.asyncio
async def test_index_monitoring(graph_manager):
    """Test index monitoring and statistics."""
    # Add test data with different patterns
    for i in range(10):
        subject = f"http://example.org/core#Agent{i}"
        # Add type
        await graph_manager.add_triple(subject, str(RDF.type), "http://example.org/core#Agent")
        # Add status
        await graph_manager.add_triple(subject, "http://example.org/core#hasStatus", "idle")
        # Add relationship
        await graph_manager.add_triple(subject, "http://example.org/core#participatesIn", f"http://example.org/core#Workflow{i}")
    
    # Get index stats
    stats = graph_manager.index.get_stats()
    
    # Verify index stats
    assert stats['predicate_count'] > 0
    assert stats['type_count'] > 0
    assert stats['relationship_count'] > 0
    assert stats['total_triples'] == 30  # 10 agents * 3 triples each

@pytest.mark.asyncio
async def test_performance_monitoring(graph_manager):
    """Test performance monitoring capabilities."""
    # Add test data
    for i in range(100):
        subject = f"http://example.org/core#Agent{i}"
        predicate = "http://example.org/core#hasStatus"
        object = "idle"
        await graph_manager.add_triple(subject, predicate, object)
    
    # Test query performance
    start_time = time.time()
    results = await graph_manager.query_graph("""
        SELECT ?agent ?status WHERE {
            ?agent <http://example.org/core#hasStatus> ?status .
        }
    """)
    query_time = time.time() - start_time
    
    # Verify performance
    assert len(results) == 100
    assert query_time < 1.0  # Should complete within 1 second
    
    # Get stats after query
    stats = graph_manager.get_stats()
    cache_stats = stats['cache_stats']
    
    # Verify cache performance
    assert cache_stats['hits'] >= 0
    assert cache_stats['misses'] >= 0
    assert cache_stats['size'] > 0 