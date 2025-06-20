import pytest
import pytest_asyncio
from agents.core.base_agent import BaseAgent, AgentMessage, AgentStatus
from agents.core.capability_types import Capability, CapabilityType
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, RDFS
from typing import Dict, Any
from agents.core.agent_registry import AgentRegistry
from agents.core.agent_factory import AgentFactory
from kg.models.graph_manager import KnowledgeGraphManager
import time
import uuid
from datetime import datetime
from agents.core.message_types import AgentMessage

class TestCapabilityAgent(BaseAgent):
    """Test agent for capability management."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.capability_history = []
        self._knowledge_graph = KnowledgeGraphManager()
    
    async def initialize(self) -> None:
        """Initialize the agent."""
        if not self._is_initialized:
            await super().initialize()
            await self._knowledge_graph.initialize()
            self._is_initialized = True
    
    async def process_message(self, message):
        if not self._is_initialized:
            await self.initialize()
            
        if message.message_type == "add_capability":
            capability = message.content["capability"]
            # Ensure capability is a Capability object
            if not isinstance(capability, Capability):
                capability = Capability(CapabilityType(capability)) if capability in CapabilityType.__members__.values() else Capability(CapabilityType.MESSAGE_PROCESSING, str(capability))
            # Check for version conflicts and remove older versions of same capability type
            current_capabilities = await self.get_capabilities()
            for existing_cap in list(current_capabilities):
                if (existing_cap.type == capability.type and 
                    existing_cap != capability):
                    await self.remove_capability(existing_cap)
                    self.capability_history.append(("remove", existing_cap))
            
            # Actually add capability to the agent
            await self.add_capability(capability)
            self.capability_history.append(("add", capability))
            await self.update_knowledge_graph({
                "agent_id": self.agent_id,
                "action": "add_capability",
                "capability": str(capability),
                "timestamp": message.timestamp
            })
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"status": "success", "capability": str(capability)},
                message_type="capability_response"
            )
        elif message.message_type == "remove_capability":
            capability = message.content["capability"]
            if not isinstance(capability, Capability):
                capability = Capability(CapabilityType(capability)) if capability in CapabilityType.__members__.values() else Capability(CapabilityType.MESSAGE_PROCESSING, str(capability))
            capabilities = await self.get_capabilities()
            if capability in capabilities:
                await self.remove_capability(capability)
                self.capability_history.append(("remove", capability))
                await self.update_knowledge_graph({
                    "agent_id": self.agent_id,
                    "action": "remove_capability",
                    "capability": str(capability),
                    "timestamp": message.timestamp
                })
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    content={"status": "success", "capability": str(capability)},
                    message_type="capability_response"
                )
            else:
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    content={"status": "error", "message": "Capability not found"},
                    message_type="error"
                )
        return await super().process_message(message)

    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query knowledge graph and track capabilities."""
        if not self._is_initialized:
            await self.initialize()
        try:
            if isinstance(query, dict) and "sparql" in query:
                return await self._knowledge_graph.query_graph(query["sparql"])
            else:
                # Handle simple query format
                subject = query.get("agent_id")
                predicate = query.get("action")
                if subject and predicate:
                    sparql = f"""
                    SELECT ?object WHERE {{
                        <http://example.org/agent/{subject}> <http://example.org/agent/{predicate}> ?object .
                    }}
                    """
                    result = await self._knowledge_graph.query_graph(sparql)
                    # Convert result format for tests
                    if result and len(result) > 0:
                        return {"capability": result[0]['object']}
                    return {}
                return {}
        except Exception as e:
            self.logger.error(f"Error querying knowledge graph: {str(e)}")
            return {}

    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update knowledge graph and track capabilities."""
        if not self._is_initialized:
            await self.initialize()
        try:
            agent_uri = f"http://example.org/agent/{update_data['agent_id']}"
            action = update_data['action']
            capability = update_data['capability']
            timestamp = update_data.get('timestamp', time.time())
            
            # Add triple to knowledge graph
            await self._knowledge_graph.add_triple(
                agent_uri,
                f"http://example.org/agent/{action}",
                capability
            )
            
            # Add timestamp
            await self._knowledge_graph.add_triple(
                agent_uri,
                "http://example.org/agent/timestamp",
                str(timestamp)
            )
        except Exception as e:
            self.logger.error(f"Error updating knowledge graph: {str(e)}")
            raise

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._is_initialized:
            await self._knowledge_graph.cleanup()
            await super().cleanup()


    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages - REQUIRED IMPLEMENTATION."""
        try:
            # Process the message based on its type and content
            response_content = f"Agent {self.agent_id} processed: {message.content}"
            
            return AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=response_content,
                message_type=getattr(message, 'message_type', 'response'),
                timestamp=datetime.now()
            )
        except Exception as e:
            # Error handling
            return AgentMessage(
                message_id=str(uuid.uuid4()),
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content=f"Error processing message: {str(e)}",
                message_type="error",
                timestamp=datetime.now()
            )

@pytest.mark.asyncio
class TestCapabilityManagement:
    """Tests for capability management functionality."""
    
    @pytest_asyncio.fixture(scope="function")
    async def setup_test_environment(self):
        """Set up test environment with registered agent types."""
        registry = AgentRegistry()
        knowledge_graph = KnowledgeGraphManager()
        factory = AgentFactory(registry, knowledge_graph)
        
        await registry.initialize()
        await knowledge_graph.initialize()
        await factory.initialize()
        
        # Register test agent types
        await factory.register_agent_template(
            "test_agent",
            TestCapabilityAgent,
            {Capability(CapabilityType.KNOWLEDGE_GRAPH)}
        )
        
        await factory.register_agent_template(
            "capability_agent",
            TestCapabilityAgent,
            {Capability(CapabilityType.KNOWLEDGE_GRAPH)}
        )
        
        await factory.register_agent_template(
            "supervisor",
            TestCapabilityAgent,
            {Capability(CapabilityType.KNOWLEDGE_GRAPH)}
        )
        
        await factory.register_agent_template(
            "worker_0",
            TestCapabilityAgent,
            {Capability(CapabilityType.KNOWLEDGE_GRAPH)}
        )
        
        await factory.register_agent_template(
            "monitor",
            TestCapabilityAgent,
            {Capability(CapabilityType.KNOWLEDGE_GRAPH)}
        )
        
        await factory.register_agent_template(
            "test_capability_agent",
            TestCapabilityAgent,
            {Capability(CapabilityType.KNOWLEDGE_GRAPH)}
        )
        
        yield registry, knowledge_graph, factory
        
        # Cleanup
        await registry.cleanup()
        await knowledge_graph.cleanup()
    
    @pytest_asyncio.fixture
    async def setup_capability_test(self, setup_test_environment):
        """Set up test environment for capability management."""
        registry, knowledge_graph, factory = setup_test_environment
        agent = await factory.create_agent(
            "test_capability_agent",
            agent_id="test_agent_1",
            capabilities={Capability(CapabilityType.KNOWLEDGE_GRAPH)}
        )
        await agent.initialize()
        return agent, registry, knowledge_graph, factory
    
    @pytest.mark.asyncio
    async def test_add_capability(self, setup_capability_test):
        """Test adding a capability to an agent."""
        agent, *_ = setup_capability_test
        test_cap = Capability(CapabilityType.MESSAGE_PROCESSING, "test_capability")
        message = AgentMessage(
            sender_id="test_sender",
            recipient_id=agent.agent_id,
            content={"capability": test_cap},
            message_type="add_capability"
        )
        response = await agent.process_message(message)
        assert response.message_type == "capability_response"
        assert response.content["status"] == "success"
        capabilities = await agent.get_capabilities()
        assert test_cap in capabilities
        assert len(agent.capability_history) == 1
        assert agent.capability_history[0][0] == "add"
        assert agent.capability_history[0][1] == test_cap

    @pytest.mark.asyncio
    async def test_remove_capability(self, setup_capability_test):
        """Test removing a capability from an agent."""
        agent, *_ = setup_capability_test
        test_cap = Capability(CapabilityType.MESSAGE_PROCESSING, "test_capability")
        # First add a capability
        add_message = AgentMessage(
            sender_id="test_sender",
            recipient_id=agent.agent_id,
            content={"capability": test_cap},
            message_type="add_capability"
        )
        await agent.process_message(add_message)
        # Then remove it
        remove_message = AgentMessage(
            sender_id="test_sender",
            recipient_id=agent.agent_id,
            content={"capability": test_cap},
            message_type="remove_capability"
        )
        response = await agent.process_message(remove_message)
        assert response.message_type == "capability_response"
        assert response.content["status"] == "success"
        capabilities = await agent.get_capabilities()
        assert test_cap not in capabilities
        assert len(agent.capability_history) == 2
        assert agent.capability_history[1][0] == "remove"
        assert agent.capability_history[1][1] == test_cap

    @pytest.mark.asyncio
    async def test_remove_nonexistent_capability(self, setup_capability_test):
        """Test removing a capability that doesn't exist."""
        agent, *_ = setup_capability_test
        test_cap = Capability(CapabilityType.MESSAGE_PROCESSING, "nonexistent_capability")
        message = AgentMessage(
            sender_id="test_sender",
            recipient_id=agent.agent_id,
            content={"capability": test_cap},
            message_type="remove_capability"
        )
        response = await agent.process_message(message)
        assert response.message_type == "error"
        assert response.content["status"] == "error"
        assert response.content["message"] == "Capability not found"
        assert len(agent.capability_history) == 0

    @pytest.mark.asyncio
    async def test_knowledge_graph_updates(self, setup_capability_test):
        """Test that capability changes are reflected in the knowledge graph."""
        agent, *_ = setup_capability_test
        test_cap = Capability(CapabilityType.MESSAGE_PROCESSING, "test_capability")
        # Add a capability
        add_message = AgentMessage(
            sender_id="test_sender",
            recipient_id=agent.agent_id,
            content={"capability": test_cap},
            message_type="add_capability"
        )
        await agent.process_message(add_message)
        # Query knowledge graph
        query = {
            "agent_id": agent.agent_id,
            "action": "add_capability"
        }
        result = await agent.query_knowledge_graph(query)
        assert result is not None
        assert "capability" in result
        assert result["capability"] == str(test_cap)
        # Remove capability
        remove_message = AgentMessage(
            sender_id="test_sender",
            recipient_id=agent.agent_id,
            content={"capability": test_cap},
            message_type="remove_capability"
        )
        await agent.process_message(remove_message)
        # Query knowledge graph again
        query = {
            "agent_id": agent.agent_id,
            "action": "remove_capability"
        }
        result = await agent.query_knowledge_graph(query)
        assert result is not None
        assert "capability" in result
        assert result["capability"] == str(test_cap)

    @pytest.mark.asyncio
    async def test_capability_conflicts(self, setup_capability_test):
        """Test handling of capability conflicts."""
        agent, *_ = setup_capability_test
        cap_v1 = Capability(CapabilityType.TASK_EXECUTION, "1.0")
        cap_v2 = Capability(CapabilityType.TASK_EXECUTION, "2.0")
        # Add v1
        add_message_v1 = AgentMessage(
            sender_id="test_sender",
            recipient_id=agent.agent_id,
            content={"capability": cap_v1},
            message_type="add_capability"
        )
        await agent.process_message(add_message_v1)
        # Add v2 (should replace v1)
        add_message_v2 = AgentMessage(
            sender_id="test_sender",
            recipient_id=agent.agent_id,
            content={"capability": cap_v2},
            message_type="add_capability"
        )
        response = await agent.process_message(add_message_v2)
        assert response.message_type == "capability_response"
        assert response.content["status"] == "success"
        capabilities = await agent.get_capabilities()
        assert cap_v1 not in capabilities
        assert cap_v2 in capabilities
        # Verify knowledge graph updates
        query = {
            "agent_id": agent.agent_id,
            "action": "add_capability"
        }
        result = await agent.query_knowledge_graph(query)
        assert result is not None
        assert "capability" in result
        assert result["capability"] == str(cap_v2)

    @pytest.mark.asyncio
    async def test_capability_dependencies(self, setup_capability_test):
        """Test capability dependency management."""
        agent, *_ = setup_capability_test
        dep_cap = Capability(CapabilityType.KNOWLEDGE_GRAPH_UPDATE, "1.0")
        dependency = Capability(CapabilityType.KNOWLEDGE_GRAPH_QUERY, "1.0")
        message = AgentMessage(
            sender_id="test_sender",
            recipient_id=agent.agent_id,
            content={
                "capability": dep_cap,
                "dependencies": [dependency]
            },
            message_type="add_capability"
        )
        response = await agent.process_message(message)
        assert response.message_type == "capability_response"
        assert response.content["status"] == "success"
        capabilities = await agent.get_capabilities()
        assert dep_cap in capabilities
        # Verify knowledge graph updates
        query = {
            "agent_id": agent.agent_id,
            "action": "add_capability"
        }
        result = await agent.query_knowledge_graph(query)
        assert result is not None
        assert "capability" in result
        assert result["capability"] == str(dep_cap) 