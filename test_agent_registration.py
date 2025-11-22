#!/usr/bin/env python3
import asyncio
from agents.core.agent_factory import AgentFactory
from kg.models.graph_manager import KnowledgeGraphManager
from tests.utils.test_agents import TestAgent, TestCapabilityAgent

async def test_agent_registration():
    try:
        print("1. Initializing knowledge graph...")
        kg = KnowledgeGraphManager()
        await kg.initialize()
        
        print("2. Initializing agent factory...")
        factory = AgentFactory(registry=None, knowledge_graph=kg)
        await factory.initialize()
        
        print("3. Registering test agent templates...")
        await factory.register_agent_template("test_agent", TestAgent)
        await factory.register_agent_template("capability_agent", TestCapabilityAgent)
        
        print("4. Checking registered agent types...")
        registered_types = list(factory._agent_classes.keys())
        print(f"Registered agent types: {registered_types}")
        
        if "test_agent" in registered_types:
            print("5. Testing agent creation...")
            agent = await factory.create_agent("test_agent", "test_1")
            print(f"✅ Successfully created agent: {agent.agent_id}")
        else:
            print("❌ test_agent not registered properly")
            
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent_registration()) 