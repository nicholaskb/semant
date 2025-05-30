import pytest
import pytest_asyncio
import asyncio
from agents.domain.corporate_knowledge_agent import CorporateKnowledgeAgent
from agents.core.base_agent import AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager

@pytest_asyncio.fixture
async def knowledge_graph():
    """Fixture for knowledge graph manager."""
    kg = KnowledgeGraphManager()
    kg.initialize_namespaces()
    return kg

@pytest_asyncio.fixture
async def corporate_agent(knowledge_graph):
    """Fixture for corporate knowledge agent."""
    agent = CorporateKnowledgeAgent()
    agent.knowledge_graph = knowledge_graph
    await agent.initialize()
    return agent

@pytest.mark.asyncio
async def test_agent_initialization(corporate_agent):
    """Test that the agent initializes correctly."""
    assert corporate_agent.agent_id == "corporate_knowledge_agent"
    assert corporate_agent.agent_type == "corporate_knowledge"
    assert corporate_agent.document_store == {}
    assert corporate_agent.knowledge_graph is not None

@pytest.mark.asyncio
async def test_document_ingest(corporate_agent):
    """Test document ingestion functionality."""
    # Create test document
    test_doc = {
        'title': 'Test Document',
        'content': 'This is a test document.',
        'timestamp': '2024-03-14T12:00:00Z',
        'source': 'test',
        'relationships': [
            {'predicate': 'relates_to', 'object': 'test_topic'}
        ]
    }
    
    # Create message
    message = AgentMessage(
        sender='test_sender',
        recipient=corporate_agent.agent_id,
        content=test_doc,
        timestamp=1234567890.0,
        message_type='document_ingest'
    )
    
    # Process message
    response = await corporate_agent.process_message(message)
    
    # Verify response
    assert response.message_type == 'document_ingest_response'
    assert response.content['status'] == 'success'
    assert 'doc_id' in response.content
    
    # Verify document was stored
    doc_id = response.content['doc_id']
    assert doc_id in corporate_agent.document_store
    assert corporate_agent.document_store[doc_id]['title'] == test_doc['title']

@pytest.mark.asyncio
async def test_knowledge_query(corporate_agent):
    """Test knowledge query functionality."""
    # First ingest a document
    test_doc = {
        'title': 'Test Document',
        'content': 'This is a test document.',
        'timestamp': '2024-03-14T12:00:00Z',
        'source': 'test'
    }
    
    ingest_message = AgentMessage(
        sender='test_sender',
        recipient=corporate_agent.agent_id,
        content=test_doc,
        timestamp=1234567890.0,
        message_type='document_ingest'
    )
    
    await corporate_agent.process_message(ingest_message)
    
    # Create query message
    query = {
        'type': 'document_search',
        'criteria': {'title': 'Test Document'}
    }
    
    query_message = AgentMessage(
        sender='test_sender',
        recipient=corporate_agent.agent_id,
        content=query,
        timestamp=1234567890.0,
        message_type='knowledge_query'
    )
    
    # Process query
    response = await corporate_agent.process_message(query_message)
    
    # Verify response
    assert response.message_type == 'knowledge_query_response'
    assert response.content['status'] == 'success'
    assert 'results' in response.content

@pytest.mark.asyncio
async def test_document_update(corporate_agent):
    """Test document update functionality."""
    # First ingest a document
    test_doc = {
        'title': 'Test Document',
        'content': 'This is a test document.',
        'timestamp': '2024-03-14T12:00:00Z',
        'source': 'test'
    }
    
    ingest_message = AgentMessage(
        sender='test_sender',
        recipient=corporate_agent.agent_id,
        content=test_doc,
        timestamp=1234567890.0,
        message_type='document_ingest'
    )
    
    response = await corporate_agent.process_message(ingest_message)
    doc_id = response.content['doc_id']
    
    # Create update message
    update_data = {
        'doc_id': doc_id,
        'changes': {
            'title': 'Updated Test Document',
            'content': 'This is an updated test document.',
            'timestamp': '2024-03-14T13:00:00Z',
            'source': 'test-updated'
        }
    }
    
    update_message = AgentMessage(
        sender='test_sender',
        recipient=corporate_agent.agent_id,
        content=update_data,
        timestamp=1234567890.0,
        message_type='document_update'
    )
    
    # Process update
    response = await corporate_agent.process_message(update_message)
    
    # Verify response
    assert response.message_type == 'document_update_response'
    assert response.content['status'] == 'success'
    
    # Verify document was updated
    assert corporate_agent.document_store[doc_id]['title'] == 'Updated Test Document'
    assert corporate_agent.document_store[doc_id]['content'] == 'This is an updated test document.'
    assert corporate_agent.document_store[doc_id]['timestamp'] == '2024-03-14T13:00:00Z'
    assert corporate_agent.document_store[doc_id]['source'] == 'test-updated'

@pytest.mark.asyncio
async def test_unknown_message_type(corporate_agent):
    """Test handling of unknown message types."""
    message = AgentMessage(
        sender='test_sender',
        recipient=corporate_agent.agent_id,
        content={},
        timestamp=1234567890.0,
        message_type='unknown_type'
    )
    
    response = await corporate_agent.process_message(message)
    
    assert response.message_type == 'error_response'
    assert response.content['status'] == 'error'
    assert 'message' in response.content 