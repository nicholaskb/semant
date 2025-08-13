import asyncio
import cProfile
import pstats
import io
from loguru import logger
from semant.kg.models.graph_manager import KnowledgeGraphManager

# Configure Loguru for minimal output during profiling
logger.remove()
logger.add(lambda msg: None, level="INFO")

async def setup_kg_with_data(kg: KnowledgeGraphManager, num_triples: int):
    """Adds a specified number of test triples to the knowledge graph."""
    logger.info(f"Setting up KG with {num_triples} triples...")
    for i in range(num_triples):
        await kg.add_triple(
            subject=f"http://example.org/subject/{i}",
            predicate=f"http://example.org/predicate/{i % 10}",
            object=f"Object {i}"
        )
    logger.info("KG setup complete.")

async def profile_read_operations(kg: KnowledgeGraphManager, num_queries: int):
    """Profiles read-heavy operations by executing a number of SPARQL queries."""
    logger.info(f"Profiling {num_queries} read operations...")
    query = """
    SELECT ?subject ?predicate ?object
    WHERE { ?subject ?predicate ?object }
    LIMIT 10
    """
    for _ in range(num_queries):
        await kg.query_graph(query)
    logger.info("Read profiling complete.")

async def profile_write_operations(kg: KnowledgeGraphManager, num_writes: int):
    """Profiles write-heavy operations by adding new triples."""
    logger.info(f"Profiling {num_writes} write operations...")
    for i in range(num_writes):
        await kg.add_triple(
            subject=f"http://example.org/new_subject/{i}",
            predicate="http://example.org/new_predicate/1",
            object=f"New Object {i}"
        )
    logger.info("Write profiling complete.")

async def main():
    """Main function to run the profiling."""
    kg = KnowledgeGraphManager()
    await kg.initialize()

    # --- Profiling Setup ---
    profiler = cProfile.Profile()
    
    # --- Profile Data Loading ---
    logger.info("--- Profiling Data Loading ---")
    profiler.enable()
    await setup_kg_with_data(kg, 1000)
    profiler.disable()

    s = io.StringIO()
    sortby = pstats.SortKey.CUMULATIVE
    ps = pstats.Stats(profiler, stream=s).sort_stats(sortby)
    ps.print_stats(20)
    print(s.getvalue())

    # --- Profile Read Operations ---
    logger.info("--- Profiling Read Operations (with cache) ---")
    profiler.enable()
    await profile_read_operations(kg, 500)
    profiler.disable()
    
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(sortby)
    ps.print_stats(20)
    print(s.getvalue())

    # --- Profile Write Operations ---
    logger.info("--- Profiling Write Operations (with cache invalidation) ---")
    profiler.enable()
    await profile_write_operations(kg, 100)
    profiler.disable()

    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(sortby)
    ps.print_stats(20)
    print(s.getvalue())

    # --- Print Final KG Stats ---
    logger.info("--- Final Knowledge Graph Statistics ---")
    stats = await kg.get_stats()
    print(stats)

    await kg.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

