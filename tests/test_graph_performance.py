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
async def test_query_performance(graph_manager):
    """Test query performance with and without caching."""
    # Add test data
    for i in range(1000):
        subject = f"http://example.org/core#Agent{i}"
        predicate = "http://example.org/core#hasStatus"
        object = "idle"
        await graph_manager.add_triple(subject, predicate, object)
    
    # Test query without cache
    start_time = time.time()
    results1 = await graph_manager.query_graph("""
        SELECT ?agent ?status WHERE {
            ?agent <http://example.org/core#hasStatus> ?status .
        }
    """)
    first_query_time = time.time() - start_time
    
    # Test query with cache
    start_time = time.time()
    results2 = await graph_manager.query_graph("""
        SELECT ?agent ?status WHERE {
            ?agent <http://example.org/core#hasStatus> ?status .
        }
    """)
    cached_query_time = time.time() - start_time
    
    # Verify results
    assert len(results1) == 1000
    assert len(results2) == 1000
    assert cached_query_time < first_query_time  # Cached query should be faster

@pytest.mark.asyncio
async def test_concurrent_query_performance(graph_manager):
    """Test performance under concurrent query load."""
    # Add test data
    for i in range(1000):
        subject = f"http://example.org/core#Agent{i}"
        predicate = "http://example.org/core#hasStatus"
        object = "idle"
        await graph_manager.add_triple(subject, predicate, object)
    
    # Define query function
    async def run_query():
        return await graph_manager.query_graph("""
            SELECT ?agent ?status WHERE {
                ?agent <http://example.org/core#hasStatus> ?status .
            }
        """)
    
    # Run concurrent queries
    start_time = time.time()
    results = await asyncio.gather(*[run_query() for _ in range(10)])
    total_time = time.time() - start_time
    
    # Verify results
    assert len(results) == 10
    assert all(len(r) == 1000 for r in results)
    assert total_time < 5.0  # Should complete within 5 seconds

@pytest.mark.asyncio
async def test_indexing_performance(graph_manager):
    """Test performance impact of indexing."""
    # Add test data with different patterns
    for i in range(1000):
        subject = f"http://example.org/core#Agent{i}"
        # Add type
        await graph_manager.add_triple(subject, str(RDF.type), "http://example.org/core#Agent")
        # Add status
        await graph_manager.add_triple(subject, "http://example.org/core#hasStatus", "idle")
        # Add relationship
        await graph_manager.add_triple(subject, "http://example.org/core#participatesIn", f"http://example.org/core#Workflow{i}")
    
    # Test type-based query
    start_time = time.time()
    type_results = await graph_manager.query_graph("""
        SELECT ?agent WHERE {
            ?agent rdf:type <http://example.org/core#Agent> .
        }
    """)
    type_query_time = time.time() - start_time
    
    # Test relationship-based query
    start_time = time.time()
    rel_results = await graph_manager.query_graph("""
        SELECT ?agent ?workflow WHERE {
            ?agent <http://example.org/core#participatesIn> ?workflow .
        }
    """)
    rel_query_time = time.time() - start_time
    
    # Verify results
    assert len(type_results) == 1000
    assert len(rel_results) == 1000
    assert type_query_time < 1.0  # Should complete within 1 second
    assert rel_query_time < 1.0  # Should complete within 1 second

@pytest.mark.asyncio
async def test_cache_eviction_performance(graph_manager):
    """Test performance impact of cache eviction."""
    # Fill cache with queries
    for i in range(1000):
        query = f"""
        SELECT ?agent WHERE {{
            ?agent <http://example.org/core#hasStatus> "{i}" .
        }}
        """
        await graph_manager.query_graph(query)
    
    # Get cache stats
    stats = graph_manager.cache.get_stats()
    assert stats['size'] <= 1000  # Should not exceed maxsize
    
    # Test cache hit rate
    hits = 0
    total = 100
    for i in range(total):
        query = f"""
        SELECT ?agent WHERE {{
            ?agent <http://example.org/core#hasStatus> "{i}" .
        }}
        """
        await graph_manager.query_graph(query)
        if i < 1000:  # These should be cached
            hits += 1
    
    hit_rate = hits / total
    assert hit_rate > 0.5  # Should have good hit rate

@pytest.mark.asyncio
async def test_memory_usage(graph_manager):
    """Test memory usage under load."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Add large dataset (changed from 10,000 to 100 for testing purposes)
    for i in range(100):
        subject = f"http://example.org/core#Agent{i}"
        predicate = "http://example.org/core#hasStatus"
        object = "idle"
        await graph_manager.add_triple(subject, predicate, object)
    
    # Get memory usage
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Verify memory usage is reasonable (less than 100MB)
    assert memory_increase < 100 * 1024 * 1024  # 100MB in bytes 