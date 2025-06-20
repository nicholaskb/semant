import pytest
import pytest_asyncio
from agents.core.research_agent import ResearchAgent
from agents.core.base_agent import AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager
from tests.utils.test_agents import ResearchTestAgent
import time

@pytest_asyncio.fixture
async def research_agent():
    """Create a ResearchAgent instance for testing."""
    agent = ResearchAgent("test_research_agent")
    kg_manager = KnowledgeGraphManager()
    agent.knowledge_graph = kg_manager
    await agent.initialize()
    return agent

@pytest_asyncio.fixture
async def test_research_agent():
    """Create a ResearchTestAgent instance for testing."""
    agent = ResearchTestAgent()
    await agent.initialize()
    return agent

@pytest.mark.asyncio
async def test_initialize(research_agent):
    """Test agent initialization."""
    assert research_agent.agent_id == "test_research_agent"
    assert research_agent.agent_type == "research"
    assert research_agent.reasoner is not None
    assert research_agent.knowledge_graph is not None

@pytest.mark.asyncio
async def test_process_message(research_agent):
    """Test processing a research message."""
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id="test_research_agent",
        content={"topic": "Test research query"},
        timestamp=time.time(),
        message_type="research_request"
    )
    response = await research_agent.process_message(message)
    assert response.sender == "test_research_agent"
    assert response.message_type == "research_response"
    assert "findings" in response.content

@pytest.mark.asyncio
async def test_test_agent_initialization(test_research_agent):
    """Test test agent initialization."""
    assert test_research_agent.agent_id == "test_research_agent"
    assert test_research_agent.agent_type == "research"
    assert test_research_agent.capabilities == ["research", "reasoning"]
    assert test_research_agent.knowledge_graph is not None

@pytest.mark.asyncio
async def test_test_agent_message_history(test_research_agent):
    """Test test agent message history tracking."""
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id="test_research_agent",
        content={"query": "Test research query"},
        timestamp=time.time(),
        message_type="research_request"
    )
    response = await test_research_agent.process_message(message)
    assert len(test_research_agent.get_message_history()) == 1
    assert test_research_agent.get_message_history()[0] == message
    assert response.content["status"] == "research_completed"
    assert response.content["findings"] == "Test findings"

@pytest.mark.asyncio
async def test_test_agent_knowledge_graph(test_research_agent):
    """Test test agent knowledge graph operations."""
    # Test update
    update_data = {
        "subject": "test_subject",
        "predicate": "test_predicate",
        "object": "test_object"
    }
    await test_research_agent.update_knowledge_graph(update_data)
    assert len(test_research_agent.get_knowledge_graph_updates()) == 1
    assert test_research_agent.get_knowledge_graph_updates()[0] == update_data
    
    # Test query
    query = {"sparql": "SELECT ?s ?p ?o WHERE { ?s ?p ?o }"}
    result = await test_research_agent.query_knowledge_graph(query)
    assert len(test_research_agent.get_knowledge_graph_queries()) == 1
    assert test_research_agent.get_knowledge_graph_queries()[0] == query

@pytest.mark.asyncio
async def test_process_message_without_topic(research_agent):
    """Test processing a message without a topic."""
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id="test_research_agent",
        content={},
        timestamp=time.time(),
        message_type="research_request"
    )
    response = await research_agent.process_message(message)
    assert response.content.get("error") == "No research topic provided."

@pytest.mark.asyncio
async def test_process_message_with_topic(research_agent):
    """Test processing a message with a valid topic."""
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id="test_research_agent",
        content={"topic": "test_topic", "depth": 2},
        timestamp=time.time(),
        message_type="research_request"
    )
    response = await research_agent.process_message(message)
    assert "findings" in response.content
    assert response.content.get("status") == "Research investigation completed"

@pytest.mark.asyncio
async def test_query_knowledge_graph_without_topic(research_agent):
    """Test querying the knowledge graph without a topic."""
    result = await research_agent.query_knowledge_graph({})
    assert result.get("error") == "No topic provided for query"

@pytest.mark.asyncio
async def test_query_knowledge_graph_with_topic(research_agent):
    """Test querying the knowledge graph with a valid topic."""
    result = await research_agent.query_knowledge_graph({
        "topic": "test_topic",
        "depth": 2
    })
    assert "related_concepts" in result
    assert "traversal" in result

@pytest.mark.asyncio
async def test_update_knowledge_graph(research_agent):
    """Test updating the knowledge graph with research findings."""
    update_data = {
        "subject": "research:test_topic",
        "predicate": "hasFindings",
        "object": {"test": "findings"}
    }
    await research_agent.update_knowledge_graph(update_data)
    # Verify the triple was added
    for s, p, o in research_agent.knowledge_graph.graph:
        if str(s) == "research:test_topic":
            assert str(p) == "hasFindings"
            break

# New test cases for advanced features

@pytest.mark.asyncio
async def test_confidence_scoring(research_agent):
    """Test confidence scoring in research findings."""
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id="test_research_agent",
        content={
            "topic": "test_topic",
            "depth": 2,
            "require_confidence": True
        },
        timestamp=time.time(),
        message_type="research_request"
    )
    response = await research_agent.process_message(message)
    findings = response.content.get("findings", {})
    assert "confidence_score" in findings
    assert 0 <= findings["confidence_score"] <= 1
    assert "confidence_factors" in findings

@pytest.mark.asyncio
async def test_evidence_tracking(research_agent):
    """Test evidence chain tracking in research findings."""
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id="test_research_agent",
        content={
            "topic": "test_topic",
            "depth": 2,
            "track_evidence": True
        },
        timestamp=time.time(),
        message_type="research_request"
    )
    response = await research_agent.process_message(message)
    findings = response.content.get("findings", {})
    assert "evidence_chain" in findings
    assert isinstance(findings["evidence_chain"], list)
    assert all("source" in evidence for evidence in findings["evidence_chain"])

@pytest.mark.asyncio
async def test_multiple_research_paths(research_agent):
    """Test exploration of multiple research paths."""
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id="test_research_agent",
        content={
            "topic": "test_topic",
            "depth": 2,
            "explore_paths": True
        },
        timestamp=time.time(),
        message_type="research_request"
    )
    response = await research_agent.process_message(message)
    findings = response.content.get("findings", {})
    assert "research_paths" in findings
    assert isinstance(findings["research_paths"], list)
    assert all("path" in path_info for path_info in findings["research_paths"])

@pytest.mark.asyncio
async def test_error_handling(research_agent):
    """Test comprehensive error handling."""
    # Test invalid depth
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id="test_research_agent",
        content={
            "topic": "test_topic",
            "depth": -1
        },
        timestamp=time.time(),
        message_type="research_request"
    )
    response = await research_agent.process_message(message)
    assert "error" in response.content

    # Test invalid topic type
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id="test_research_agent",
        content={
            "topic": 123,  # Invalid type
            "depth": 2
        },
        timestamp=time.time(),
        message_type="research_request"
    )
    response = await research_agent.process_message(message)
    assert "error" in response.content

@pytest.mark.asyncio
async def test_reasoner_integration(research_agent):
    """Test integration with KnowledgeGraphReasoner."""
    # Test reasoner initialization
    assert research_agent.reasoner is not None
    
    # Test reasoner methods
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id="test_research_agent",
        content={
            "topic": "test_topic",
            "depth": 2,
            "use_reasoner": True
        },
        timestamp=time.time(),
        message_type="research_request"
    )
    response = await research_agent.process_message(message)
    findings = response.content.get("findings", {})
    assert "reasoning_steps" in findings
    assert isinstance(findings["reasoning_steps"], dict)
    assert "topic" in findings["reasoning_steps"]
    assert "related_concepts" in findings["reasoning_steps"]
    assert "key_insights" in findings["reasoning_steps"]
    assert "sources" in findings["reasoning_steps"]
    assert "confidence" in findings["reasoning_steps"]

@pytest.mark.asyncio
async def test_research_findings_persistence(research_agent):
    """Test persistence of research findings."""
    # First research request
    message1 = AgentMessage(
        sender_id="test_sender",
        recipient_id="test_research_agent",
        content={
            "topic": "test_topic",
            "depth": 2
        },
        timestamp=time.time(),
        message_type="research_request"
    )
    await research_agent.process_message(message1)
    
    # Query for stored findings
    query_result = await research_agent.query_knowledge_graph({
        "topic": "test_topic",
        "include_findings": True
    })
    assert "stored_findings" in query_result
    assert isinstance(query_result["stored_findings"], list) 