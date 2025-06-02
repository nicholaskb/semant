import pytest
import pytest_asyncio
from datetime import datetime
from agents.core.base_agent import BaseAgent, AgentStatus, AgentMessage
from agents.core.capability_types import Capability, CapabilityType
from agents.core.agent_registry import AgentRegistry
from agents.core.agent_factory import AgentFactory
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, XSD

class TestSecurityAgent(BaseAgent):
    """Test agent for security and audit testing."""
    
    def __init__(self, agent_id: str, agent_type: str = "security_test", capabilities=None, config=None):
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities or {
                Capability(CapabilityType.SECURITY_CHECK)
            },
            config=config
        )
        self.audit_log = []
        
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        # Log the message for audit
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "sender": message.sender,
            "message_type": message.message_type,
            "content": message.content
        })
        
        # Check security level
        if message.content.get("security_level", "low") == "high":
            if not self.config.get("has_high_security_access", False):
                return AgentMessage(
                    sender=self.agent_id,
                    recipient=message.sender,
                    content={"error": "Insufficient security level"},
                    message_type="error"
                )
        
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"status": "processed", "audit_id": len(self.audit_log)},
            message_type="response"
        )
        
    async def update_knowledge_graph(self, update_data: dict) -> None:
        # Update audit log in knowledge graph
        audit_uri = URIRef(f"audit:{len(self.audit_log)}")
        self.knowledge_graph.add((audit_uri, RDF.type, URIRef("audit:AuditEntry")))
        self.knowledge_graph.add((audit_uri, URIRef("audit:timestamp"), Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))
        self.knowledge_graph.add((audit_uri, URIRef("audit:action"), Literal(update_data.get("action", "unknown"))))
        
    async def query_knowledge_graph(self, query: dict) -> dict:
        return {}

@pytest_asyncio.fixture
async def setup_security_test():
    """Set up test environment for security testing."""
    registry = AgentRegistry()
    knowledge_graph = Graph()
    factory = AgentFactory(registry, knowledge_graph)
    
    # Register test agent template
    await factory.register_agent_template(
        "security_test",
        TestSecurityAgent,
        {CapabilityType.SECURITY_CHECK}
    )
    
    return registry, knowledge_graph, factory

@pytest.mark.asyncio
async def test_security_levels(setup_security_test):
    """Test security level enforcement."""
    registry, knowledge_graph, factory = await setup_security_test
    
    # Create agent with security configuration
    agent = await factory.create_agent(
        "security_test",
        config={"has_high_security_access": False}
    )
    
    # Test low security message
    message = AgentMessage(
        sender="test_agent",
        recipient=agent.agent_id,
        content={"security_level": "low"},
        message_type="test"
    )
    
    response = await agent.process_message(message)
    assert response.message_type == "response"
    assert response.content["status"] == "processed"
    
    # Test high security message
    message = AgentMessage(
        sender="test_agent",
        recipient=agent.agent_id,
        content={"security_level": "high"},
        message_type="test"
    )
    
    response = await agent.process_message(message)
    assert response.message_type == "error"
    assert "Insufficient security level" in response.content["error"]
    
    # Update agent security level
    agent.config["has_high_security_access"] = True
    
    # Test high security message again
    response = await agent.process_message(message)
    assert response.message_type == "response"
    assert response.content["status"] == "processed"

@pytest.mark.asyncio
async def test_audit_logging(setup_security_test):
    """Test audit logging functionality."""
    registry, knowledge_graph, factory = await setup_security_test
    
    # Create agent
    agent = await factory.create_agent("security_test")
    
    # Send test messages
    messages = [
        AgentMessage(
            sender="test_agent",
            recipient=agent.agent_id,
            content={"action": "test_action_1"},
            message_type="test"
        ),
        AgentMessage(
            sender="test_agent",
            recipient=agent.agent_id,
            content={"action": "test_action_2"},
            message_type="test"
        )
    ]
    
    for message in messages:
        await agent.process_message(message)
    
    # Verify audit log
    assert len(agent.audit_log) == 2
    assert agent.audit_log[0]["message_type"] == "test"
    assert agent.audit_log[1]["message_type"] == "test"
    assert "test_action_1" in str(agent.audit_log[0]["content"])
    assert "test_action_2" in str(agent.audit_log[1]["content"])
    
    # Verify knowledge graph audit entries
    audit_entries = list(knowledge_graph.triples((None, RDF.type, URIRef("audit:AuditEntry"))))
    assert len(audit_entries) == 2
    
    # Verify audit entry details
    for entry_uri, _, _ in audit_entries:
        timestamp = list(knowledge_graph.triples((entry_uri, URIRef("audit:timestamp"), None)))[0][2]
        action = list(knowledge_graph.triples((entry_uri, URIRef("audit:action"), None)))[0][2]
        assert isinstance(timestamp, Literal)
        assert isinstance(action, Literal)

@pytest.mark.asyncio
async def test_security_metrics(setup_security_test):
    """Test security metrics tracking."""
    registry, knowledge_graph, factory = await setup_security_test
    
    # Create agent
    agent = await factory.create_agent("security_test")
    
    # Send messages with different security levels
    messages = [
        AgentMessage(
            sender="test_agent",
            recipient=agent.agent_id,
            content={"security_level": "low"},
            message_type="test"
        ),
        AgentMessage(
            sender="test_agent",
            recipient=agent.agent_id,
            content={"security_level": "high"},
            message_type="test"
        )
    ]
    
    for message in messages:
        await agent.process_message(message)
    
    # Verify security metrics in knowledge graph
    agent_uri = URIRef(f"agent:{agent.agent_id}")
    security_metrics = list(knowledge_graph.triples((agent_uri, URIRef("agent:hasMetric"), None)))
    assert len(security_metrics) > 0
    
    # Verify specific security metrics
    metrics = await agent.query_knowledge_graph({
        "query": f"""
        SELECT ?metric ?value WHERE {{
            <{agent_uri}> agent:hasMetric ?metric .
            ?metric agent:hasMetricValue ?value .
        }}
        """
    })
    
    assert len(metrics) > 0
    assert any(m["metric"] == "security_violations" for m in metrics)
    assert any(m["metric"] == "security_checks" for m in metrics) 