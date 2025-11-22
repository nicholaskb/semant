#!/usr/bin/env python3
"""
Test script for enhanced caching functionality.
Verifies that the improved cache provides better hit rates and performance.
"""

import asyncio
import time
from kg.models.graph_manager import KnowledgeGraphManager

async def test_enhanced_caching():
    """Test the enhanced caching functionality."""

    # Initialize KG Manager
    kg_manager = KnowledgeGraphManager()
    await kg_manager.initialize()

    print("🧪 Testing Enhanced Caching Functionality")
    print("=" * 50)

    # Add some test data
    print("\n📝 Adding test data...")
    test_triples = [
        ('http://example.org/agent/TestAgent1', 'http://example.org/core#type', 'http://example.org/agent/Agent'),
        ('http://example.org/agent/TestAgent1', 'http://example.org/core#hasCapability', 'http://example.org/capability/TestCap1'),
        ('http://example.org/agent/TestAgent1', 'http://example.org/core#status', 'active'),
        ('http://example.org/agent/TestAgent2', 'http://example.org/core#type', 'http://example.org/agent/Agent'),
        ('http://example.org/agent/TestAgent2', 'http://example.org/core#hasCapability', 'http://example.org/capability/TestCap2'),
        ('http://example.org/agent/TestAgent2', 'http://example.org/core#status', 'active'),
    ]

    for subject, predicate, obj in test_triples:
        await kg_manager.add_triple(subject, predicate, obj)

    print(f"Added {len(test_triples)} test triples")

    # Test query performance with cache warming
    print("\n🔄 Testing query performance...")

    test_queries = [
        "SELECT ?s WHERE { ?s <http://example.org/core#type> <http://example.org/agent/Agent> }",
        "SELECT ?s ?o WHERE { ?s <http://example.org/core#hasCapability> ?o }",
        "SELECT ?s WHERE { ?s <http://example.org/core#status> 'active' }",
        "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10",
    ]

    # First round - should populate cache
    print("First round (cache population):")
    start_time = time.time()
    for i, query in enumerate(test_queries):
        result = await kg_manager.query_graph(query)
        print(".4f")
    first_round_time = time.time() - start_time

    # Second round - should benefit from cache
    print("\nSecond round (cache hits):")
    start_time = time.time()
    for i, query in enumerate(test_queries):
        result = await kg_manager.query_graph(query)
        print(".4f")
    second_round_time = time.time() - start_time

    # Calculate improvement
    improvement = ((first_round_time - second_round_time) / first_round_time) * 100
    print(".2f")

    # Get cache statistics
    print("\n📊 Cache Statistics:")
    cache_stats = await kg_manager.get_cache_stats()

    if cache_stats:
        perf = cache_stats.get('cache_performance', {})
        pattern = cache_stats.get('pattern_analysis', {})
        overall = cache_stats.get('overall_metrics', {})

        print(f"Cache size: {perf.get('size', 0)}/{perf.get('maxsize', 0)}")
        print(".1%")
        print(f"Total accesses: {perf.get('total_accesses', 0)}")
        print(f"Unique patterns: {perf.get('unique_patterns', 0)}")
        print(".2%")

        # Show most common patterns
        most_common = pattern.get('most_common_patterns', [])
        if most_common:
            print("\nMost common query patterns:")
            for pattern_name, count in most_common[:3]:
                print(f"  {pattern_name}: {count} accesses")

    # Test pattern recognition
    print("\n🔍 Testing pattern recognition...")

    # Execute similar queries to test pattern detection
    similar_queries = [
        "SELECT ?x WHERE { ?x <http://example.org/core#type> <http://example.org/agent/Agent> }",
        "SELECT ?y WHERE { ?y <http://example.org/core#status> 'active' }",
        "SELECT ?z ?w WHERE { ?z <http://example.org/core#hasCapability> ?w }",
    ]

    for query in similar_queries:
        await kg_manager.query_graph(query)

    # Check updated pattern stats
    updated_stats = await kg_manager.get_cache_stats()
    if updated_stats:
        pattern = updated_stats.get('pattern_analysis', {})
        most_common = pattern.get('most_common_patterns', [])
        if most_common:
            print("Updated pattern counts after similar queries:")
            for pattern_name, count in most_common[:3]:
                print(f"  {pattern_name}: {count} accesses")

    # Cleanup
    await kg_manager.shutdown()

    print("\n✅ Enhanced caching test completed!")
    print(f"Performance improvement: {improvement:.2f}%")
    print("Cache hit rate should be significantly improved on repeated queries.")

if __name__ == "__main__":
    asyncio.run(test_enhanced_caching())

