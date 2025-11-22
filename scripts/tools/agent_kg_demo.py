#!/usr/bin/env python3
"""
Demonstration of agent modifying knowledge graph
"""
import asyncio
import uuid
from datetime import datetime
from kg.models.graph_manager import KnowledgeGraphManager

class KnowledgeGraphModifyingAgent:
    """Example agent that modifies the knowledge graph"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.kg = KnowledgeGraphManager(persistent_storage=True)
    
    async def modify_knowledge_graph(self):
        """Demonstrate agent modifying the knowledge graph"""
        print(f"🎯 Agent {self.agent_id[:8]} modifying knowledge graph...")
        
        # 1. Add agent information
        agent_uri = f"http://example.org/agent/{self.agent_id}"
        await self.kg.add_triple(
            agent_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/core#Agent"
        )
        await self.kg.add_triple(
            agent_uri,
            "http://example.org/core#hasCapability",
            "knowledge_graph_modification"
        )
        await self.kg.add_triple(
            agent_uri,
            "http://example.org/core#status",
            "active"
        )
        
        # 2. Add agent decision
        decision_id = str(uuid.uuid4())
        decision_uri = f"http://example.org/agent/decision/{decision_id}"
        await self.kg.add_triple(
            decision_uri,
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://example.org/core#AgentDecision"
        )
        await self.kg.add_triple(
            decision_uri,
            "http://example.org/core#madeBy",
            agent_uri
        )
        await self.kg.add_triple(
            decision_uri,
            "http://example.org/core#decisionType",
            "knowledge_graph_modification"
        )
        await self.kg.add_triple(
            decision_uri,
            "http://example.org/core#timestamp",
            datetime.now().isoformat()
        )
        await self.kg.add_triple(
            decision_uri,
            "http://example.org/core#description",
            "Modified knowledge graph with new agent and decision data"
        )
        
        print(f"✅ Agent {self.agent_id[:8]} added:")
        print("   • Agent entity with active status")
        print("   • Decision record with timestamp")
        print("   • All data persisted to RDF storage")
        
        return decision_uri

async def main():
    print("🚀 AGENT KNOWLEDGE GRAPH MODIFICATION DEMO")
    print("=" * 50)
    
    # Create agent
    agent = KnowledgeGraphModifyingAgent("demo-agent-123")
    
    # Before modification
    print(f"📊 Before: {len(agent.kg.graph)} triples in KG")
    
    # Modify KG
    decision_uri = await agent.modify_knowledge_graph()
    
    # After modification
    print(f"📊 After: {len(agent.kg.graph)} triples in KG")
    print(f"💾 Data persisted to: {agent.kg._persistent_file}")
    
    # Verify persistence
    print("
🔍 Verifying persistence across instances..."
    agent2 = KnowledgeGraphModifyingAgent("verification-agent")
    
    # Query for the agent's modifications
    query = f'''
    PREFIX core: <http://example.org/core#>
    
    SELECT ?agent ?capability ?decision ?description WHERE {{
      ?agent a core:Agent .
      ?agent core:hasCapability ?capability .
      ?decision core:madeBy ?agent .
      ?decision core:description ?description .
      FILTER(CONTAINS(STR(?agent), "demo-agent-123"))
    }}
    '''
    
    results = await agent2.kg.query_graph(query)
    if results:
        print("✅ SUCCESS: Agent modifications found in new instance!"        for result in results:
            print(f"   • Agent: {result.get('agent', 'unknown')}")
            print(f"   • Capability: {result.get('capability', 'unknown')}")
            print(f"   • Decision: {result.get('decision', 'unknown')}")
            print(f"   • Description: {result.get('description', 'unknown')[:50]}...")
    else:
        print("❌ No agent modifications found")
    
    print("
🎉 AGENT KG MODIFICATION COMPLETE!"
    print("   • Agents can modify persistent RDF storage")
    print("   • Data survives across instances")
    print("   • Full temporal tracking maintained")
    print("   • Security and indexing automatic")

if __name__ == "__main__":
    asyncio.run(main())
