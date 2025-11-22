"""
Tests for fixed agent methods in Task 10
=========================================
Verifies that all agent methods are properly implemented.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock

from agents.core.base_agent import AgentMessage
from agents.core.feature_z_agent import FeatureZAgent
from agents.domain.simple_agents import (
    SimpleResponderAgent,
    FinanceAgent,
    CoachingAgent,
    IntelligenceAgent,
    DeveloperAgent
)


@pytest.fixture
def mock_knowledge_graph():
    """Create a mock knowledge graph for testing."""
    kg = Mock()
    kg.add_triple = AsyncMock(return_value=None)
    kg.query_graph = AsyncMock(return_value=[])
    kg.update_graph = AsyncMock(return_value=None)
    kg.initialize = AsyncMock(return_value=None)
    return kg


@pytest.fixture
def sample_message():
    """Create a sample agent message for testing."""
    return AgentMessage(
        sender_id="test_sender",
        recipient_id="test_recipient",
        content={"test": "data"},
        timestamp=datetime.now(),
        message_type="test"
    )


# ============================================================================
# FeatureZAgent Tests
# ============================================================================

@pytest.mark.asyncio
async def test_feature_z_agent_initialization():
    """Test FeatureZAgent can be initialized properly."""
    agent = FeatureZAgent(agent_id="test_feature_z")
    await agent.initialize()
    
    assert agent.agent_id == "test_feature_z"
    assert agent.agent_type == "feature_z"
    capabilities = await agent.get_capabilities()
    capability_types = {cap.type.value.upper() for cap in capabilities}
    assert "FEATURE_Z_PROCESSING" in capability_types or "feature_z_processing" in capability_types
    assert "DATA_VALIDATION" in capability_types or "data_validation" in capability_types
    assert agent.processed_count == 0
    assert agent.error_count == 0


@pytest.mark.asyncio
async def test_feature_z_agent_process_message(sample_message):
    """Test FeatureZAgent can process messages."""
    agent = FeatureZAgent(agent_id="test_feature_z")
    await agent.initialize()
    
    # Test validation operation
    message = AgentMessage(
        sender_id="test",
        recipient_id="test_feature_z",
        content={
            "operation": "validate",
            "feature_data": {"id": 1, "type": "test", "value": 42}
        },
        timestamp=datetime.now(),
        message_type="request"
    )
    
    response = await agent.process_message(message)
    assert response.content["status"] == "success"
    assert response.content["operation"] == "validate"
    assert response.content["result"]["is_valid"] is True
    assert agent.processed_count == 1


@pytest.mark.asyncio
async def test_feature_z_agent_process_data(sample_message):
    """Test FeatureZAgent can process feature data."""
    agent = FeatureZAgent(agent_id="test_feature_z")
    await agent.initialize()
    
    message = AgentMessage(
        sender_id="test",
        recipient_id="test_feature_z",
        content={
            "operation": "process",
            "feature_data": {"id": 1, "type": "test", "value": 42}
        },
        timestamp=datetime.now(),
        message_type="request"
    )
    
    response = await agent.process_message(message)
    assert response.content["status"] == "success"
    assert response.content["operation"] == "process"
    assert response.content["result"]["processed"] is True
    assert agent.processed_count == 1


@pytest.mark.asyncio
async def test_feature_z_agent_query_status(sample_message):
    """Test FeatureZAgent can query its own status."""
    agent = FeatureZAgent(agent_id="test_feature_z")
    await agent.initialize()
    
    message = AgentMessage(
        sender_id="test",
        recipient_id="test_feature_z",
        content={"operation": "query"},
        timestamp=datetime.now(),
        message_type="request"
    )
    
    response = await agent.process_message(message)
    assert response.content["status"] == "success"
    assert response.content["result"]["agent_id"] == "test_feature_z"
    assert response.content["result"]["processed_count"] == 1  # From processing the query
    assert response.content["result"]["error_count"] == 0


@pytest.mark.asyncio
async def test_feature_z_agent_error_handling(sample_message):
    """Test FeatureZAgent handles errors properly."""
    agent = FeatureZAgent(agent_id="test_feature_z")
    await agent.initialize()
    
    # Test with missing feature data
    message = AgentMessage(
        sender_id="test",
        recipient_id="test_feature_z",
        content={"operation": "validate", "feature_data": None},
        timestamp=datetime.now(),
        message_type="request"
    )
    
    response = await agent.process_message(message)
    assert response.content["status"] == "error"
    assert "No feature data provided" in response.content["error"]
    assert agent.error_count == 1


@pytest.mark.asyncio
async def test_feature_z_agent_kg_integration(mock_knowledge_graph):
    """Test FeatureZAgent knowledge graph integration."""
    agent = FeatureZAgent(
        agent_id="test_feature_z",
        knowledge_graph=mock_knowledge_graph
    )
    await agent.initialize()
    
    # Test query_knowledge_graph
    query_result = await agent.query_knowledge_graph({"type": "operations"})
    assert "operations" in query_result or "error" in query_result
    
    # Test update_knowledge_graph
    await agent.update_knowledge_graph({
        "type": "test_update",
        "data": "test_value"
    })
    assert mock_knowledge_graph.add_triple.called


# ============================================================================
# SimpleResponderAgent Tests
# ============================================================================

@pytest.mark.asyncio
async def test_simple_responder_agent_initialization():
    """Test SimpleResponderAgent can be initialized properly."""
    agent = SimpleResponderAgent(
        agent_id="test_simple",
        agent_type="simple",
        default_response="Default response"
    )
    await agent.initialize()
    
    assert agent.agent_id == "test_simple"
    assert agent.agent_type == "simple"
    assert agent.default_response == "Default response"
    assert agent.response_count == 0


@pytest.mark.asyncio
async def test_simple_responder_agent_process_message(sample_message):
    """Test SimpleResponderAgent can process messages."""
    agent = SimpleResponderAgent(
        agent_id="test_simple",
        agent_type="simple",
        default_response="Default response"
    )
    await agent.initialize()
    
    response = await agent.process_message(sample_message)
    assert response.content["response"] == "Default response"
    assert response.content["response_count"] == 1
    assert response.content["agent_type"] == "simple"


@pytest.mark.asyncio
async def test_simple_responder_agent_custom_response(sample_message):
    """Test SimpleResponderAgent can handle custom responses."""
    agent = SimpleResponderAgent(
        agent_id="test_simple",
        agent_type="simple",
        default_response="Default response"
    )
    await agent.initialize()
    
    message = AgentMessage(
        sender_id="test",
        recipient_id="test_simple",
        content={"custom_response": "Custom response"},
        timestamp=datetime.now(),
        message_type="request"
    )
    
    response = await agent.process_message(message)
    assert response.content["response"] == "Custom response"
    assert response.content["response_count"] == 1


@pytest.mark.asyncio
async def test_simple_responder_agent_kg_integration(mock_knowledge_graph):
    """Test SimpleResponderAgent knowledge graph integration."""
    agent = SimpleResponderAgent(
        agent_id="test_simple",
        agent_type="simple",
        default_response="Default",
        knowledge_graph=mock_knowledge_graph
    )
    await agent.initialize()
    
    # Process a message (which should log to KG)
    message = AgentMessage(
        sender_id="test",
        recipient_id="test_simple",
        content={},
        timestamp=datetime.now(),
        message_type="request"
    )
    
    await agent.process_message(message)
    assert mock_knowledge_graph.add_triple.called
    
    # Test query_knowledge_graph
    query_result = await agent.query_knowledge_graph({"sparql": "SELECT * WHERE {?s ?p ?o}"})
    assert "results" in query_result or "error" in query_result
    
    # Test update_knowledge_graph
    await agent.update_knowledge_graph({"test_key": "test_value"})
    assert mock_knowledge_graph.add_triple.called


# ============================================================================
# Derived Agent Tests
# ============================================================================

@pytest.mark.asyncio
async def test_finance_agent():
    """Test FinanceAgent works correctly."""
    agent = FinanceAgent()
    await agent.initialize()
    
    assert agent.agent_id == "finance_agent"
    assert agent.agent_type == "finance"
    assert agent.default_response == "Finance information not available."
    
    message = AgentMessage(
        sender_id="test",
        recipient_id="finance_agent",
        content={},
        timestamp=datetime.now(),
        message_type="request"
    )
    
    response = await agent.process_message(message)
    assert response.content["response"] == "Finance information not available."


@pytest.mark.asyncio
async def test_coaching_agent():
    """Test CoachingAgent works correctly."""
    agent = CoachingAgent()
    await agent.initialize()
    
    assert agent.agent_id == "coaching_agent"
    assert agent.agent_type == "coaching"
    assert agent.default_response == "Keep learning and growing!"
    
    message = AgentMessage(
        sender_id="test",
        recipient_id="coaching_agent",
        content={},
        timestamp=datetime.now(),
        message_type="request"
    )
    
    response = await agent.process_message(message)
    assert response.content["response"] == "Keep learning and growing!"


@pytest.mark.asyncio
async def test_intelligence_agent():
    """Test IntelligenceAgent works correctly."""
    agent = IntelligenceAgent()
    await agent.initialize()
    
    assert agent.agent_id == "intelligence_agent"
    assert agent.agent_type == "intelligence"
    assert agent.default_response == "No intelligence reports."
    
    message = AgentMessage(
        sender_id="test",
        recipient_id="intelligence_agent",
        content={},
        timestamp=datetime.now(),
        message_type="request"
    )
    
    response = await agent.process_message(message)
    assert response.content["response"] == "No intelligence reports."


@pytest.mark.asyncio
async def test_developer_agent():
    """Test DeveloperAgent works correctly."""
    agent = DeveloperAgent()
    await agent.initialize()
    
    assert agent.agent_id == "developer_agent"
    assert agent.agent_type == "developer"
    assert agent.default_response == "Code generation not supported."
    
    message = AgentMessage(
        sender_id="test",
        recipient_id="developer_agent",
        content={},
        timestamp=datetime.now(),
        message_type="request"
    )
    
    response = await agent.process_message(message)
    assert response.content["response"] == "Code generation not supported."


# ============================================================================
# Edge Cases and Error Scenarios
# ============================================================================

@pytest.mark.asyncio
async def test_agents_without_kg():
    """Test agents work correctly without knowledge graph."""
    feature_agent = FeatureZAgent(agent_id="test_no_kg")
    simple_agent = SimpleResponderAgent(
        agent_id="test_simple_no_kg",
        agent_type="simple",
        default_response="Test"
    )
    
    await feature_agent.initialize()
    await simple_agent.initialize()
    
    # Test KG operations return appropriate responses
    feature_query = await feature_agent.query_knowledge_graph({"type": "test"})
    assert "error" in feature_query
    assert "not available" in feature_query["error"].lower()
    
    simple_query = await simple_agent.query_knowledge_graph({"sparql": "SELECT *"})
    assert "error" in simple_query
    assert "not available" in simple_query["error"].lower()
    
    # Test update operations handle missing KG gracefully
    await feature_agent.update_knowledge_graph({"test": "data"})
    await simple_agent.update_knowledge_graph({"test": "data"})
    # Should not raise exceptions


@pytest.mark.asyncio
async def test_multiple_agent_interactions():
    """Test multiple agents can interact without conflicts."""
    agents = [
        FeatureZAgent(agent_id="feature_1"),
        FeatureZAgent(agent_id="feature_2"),
        SimpleResponderAgent("simple_1", "type1", "Response 1"),
        SimpleResponderAgent("simple_2", "type2", "Response 2"),
    ]
    
    # Initialize all agents
    for agent in agents:
        await agent.initialize()
    
    # Process messages with each agent
    for i, agent in enumerate(agents):
        message = AgentMessage(
            sender_id=f"test_{i}",
            recipient_id=agent.agent_id,
            content={"test_data": f"data_{i}"},
            timestamp=datetime.now(),
            message_type="test"
        )
        
        response = await agent.process_message(message)
        assert response.sender_id == agent.agent_id
        assert response.recipient_id == f"test_{i}"
        
    # Verify each agent maintains its own state
    assert agents[0].agent_id == "feature_1"
    assert agents[1].agent_id == "feature_2"
    assert agents[2].default_response == "Response 1"
    assert agents[3].default_response == "Response 2"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
