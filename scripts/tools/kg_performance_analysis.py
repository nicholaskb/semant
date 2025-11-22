#!/usr/bin/env python3
"""
Knowledge Graph Performance Analysis Script
Runs comprehensive profiling to identify bottlenecks and optimization opportunities.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List
from loguru import logger

from kg.models.graph_manager import KnowledgeGraphManager
from kg.models.performance_profiler import KGPerformanceProfiler

async def run_performance_analysis():
    """Run comprehensive performance analysis of the Knowledge Graph."""

    # Initialize KG Manager
    kg_manager = KnowledgeGraphManager()
    await kg_manager.initialize()

    # Initialize profiler
    profiler = KGPerformanceProfiler(kg_manager)

    print("🔍 Starting Knowledge Graph Performance Analysis...")
    print("=" * 60)

    # 1. Profile common query patterns
    print("\n📊 Profiling Query Performance...")

    common_queries = [
        "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 100",  # Broad query
        "SELECT ?s WHERE { ?s <http://example.org/core#type> ?o }",  # Type query
        "SELECT ?s ?p ?o WHERE { ?s ?p ?o . FILTER(?s = <http://example.org/agent/Agent>) }",  # Specific subject
        "SELECT ?s ?o WHERE { ?s <http://example.org/core#hasCapability> ?o }",  # Relationship query
    ]

    query_results = await profiler.profile_query_performance(common_queries, iterations=5)
    print("Query Performance Results:")
    for query, stats in query_results.items():
        print(".4f")

    # 2. Profile mutation operations
    print("\n📝 Profiling Mutation Operations...")

    mutation_ops = [
        {
            'type': 'add',
            'subject': 'http://example.org/test/perf_subject',
            'predicate': 'http://example.org/test#perf_predicate',
            'object': 'test_value'
        }
    ]

    mutation_results = await profiler.profile_mutation_performance(mutation_ops, iterations=3)
    print("Mutation Performance Results:")
    for op, stats in mutation_results.items():
        print(".4f")

    # 3. Profile bulk operations
    print("\n📦 Profiling Bulk Operations...")
    bulk_results = await profiler.profile_bulk_operations(bulk_size=50)
    print("Bulk Operation Results:")
    print(".4f")
    print(".4f")
    print(".6f")
    print(".6f")

    # 4. Analyze current KG state
    print("\n📈 Current Knowledge Graph Statistics...")
    stats = await kg_manager.get_stats()
    print(f"Total triples: {stats['metrics']['triple_count']}")
    print(f"Cache hits: {stats['metrics']['cache_hits']}")
    print(f"Cache misses: {stats['metrics']['cache_misses']}")
    print(f"Query count: {stats['metrics']['query_count']}")

    # 5. Generate comprehensive report
    print("\n📋 Generating Performance Report...")
    report = profiler.generate_report()
    print(report)

    # 6. Save results to file
    results_dir = Path("kg_performance_results")
    results_dir.mkdir(exist_ok=True)

    results = {
        'query_performance': query_results,
        'mutation_performance': mutation_results,
        'bulk_performance': bulk_results,
        'kg_stats': stats,
        'report': report,
        'profiler_stats': profiler.get_profiler_stats()
    }

    with open(results_dir / "performance_analysis.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n✅ Analysis complete! Results saved to {results_dir}/performance_analysis.json")

    # Cleanup
    await kg_manager.shutdown()

    return results

async def identify_optimization_opportunities(analysis_results: Dict[str, Any]) -> List[str]:
    """Identify specific optimization opportunities based on analysis."""

    opportunities = []

    # Check query performance
    query_perf = analysis_results.get('query_performance', {})
    for query, stats in query_perf.items():
        if stats['average_duration'] > 0.1:  # More than 100ms
            opportunities.append(f"Slow query detected ({query}): {stats['average_duration']:.4f}s avg")

    # Check cache efficiency
    kg_stats = analysis_results.get('kg_stats', {})
    cache_hits = kg_stats.get('metrics', {}).get('cache_hits', 0)
    cache_misses = kg_stats.get('metrics', {}).get('cache_misses', 0)
    total_queries = cache_hits + cache_misses

    if total_queries > 0:
        hit_rate = cache_hits / total_queries
        if hit_rate < 0.7:  # Less than 70% hit rate
            opportunities.append(".1%")

    # Check bulk operation performance
    bulk_perf = analysis_results.get('bulk_performance', {})
    avg_add_time = bulk_perf.get('avg_add_time', 0)
    if avg_add_time > 0.01:  # More than 10ms per add
        opportunities.append(".6f")

    return opportunities

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(lambda msg: print(f"[PROFILER] {msg}"), level="INFO")

    # Run analysis
    results = asyncio.run(run_performance_analysis())

    # Identify opportunities
    opportunities = asyncio.run(identify_optimization_opportunities(results))

    print("\n🎯 OPTIMIZATION OPPORTUNITIES:")
    for opp in opportunities:
        print(f"  • {opp}")

    print("\n📝 Next Steps:")
    print("  1. Review the detailed report in kg_performance_results/performance_analysis.json")
    print("  2. Focus on high-severity bottlenecks first")
    print("  3. Implement caching improvements for slow queries")
    print("  4. Consider indexing optimizations for relationship queries")
    print("  5. Profile again after optimizations to measure improvement")
