import asyncio
from demo_research import setup_demo_graph

async def main():
    graph = await setup_demo_graph()
    print("Triples in the knowledge graph:")
    for s, p, o in graph:
        print(f"{s} {p} {o}")

if __name__ == "__main__":
    asyncio.run(main()) 