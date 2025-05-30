import asyncio
import os
from kg.models.graph_manager import KnowledgeGraphManager

async def main():
    kg = KnowledgeGraphManager()
    data = await kg.export_graph()
    os.makedirs("kg/data", exist_ok=True)
    with open("kg/data/initial_graph.ttl", "w") as f:
        f.write(data)
    print("Knowledge graph initialized at kg/data/initial_graph.ttl")

if __name__ == "__main__":
    asyncio.run(main())
