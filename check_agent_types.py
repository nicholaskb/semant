#!/usr/bin/env python3
import asyncio
from agents.core.agent_factory import AgentFactory
from kg.models.graph_manager import KnowledgeGraphManager

async def check_registered_agents():
    try:
        kg = KnowledgeGraphManager()
        await kg.initialize()
        factory = AgentFactory(registry=None, knowledge_graph=kg)
        await factory.initialize()
        print('Registered agent types:', list(factory._agent_classes.keys()))
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    asyncio.run(check_registered_agents()) 