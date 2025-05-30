import pytest
import asyncio
from datetime import datetime
from rdflib.namespace import RDF, RDFS
from rdflib import URIRef
from demo_agents import (
    EngagementManagerAgent,
    StrategyLeadAgent,
    ImplementationLeadAgent,
    ValueRealizationLeadAgent,
    AgentMessage,
    KnowledgeGraph,
    CONSULTING
)

@pytest.fixture
async def setup_agents():
    """Setup all agents for testing."""
    engagement_manager = EngagementManagerAgent()
    strategy_lead = StrategyLeadAgent()
    implementation_lead = ImplementationLeadAgent()
    value_realization_lead = ValueRealizationLeadAgent()
    
    await engagement_manager.initialize()
    await strategy_lead.initialize()
    await implementation_lead.initialize()
    await value_realization_lead.initialize()
    
    return {
        'engagement_manager': engagement_manager,
        'strategy_lead': strategy_lead,
        'implementation_lead': implementation_lead,
        'value_realization_lead': value_realization_lead
    }

@pytest.mark.asyncio
async def test_engagement_initialization(setup_agents):
    """Test engagement initialization and knowledge graph updates."""
    agents = await setup_agents
    engagement_manager = agents['engagement_manager']
    
    # Create test engagement
    engagement_message = AgentMessage(
        sender="test_client",
        recipient="engagement_manager",
        content={
            'client': 'Test Healthcare Provider',
            'scope': 'Test AI Transformation',
            'budget': '$10M',
            'timeline': '12 months'
        },
        timestamp=datetime.now().timestamp(),
        message_type="engagement_request"
    )
    
    # Process engagement
    response = await engagement_manager.process_message(engagement_message)
    
    # Verify response
    assert response.content['status'] == 'engagement_started'
    assert 'engagement_id' in response.content
    
    # Verify knowledge graph
    graph_data = await engagement_manager.query_knowledge_graph({})
    engagement_id = response.content['engagement_id']
    
    assert f"engagement:{engagement_id}" in graph_data
    assert any("Test Healthcare Provider" in str(v) for v in graph_data[f"engagement:{engagement_id}"].values())
    assert any("Test AI Transformation" in str(v) for v in graph_data[f"engagement:{engagement_id}"].values())

@pytest.mark.asyncio
async def test_strategy_development(setup_agents):
    """Test strategy development and knowledge capture."""
    agents = await setup_agents
    strategy_lead = agents['strategy_lead']
    
    # Create test strategy request
    strategy_message = AgentMessage(
        sender="engagement_manager",
        recipient="strategy_lead",
        content={
            'engagement_id': 'test_engagement_1',
            'client': 'Test Client',
            'scope': 'Digital Transformation'
        },
        timestamp=datetime.now().timestamp(),
        message_type="strategy_request"
    )
    
    # Process strategy request
    response = await strategy_lead.process_message(strategy_message)
    
    # Verify response
    assert response.content['status'] == 'strategy_developed'
    assert 'strategy' in response.content
    
    # Verify strategy content
    strategy = response.content['strategy']
    assert 'vision' in strategy
    assert 'key_pillars' in strategy
    assert 'implementation_approach' in strategy
    
    # Verify knowledge graph
    graph_data = await strategy_lead.query_knowledge_graph({})
    assert f"strategy:test_engagement_1" in graph_data

@pytest.mark.asyncio
async def test_implementation_planning(setup_agents):
    """Test implementation planning and knowledge capture."""
    agents = await setup_agents
    implementation_lead = agents['implementation_lead']
    
    # Create test implementation request
    implementation_message = AgentMessage(
        sender="strategy_lead",
        recipient="implementation_lead",
        content={
            'engagement_id': 'test_engagement_1',
            'strategy': {
                'vision': 'Test Vision',
                'key_pillars': ['Pillar 1', 'Pillar 2'],
                'implementation_approach': 'Phased'
            }
        },
        timestamp=datetime.now().timestamp(),
        message_type="implementation_request"
    )
    
    # Process implementation request
    response = await implementation_lead.process_message(implementation_message)
    
    # Verify response
    assert response.content['status'] == 'implementation_planned'
    assert 'implementation' in response.content
    
    # Verify implementation content
    implementation = response.content['implementation']
    assert 'phases' in implementation
    assert 'resource_requirements' in implementation
    
    # Verify knowledge graph
    graph_data = await implementation_lead.query_knowledge_graph({})
    assert f"implementation:test_engagement_1" in graph_data

@pytest.mark.asyncio
async def test_value_framework_development(setup_agents):
    """Test value framework development and knowledge capture."""
    agents = await setup_agents
    value_lead = agents['value_realization_lead']
    
    # Create test value request
    value_message = AgentMessage(
        sender="implementation_lead",
        recipient="value_realization_lead",
        content={
            'engagement_id': 'test_engagement_1',
            'implementation': {
                'phases': [
                    {'name': 'Phase 1', 'duration': '3 months'},
                    {'name': 'Phase 2', 'duration': '6 months'}
                ],
                'resource_requirements': {'team_size': 10}
            }
        },
        timestamp=datetime.now().timestamp(),
        message_type="value_request"
    )
    
    # Process value request
    response = await value_lead.process_message(value_message)
    
    # Verify response
    assert response.content['status'] == 'value_framework_developed'
    assert 'framework' in response.content
    
    # Verify framework content
    framework = response.content['framework']
    assert 'key_metrics' in framework
    assert 'value_tracking_process' in framework
    
    # Verify knowledge graph
    graph_data = await value_lead.query_knowledge_graph({})
    assert f"value:test_engagement_1" in graph_data

@pytest.mark.asyncio
async def test_end_to_end_engagement(setup_agents):
    """Test complete engagement flow from initialization to value framework."""
    agents = await setup_agents
    engagement_manager = agents['engagement_manager']
    strategy_lead = agents['strategy_lead']
    implementation_lead = agents['implementation_lead']
    value_lead = agents['value_realization_lead']
    
    # 1. Initialize engagement
    engagement_message = AgentMessage(
        sender="test_client",
        recipient="engagement_manager",
        content={
            'client': 'End-to-End Test Client',
            'scope': 'Comprehensive Digital Transformation',
            'budget': '$20M',
            'timeline': '24 months'
        },
        timestamp=datetime.now().timestamp(),
        message_type="engagement_request"
    )
    
    engagement_response = await engagement_manager.process_message(engagement_message)
    engagement_id = engagement_response.content['engagement_id']
    
    # 2. Develop strategy
    strategy_message = AgentMessage(
        sender="engagement_manager",
        recipient="strategy_lead",
        content={
            'engagement_id': engagement_id,
            'client': 'End-to-End Test Client',
            'scope': 'Comprehensive Digital Transformation'
        },
        timestamp=datetime.now().timestamp(),
        message_type="strategy_request"
    )
    
    strategy_response = await strategy_lead.process_message(strategy_message)
    
    # 3. Plan implementation
    implementation_message = AgentMessage(
        sender="strategy_lead",
        recipient="implementation_lead",
        content={
            'engagement_id': engagement_id,
            'strategy': strategy_response.content['strategy']
        },
        timestamp=datetime.now().timestamp(),
        message_type="implementation_request"
    )
    
    implementation_response = await implementation_lead.process_message(implementation_message)
    
    # 4. Develop value framework
    value_message = AgentMessage(
        sender="implementation_lead",
        recipient="value_realization_lead",
        content={
            'engagement_id': engagement_id,
            'implementation': implementation_response.content['implementation']
        },
        timestamp=datetime.now().timestamp(),
        message_type="value_request"
    )
    
    value_response = await value_lead.process_message(value_message)
    
    # Verify complete flow
    assert engagement_response.content['status'] == 'engagement_started'
    assert strategy_response.content['status'] == 'strategy_developed'
    assert implementation_response.content['status'] == 'implementation_planned'
    assert value_response.content['status'] == 'value_framework_developed'
    
    # Verify knowledge graph consistency
    engagement_graph = await engagement_manager.query_knowledge_graph({})
    strategy_graph = await strategy_lead.query_knowledge_graph({})
    implementation_graph = await implementation_lead.query_knowledge_graph({})
    value_graph = await value_lead.query_knowledge_graph({})
    
    assert f"engagement:{engagement_id}" in engagement_graph
    assert f"strategy:{engagement_id}" in strategy_graph
    assert f"implementation:{engagement_id}" in implementation_graph
    assert f"value:{engagement_id}" in value_graph

@pytest.mark.asyncio
async def test_knowledge_graph_consistency(setup_agents):
    """Test knowledge graph consistency across agents."""
    agents = await setup_agents
    engagement_manager = agents['engagement_manager']
    
    # Create test engagement
    engagement_message = AgentMessage(
        sender="test_client",
        recipient="engagement_manager",
        content={
            'client': 'Knowledge Graph Test Client',
            'scope': 'Knowledge Graph Test',
            'budget': '$5M',
            'timeline': '6 months'
        },
        timestamp=datetime.now().timestamp(),
        message_type="engagement_request"
    )
    
    # Process engagement
    response = await engagement_manager.process_message(engagement_message)
    engagement_id = response.content['engagement_id']
    
    # Verify knowledge graph structure
    graph_data = await engagement_manager.query_knowledge_graph({})
    
    # Check engagement node
    assert f"engagement:{engagement_id}" in graph_data
    engagement_node = graph_data[f"engagement:{engagement_id}"]
    
    # Verify required properties
    required_properties = [
        str(RDF.type),
        str(CONSULTING.hasClient),
        str(CONSULTING.hasScope),
        str(CONSULTING.hasBudget),
        str(CONSULTING.hasTimeline)
    ]
    
    for prop in required_properties:
        assert any(prop in str(p) for p in engagement_node.keys())
    
    # Verify property values
    assert any("Knowledge Graph Test Client" in str(v) for v in engagement_node.values())
    assert any("Knowledge Graph Test" in str(v) for v in engagement_node.values())
    assert any("$5M" in str(v) for v in engagement_node.values())
    assert any("6 months" in str(v) for v in engagement_node.values())

@pytest.mark.asyncio
async def test_agent_diary_functionality(setup_agents):
    """Test that each consulting agent can write to and read from their diary after a move event."""
    agents = await setup_agents
    move_event = {
        'event': 'move',
        'reason': 'Agent assigned to new engagement',
        'location': 'Client Site A'
    }
    for agent_name, agent in agents.items():
        # Simulate a move event
        agent.write_diary(f"Moved: {move_event['reason']}", details=move_event)
        diary_entries = agent.read_diary()
        assert len(diary_entries) > 0
        last_entry = diary_entries[-1]
        assert "Moved" in last_entry["message"]
        assert last_entry["details"] == move_event 

@pytest.mark.asyncio
async def test_agent_diary_in_knowledge_graph(setup_agents):
    """Test that each consulting agent's diary entries are present in the knowledge graph after writing."""
    agents = await setup_agents
    for agent_name, agent in agents.items():
        agent.write_diary("Moved to new client site", details={"event": "move", "location": "HQ"})
        # Query the knowledge graph for diary entries
        g = agent.knowledge_graph.graph
        agent_uri = f"agent:{agent.agent_id}"
        found = False
        for s, p, o in g.triples((URIRef(agent_uri), None, None)):
            if str(p).endswith("hasDiaryEntry"):
                # Check that the diary node has expected properties
                diary_bnode = o
                has_message = False
                has_timestamp = False
                for _, dp, dv in g.triples((diary_bnode, None, None)):
                    if str(dp).endswith("message") and "Moved to new client site" in str(dv):
                        has_message = True
                    if str(dp).endswith("timestamp"):
                        has_timestamp = True
                if has_message and has_timestamp:
                    found = True
        assert found, f"Diary entry not found in knowledge graph for {agent_name}" 