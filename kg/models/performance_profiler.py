"""
Performance profiler for Knowledge Graph operations.
Identifies bottlenecks and provides optimization recommendations.
"""

import asyncio
import time
import cProfile
import pstats
import io
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
from dataclasses import dataclass, field
from loguru import logger

from .graph_manager import KnowledgeGraphManager

@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    operation_name: str
    start_time: float
    end_time: float
    duration: float = field(init=False)
    memory_usage: Optional[int] = None
    cache_hit_rate: float = 0.0
    query_complexity: int = 0

    def __post_init__(self):
        self.duration = self.end_time - self.start_time

@dataclass
class BottleneckAnalysis:
    """Analysis of identified bottlenecks."""
    operation: str
    average_duration: float
    call_count: int
    severity: str  # 'low', 'medium', 'high', 'critical'
    recommendation: str

class KGPerformanceProfiler:
    """Performance profiler for Knowledge Graph operations."""

    def __init__(self, kg_manager: KnowledgeGraphManager):
        self.kg_manager = kg_manager
        self.metrics: List[PerformanceMetrics] = []
        self.profiler = cProfile.Profile()
        self.logger = logger.bind(component="KGPerformanceProfiler")

    @contextmanager
    def profile_operation(self, operation_name: str):
        """Context manager to profile a specific operation."""
        start_time = time.time()
        self.profiler.enable()

        try:
            yield
        finally:
            self.profiler.disable()
            end_time = time.time()

            metric = PerformanceMetrics(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time
            )

            # Get cache stats if available
            if hasattr(self.kg_manager, 'cache'):
                cache_stats = self.kg_manager.metrics
                total_queries = cache_stats.get('cache_hits', 0) + cache_stats.get('cache_misses', 0)
                if total_queries > 0:
                    metric.cache_hit_rate = cache_stats.get('cache_hits', 0) / total_queries

            self.metrics.append(metric)
            self.logger.info(f"Profiled {operation_name}: {metric.duration:.4f}s")

    async def profile_query_performance(self, queries: List[str], iterations: int = 10) -> Dict[str, Any]:
        """Profile performance of common SPARQL queries."""
        results = {}

        for query in queries:
            durations = []

            # Warm up cache
            await self.kg_manager.query_graph(query)

            for _ in range(iterations):
                with self.profile_operation(f"query_{hash(query) % 1000}"):
                    await self.kg_manager.query_graph(query)
                durations.append(self.metrics[-1].duration)

            avg_duration = sum(durations) / len(durations)
            results[query[:50] + "..."] = {
                'average_duration': avg_duration,
                'min_duration': min(durations),
                'max_duration': max(durations),
                'iterations': iterations
            }

        return results

    async def profile_mutation_performance(self, operations: List[Dict[str, Any]], iterations: int = 5) -> Dict[str, Any]:
        """Profile performance of mutation operations (add/remove triples)."""
        results = {}

        for op in operations:
            durations = []
            operation_name = op.get('type', 'unknown')

            for _ in range(iterations):
                if operation_name == 'add':
                    with self.profile_operation("add_triple"):
                        await self.kg_manager.add_triple(
                            op['subject'], op['predicate'], op['object']
                        )
                elif operation_name == 'remove':
                    with self.profile_operation("remove_triple"):
                        await self.kg_manager.remove_triple(op['subject'], op['predicate'])

                durations.append(self.metrics[-1].duration)

            avg_duration = sum(durations) / len(durations)
            results[f"{operation_name}_{hash(str(op)) % 1000}"] = {
                'average_duration': avg_duration,
                'min_duration': min(durations),
                'max_duration': max(durations),
                'iterations': iterations
            }

        return results

    async def profile_bulk_operations(self, bulk_size: int = 100) -> Dict[str, Any]:
        """Profile bulk operations performance."""
        # Generate test triples
        test_triples = []
        for i in range(bulk_size):
            test_triples.append({
                'subject': f'http://example.org/test/entity_{i}',
                'predicate': 'http://example.org/test#hasProperty',
                'object': f'value_{i}'
            })

        # Profile bulk add
        start_time = time.time()
        for triple in test_triples:
            await self.kg_manager.add_triple(
                triple['subject'], triple['predicate'], triple['object']
            )
        bulk_add_time = time.time() - start_time

        # Profile bulk query
        start_time = time.time()
        for triple in test_triples[:10]:  # Query first 10
            await self.kg_manager.query_graph(f"""
                SELECT ?o WHERE {{
                    <{triple['subject']}> <{triple['predicate']}> ?o
                }}
            """)
        bulk_query_time = time.time() - start_time

        return {
            'bulk_add_time': bulk_add_time,
            'bulk_query_time': bulk_query_time,
            'avg_add_time': bulk_add_time / bulk_size,
            'avg_query_time': bulk_query_time / 10
        }

    def analyze_bottlenecks(self) -> List[BottleneckAnalysis]:
        """Analyze collected metrics to identify bottlenecks."""
        bottlenecks = []

        # Group metrics by operation
        operation_metrics = {}
        for metric in self.metrics:
            if metric.operation_name not in operation_metrics:
                operation_metrics[metric.operation_name] = []
            operation_metrics[metric.operation_name].append(metric)

        for operation, metrics_list in operation_metrics.items():
            avg_duration = sum(m.duration for m in metrics_list) / len(metrics_list)
            call_count = len(metrics_list)

            # Determine severity based on duration and call count
            if avg_duration > 1.0 and call_count > 10:
                severity = 'critical'
                recommendation = "High-frequency operation with slow performance. Consider caching or indexing optimization."
            elif avg_duration > 0.5:
                severity = 'high'
                recommendation = "Slow operation. Review query complexity and consider optimization."
            elif avg_duration > 0.1:
                severity = 'medium'
                recommendation = "Moderate performance. Monitor for regression."
            else:
                severity = 'low'
                recommendation = "Acceptable performance."

            bottlenecks.append(BottleneckAnalysis(
                operation=operation,
                average_duration=avg_duration,
                call_count=call_count,
                severity=severity,
                recommendation=recommendation
            ))

        # Sort by severity and duration
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        bottlenecks.sort(key=lambda x: (severity_order[x.severity], x.average_duration), reverse=True)

        return bottlenecks

    def generate_report(self) -> str:
        """Generate a comprehensive performance report."""
        bottlenecks = self.analyze_bottlenecks()

        report = []
        report.append("=" * 60)
        report.append("KNOWLEDGE GRAPH PERFORMANCE REPORT")
        report.append("=" * 60)
        report.append("")

        # Summary stats
        total_operations = len(self.metrics)
        total_time = sum(m.duration for m in self.metrics)
        avg_time = total_time / total_operations if total_operations > 0 else 0

        report.append("SUMMARY STATISTICS:")
        report.append(f"  Total operations profiled: {total_operations}")
        report.append(".4f")
        report.append(".4f")
        report.append("")

        # Bottlenecks
        report.append("IDENTIFIED BOTTLENECKS:")
        for bottleneck in bottlenecks[:10]:  # Top 10
            report.append(f"  {bottleneck.operation}:")
            report.append(".4f")
            report.append(f"    Severity: {bottleneck.severity.upper()}")
            report.append(f"    Recommendation: {bottleneck.recommendation}")
            report.append("")

        # Cache analysis
        cache_hits = sum(1 for m in self.metrics if m.cache_hit_rate > 0)
        cache_misses = len(self.metrics) - cache_hits
        if cache_hits + cache_misses > 0:
            hit_rate = cache_hits / (cache_hits + cache_misses)
            report.append("CACHE ANALYSIS:")
            report.append(".2%")
            report.append("")

        return "\n".join(report)

    def get_profiler_stats(self) -> str:
        """Get detailed profiler statistics."""
        s = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # Top 20 functions
        return s.getvalue()

