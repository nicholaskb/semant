import pytest
import pytest_asyncio
from datetime import datetime
from agents.core.base_agent import BaseAgent, AgentStatus, AgentMessage
from agents.core.capability_types import Capability, CapabilityType
from agents.core.agent_registry import AgentRegistry
from agents.core.agent_factory import AgentFactory
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, XSD
from agents.utils import AwaitableValue

class TestIntegrationAgent(BaseAgent):
    """Test agent for integration testing."""
    
    def __init__(self, agent_id: str, agent_type: str = "integration_test", capabilities=None, config=None, knowledge_graph=None, **kwargs):
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities or {
                Capability(CapabilityType.INTEGRATION_MANAGEMENT)
            },
            config=config,
            knowledge_graph=knowledge_graph,
            **kwargs
        )
        self.integration_status = "active"
        self.message_count = 0
        self.latency = 0.0
        self.graph = self.knowledge_graph
        
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        self.message_count += 1
        self.latency = 0.1  # Simulated latency
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender,
            content={
                "status": "processed",
                "latency": self.latency
            },
            message_type="response"
        )
        
    def update_graph(self):
        # Update knowledge graph with integration metrics
        integration_uri = URIRef(f"integration:{self.agent_id}")
        g = self.knowledge_graph if hasattr(self, "knowledge_graph") and self.knowledge_graph else self.graph
        g.add((integration_uri, RDF.type, URIRef("integration:Integration")))
        g.add((integration_uri, URIRef("integration:hasStatus"), Literal(self.integration_status)))
        g.add((integration_uri, URIRef("integration:hasMessageCount"), Literal(self.message_count, datatype=XSD.integer)))
        g.add((integration_uri, URIRef("integration:hasMessageLatency"), Literal(self.latency, datatype=XSD.float)))
        
    async def query_knowledge_graph(self, query: dict) -> dict:
        return {}

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        return await self.process_message(message)

class TestModuleAgent(BaseAgent):
    """Test agent for module management testing."""
    
    def __init__(self, agent_id: str, agent_type: str = "module_test", capabilities=None, config=None, knowledge_graph=None, **kwargs):
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities or {
                Capability(CapabilityType.MODULE_MANAGEMENT)
            },
            config=config,
            knowledge_graph=knowledge_graph,
            **kwargs
        )
        self.module_status = "loaded"
        self.load_time = 0.0
        self.dependencies = set()
        self.graph = self.knowledge_graph
        
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        # Handle module operations
        if message.content.get("operation") == "load":
            self.module_status = "loaded"
            self.load_time = message.content.get("load_time", 0.0)
        elif message.content.get("operation") == "unload":
            self.module_status = "unloaded"
        elif message.content.get("operation") == "add_dependency":
            self.dependencies.add(message.content["dependency"])
            
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender,
            content={
                "status": "processed",
                "module_status": self.module_status,
                "load_time": self.load_time,
                "dependencies": list(self.dependencies)
            },
            message_type="response"
        )
        
    def update_graph(self):
        # Update knowledge graph with module metrics
        module_uri = URIRef(f"module:{self.agent_id}")
        g = self.knowledge_graph if hasattr(self, "knowledge_graph") and self.knowledge_graph else self.graph
        g.add((module_uri, RDF.type, URIRef("module:Module")))
        g.add((module_uri, URIRef("module:hasStatus"), Literal(self.module_status)))
        g.add((module_uri, URIRef("module:hasLoadTime"), Literal(self.load_time, datatype=XSD.float)))
        
        # Add dependencies
        for dep in self.dependencies:
            dep_uri = URIRef(f"module:{dep}")
            g.add((module_uri, URIRef("module:hasDependency"), dep_uri))
        
    async def query_knowledge_graph(self, query: dict) -> dict:
        return {}

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        return await self.process_message(message)

@pytest_asyncio.fixture
async def setup_integration_test():
    """Set up test environment for integration testing."""
    registry = AgentRegistry()
    knowledge_graph = Graph()
    factory = AgentFactory(registry, knowledge_graph)
    
    # Register test agent templates
    await factory.register_agent_template(
        "integration_test",
        TestIntegrationAgent,
        {CapabilityType.INTEGRATION_MANAGEMENT}
    )
    
    await factory.register_agent_template(
        "module_test",
        TestModuleAgent,
        {CapabilityType.MODULE_MANAGEMENT}
    )
    
    return AwaitableValue((registry, knowledge_graph, factory))

@pytest.mark.asyncio
async def test_integration_management(setup_integration_test):
    """Test integration management functionality."""
    registry, knowledge_graph, factory = await setup_integration_test
    
    # Create integration agent
    agent = await factory.create_agent("integration_test", knowledge_graph=knowledge_graph)
    
    # Test message processing
    result = await agent.process_message(AgentMessage(
        sender_id="test_agent",
        recipient_id=agent.agent_id,
        content={},
        message_type="test"
    ))
    assert result.message_type == "response"
    assert result.content["status"] == "processed"
    assert result.content["latency"] > 0
    
    # Test knowledge graph updates
    agent.update_graph()
    status = list(knowledge_graph.triples((URIRef(f"integration:{agent.agent_id}"), URIRef("integration:hasStatus"), None)))[0][2]
    assert str(status) == "active"
    
    message_count = list(knowledge_graph.triples((URIRef(f"integration:{agent.agent_id}"), URIRef("integration:hasMessageCount"), None)))[0][2]
    assert int(message_count) == 1

@pytest.mark.asyncio
async def test_module_management(setup_integration_test):
    """Test module management functionality."""
    registry, knowledge_graph, factory = await setup_integration_test
    
    # Create module agent
    agent = await factory.create_agent("module_test", knowledge_graph=knowledge_graph)
    
    # Test module loading
    result = await agent.process_message(AgentMessage(
        sender_id="test_agent",
        recipient_id=agent.agent_id,
        content={
            "operation": "load",
            "load_time": 0.5
        },
        message_type="test"
    ))
    assert result.message_type == "response"
    assert result.content["module_status"] == "loaded"
    assert result.content["load_time"] == 0.5
    
    # Test dependency management
    result = await agent.process_message(AgentMessage(
        sender_id="test_agent",
        recipient_id=agent.agent_id,
        content={
            "operation": "add_dependency",
            "dependency": "test_dependency"
        },
        message_type="test"
    ))
    assert "test_dependency" in result.content["dependencies"]
    
    # Test knowledge graph updates
    agent.update_graph()
    status = list(knowledge_graph.triples((URIRef(f"module:{agent.agent_id}"), URIRef("module:hasStatus"), None)))[0][2]
    assert str(status) == "loaded"
    
    load_time = list(knowledge_graph.triples((URIRef(f"module:{agent.agent_id}"), URIRef("module:hasLoadTime"), None)))[0][2]
    assert float(load_time) > 0
    
    # Test module unloading
    result = await agent.process_message(AgentMessage(
        sender_id="test_agent",
        recipient_id=agent.agent_id,
        content={
            "operation": "unload"
        },
        message_type="test"
    ))
    assert result.message_type == "response"
    assert result.content["module_status"] == "unloaded"

@pytest.mark.asyncio
async def test_integration_metrics(setup_integration_test):
    """Test integration metrics tracking."""
    registry, knowledge_graph, factory = await setup_integration_test
    
    # Create integration agent
    agent = await factory.create_agent("integration_test", knowledge_graph=knowledge_graph)
    
    # Process multiple messages
    for _ in range(3):
        await agent.process_message(AgentMessage(
            sender_id="test_agent",
            recipient_id=agent.agent_id,
            content={},
            message_type="test"
        ))
    
    # Update metrics
    agent.update_graph()
    
    # Verify metrics in knowledge graph
    message_count = list(knowledge_graph.triples((URIRef(f"integration:{agent.agent_id}"), URIRef("integration:hasMessageCount"), None)))[0][2]
    assert int(message_count) == 3
    
    latency = list(knowledge_graph.triples((URIRef(f"integration:{agent.agent_id}"), URIRef("integration:hasMessageLatency"), None)))[0][2]
    assert float(latency) > 0 