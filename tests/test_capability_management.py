import pytest
import pytest_asyncio
from agents.core.base_agent import BaseAgent, AgentMessage, AgentStatus
from agents.core.capability_types import Capability, CapabilityType
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS

class TestCapabilityAgent(BaseAgent):
    """Test agent for capability management."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.capability_history = []
    
    async def process_message(self, message):
        if message.message_type == "add_capability":
            capability = message.content["capability"]
            self.capabilities.add(capability)
            self.capability_history.append(("add", capability))
            await self.update_knowledge_graph({
                "agent_id": self.agent_id,
                "action": "add_capability",
                "capability": str(capability),
                "timestamp": message.timestamp
            })
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"status": "success", "capability": str(capability)},
                message_type="capability_response"
            )
        elif message.message_type == "remove_capability":
            capability = message.content["capability"]
            if capability in self.capabilities:
                self.capabilities.remove(capability)
                self.capability_history.append(("remove", capability))
                await self.update_knowledge_graph({
                    "agent_id": self.agent_id,
                    "action": "remove_capability",
                    "capability": str(capability),
                    "timestamp": message.timestamp
                })
                return AgentMessage(
                    sender=self.agent_id,
                    recipient=message.sender,
                    content={"status": "success", "capability": str(capability)},
                    message_type="capability_response"
                )
            else:
                return AgentMessage(
                    sender=self.agent_id,
                    recipient=message.sender,
                    content={"status": "error", "message": "Capability not found"},
                    message_type="error"
                )
        return await super().process_message(message)

@pytest.mark.asyncio
class TestCapabilityManagement:
    """Tests for capability management functionality."""
    
    @pytest_asyncio.fixture
    async def setup_capability_test(self):
        """Set up test environment for capability management."""
        knowledge_graph = Graph()
        agent = TestCapabilityAgent(
            "test_capability_agent",
            capabilities={
                Capability(CapabilityType.TASK_EXECUTION, "1.0"),
                Capability(CapabilityType.KNOWLEDGE_GRAPH_QUERY, "1.0")
            }
        )
        agent.knowledge_graph = knowledge_graph
        await agent.initialize()
        return agent, knowledge_graph
    
    async def test_capability_addition(self, setup_capability_test):
        """Test adding capabilities to an agent."""
        agent, knowledge_graph = setup_capability_test
        
        # Add a new capability
        new_capability = Capability(CapabilityType.KNOWLEDGE_GRAPH_UPDATE, "1.0")
        message = AgentMessage(
            sender="test_sender",
            recipient="test_capability_agent",
            content={"capability": new_capability},
            message_type="add_capability"
        )
        
        response = await agent.process_message(message)
        assert response.message_type == "capability_response"
        assert response.content["status"] == "success"
        assert new_capability in agent.capabilities
        
        # Verify knowledge graph update
        query = """
        SELECT ?agent ?action ?capability
        WHERE {
            ?agent rdf:type core:Agent .
            ?agent core:hasAction ?action .
            ?agent core:hasCapability ?capability .
        }
        """
        results = await agent.query_knowledge_graph(query)
        assert len(results) > 0
        assert any(r["action"] == "add_capability" for r in results)
    
    async def test_capability_removal(self, setup_capability_test):
        """Test removing capabilities from an agent."""
        agent, knowledge_graph = setup_capability_test
        
        # Remove an existing capability
        capability_to_remove = Capability(CapabilityType.TASK_EXECUTION, "1.0")
        message = AgentMessage(
            sender="test_sender",
            recipient="test_capability_agent",
            content={"capability": capability_to_remove},
            message_type="remove_capability"
        )
        
        response = await agent.process_message(message)
        assert response.message_type == "capability_response"
        assert response.content["status"] == "success"
        assert capability_to_remove not in agent.capabilities
        
        # Verify knowledge graph update
        query = """
        SELECT ?agent ?action ?capability
        WHERE {
            ?agent rdf:type core:Agent .
            ?agent core:hasAction ?action .
            ?agent core:hasCapability ?capability .
        }
        """
        results = await agent.query_knowledge_graph(query)
        assert len(results) > 0
        assert any(r["action"] == "remove_capability" for r in results)
    
    async def test_capability_conflicts(self, setup_capability_test):
        """Test handling of capability conflicts."""
        agent, knowledge_graph = setup_capability_test
        
        # Try to add a conflicting capability
        conflicting_capability = Capability(CapabilityType.TASK_EXECUTION, "2.0")
        message = AgentMessage(
            sender="test_sender",
            recipient="test_capability_agent",
            content={"capability": conflicting_capability},
            message_type="add_capability"
        )
        
        response = await agent.process_message(message)
        assert response.message_type == "capability_response"
        assert response.content["status"] == "success"
        
        # Verify that the new version replaced the old one
        assert Capability(CapabilityType.TASK_EXECUTION, "1.0") not in agent.capabilities
        assert Capability(CapabilityType.TASK_EXECUTION, "2.0") in agent.capabilities
        
        # Verify knowledge graph updates
        query = """
        SELECT ?agent ?capability ?version
        WHERE {
            ?agent rdf:type core:Agent .
            ?agent core:hasCapability ?capability .
            ?capability core:hasVersion ?version .
        }
        """
        results = await agent.query_knowledge_graph(query)
        assert len(results) > 0
        assert any(r["version"] == "2.0" for r in results)
    
    async def test_capability_dependencies(self, setup_capability_test):
        """Test capability dependency management."""
        agent, knowledge_graph = setup_capability_test
        
        # Add a capability with dependencies
        dependent_capability = Capability(CapabilityType.KNOWLEDGE_GRAPH_UPDATE, "1.0")
        message = AgentMessage(
            sender="test_sender",
            recipient="test_capability_agent",
            content={
                "capability": dependent_capability,
                "dependencies": [
                    Capability(CapabilityType.KNOWLEDGE_GRAPH_QUERY, "1.0")
                ]
            },
            message_type="add_capability"
        )
        
        response = await agent.process_message(message)
        assert response.message_type == "capability_response"
        assert response.content["status"] == "success"
        assert dependent_capability in agent.capabilities
        
        # Verify knowledge graph updates
        query = """
        SELECT ?agent ?capability ?dependency
        WHERE {
            ?agent rdf:type core:Agent .
            ?agent core:hasCapability ?capability .
            ?capability core:requiresCapability ?dependency .
        }
        """
        results = await agent.query_knowledge_graph(query)
        assert len(results) > 0
        assert any(r["dependency"] == str(Capability(CapabilityType.KNOWLEDGE_GRAPH_QUERY, "1.0")) for r in results) 