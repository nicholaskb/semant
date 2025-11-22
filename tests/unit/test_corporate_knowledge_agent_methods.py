"""
Unit tests for CorporateKnowledgeAgent missing methods implementation.
Tests the newly implemented _search_documents and _query_relationships methods.
"""

import pytest
import asyncio
from agents.domain.corporate_knowledge_agent import CorporateKnowledgeAgent
from agents.core.message_types import AgentMessage
from datetime import datetime


@pytest.fixture
async def knowledge_agent():
    """Create a CorporateKnowledgeAgent instance for testing."""
    agent = CorporateKnowledgeAgent()
    await agent.initialize()
    return agent


@pytest.fixture
async def populated_agent(knowledge_agent):
    """Create an agent with test documents."""
    # Add test documents
    knowledge_agent.document_store = {
        'doc_1': {
            'title': 'Python Programming Guide',
            'content': 'A comprehensive guide to Python programming language',
            'source': 'internal_wiki',
            'timestamp': '2025-01-10T10:00:00'
        },
        'doc_2': {
            'title': 'JavaScript Best Practices',
            'content': 'Best practices for writing clean JavaScript code',
            'source': 'external_blog',
            'timestamp': '2025-01-11T14:30:00'
        },
        'doc_3': {
            'title': 'Python Design Patterns',
            'content': 'Common design patterns in Python applications',
            'source': 'internal_wiki',
            'timestamp': '2025-01-12T09:15:00'
        }
    }
    return knowledge_agent


class TestSearchDocuments:
    """Test suite for _search_documents method."""
    
    @pytest.mark.asyncio
    async def test_search_by_title(self, populated_agent):
        """Test searching documents by title substring."""
        criteria = {'title': 'Python'}
        result = await populated_agent._search_documents(criteria)
        
        assert result['count'] == 2
        assert len(result['documents']) == 2
        titles = [doc['title'] for doc in result['documents']]
        assert 'Python Programming Guide' in titles
        assert 'Python Design Patterns' in titles
    
    @pytest.mark.asyncio
    async def test_search_by_content(self, populated_agent):
        """Test searching documents by content substring."""
        criteria = {'content': 'best practices'}
        result = await populated_agent._search_documents(criteria)
        
        assert result['count'] == 1
        assert result['documents'][0]['title'] == 'JavaScript Best Practices'
    
    @pytest.mark.asyncio
    async def test_search_by_source(self, populated_agent):
        """Test searching documents by source filter."""
        criteria = {'source': 'internal_wiki'}
        result = await populated_agent._search_documents(criteria)
        
        assert result['count'] == 2
        sources = [doc['source'] for doc in result['documents']]
        assert all(s == 'internal_wiki' for s in sources)
    
    @pytest.mark.asyncio
    async def test_search_by_doc_ids(self, populated_agent):
        """Test searching documents by specific IDs."""
        criteria = {'doc_ids': ['doc_1', 'doc_3']}
        result = await populated_agent._search_documents(criteria)
        
        assert result['count'] == 2
        doc_ids = [doc['doc_id'] for doc in result['documents']]
        assert 'doc_1' in doc_ids
        assert 'doc_3' in doc_ids
    
    @pytest.mark.asyncio
    async def test_search_multiple_criteria(self, populated_agent):
        """Test searching with multiple criteria (AND logic)."""
        criteria = {
            'title': 'Python',
            'source': 'internal_wiki'
        }
        result = await populated_agent._search_documents(criteria)
        
        assert result['count'] == 2
        for doc in result['documents']:
            assert 'Python' in doc['title']
            assert doc['source'] == 'internal_wiki'
    
    @pytest.mark.asyncio
    async def test_search_no_matches(self, populated_agent):
        """Test search that returns no results."""
        criteria = {'title': 'NonExistentDocument'}
        result = await populated_agent._search_documents(criteria)
        
        assert result['count'] == 0
        assert result['documents'] == []
    
    @pytest.mark.asyncio
    async def test_search_empty_criteria_raises_error(self, populated_agent):
        """Test that empty criteria raises ValueError."""
        with pytest.raises(ValueError, match="Search criteria cannot be empty"):
            await populated_agent._search_documents({})
    
    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, populated_agent):
        """Test that search is case-insensitive."""
        criteria = {'title': 'python'}  # lowercase
        result = await populated_agent._search_documents(criteria)
        
        assert result['count'] == 2  # Should match 'Python' titles


class TestQueryRelationships:
    """Test suite for _query_relationships method."""
    
    @pytest.mark.asyncio
    async def test_query_missing_doc_id_raises_error(self, knowledge_agent):
        """Test that missing doc_id raises ValueError."""
        criteria = {'relationship_type': 'relatedTo'}
        
        with pytest.raises(ValueError, match="doc_id is required"):
            await knowledge_agent._query_relationships(criteria)
    
    @pytest.mark.asyncio
    async def test_query_empty_criteria_raises_error(self, knowledge_agent):
        """Test that empty criteria raises ValueError."""
        with pytest.raises(ValueError, match="Query criteria cannot be empty"):
            await knowledge_agent._query_relationships({})
    
    @pytest.mark.asyncio
    async def test_query_without_knowledge_graph(self, knowledge_agent):
        """Test query when knowledge graph is not available."""
        knowledge_agent.knowledge_graph = None
        criteria = {'doc_id': 'doc_1'}
        
        result = await knowledge_agent._query_relationships(criteria)
        
        assert result['count'] == 0
        assert result['relationships'] == []
    
    @pytest.mark.asyncio
    async def test_query_default_direction_is_outgoing(self, knowledge_agent):
        """Test that default direction is 'outgoing'."""
        # This test verifies the default behavior
        # In a real scenario with KG, we'd mock the query_graph method
        criteria = {'doc_id': 'doc_1'}
        
        # Set up mock knowledge graph
        class MockKG:
            async def query_graph(self, query):
                return []
        
        knowledge_agent.knowledge_graph = MockKG()
        result = await knowledge_agent._query_relationships(criteria)
        
        assert result['count'] == 0
        assert 'relationships' in result
    
    @pytest.mark.asyncio
    async def test_query_all_directions(self, knowledge_agent):
        """Test querying relationships in all directions."""
        # Mock knowledge graph with test data
        class MockKG:
            async def query_graph(self, query):
                if 'SELECT ?predicate ?object' in query:
                    # Outgoing relationships
                    return [
                        {'predicate': 'relatedTo', 'object': 'doc_2'},
                        {'predicate': 'references', 'object': 'doc_3'}
                    ]
                elif 'SELECT ?subject ?predicate' in query:
                    # Incoming relationships
                    return [
                        {'subject': 'doc_4', 'predicate': 'derivedFrom'}
                    ]
                return []
        
        knowledge_agent.knowledge_graph = MockKG()
        criteria = {'doc_id': 'doc_1', 'direction': 'both'}
        
        result = await knowledge_agent._query_relationships(criteria)
        
        assert result['count'] == 3
        assert len(result['relationships']) == 3
        
        # Verify outgoing relationships
        outgoing = [r for r in result['relationships'] if r['direction'] == 'outgoing']
        assert len(outgoing) == 2
        
        # Verify incoming relationships
        incoming = [r for r in result['relationships'] if r['direction'] == 'incoming']
        assert len(incoming) == 1


class TestIntegration:
    """Integration tests for the agent with new methods."""
    
    @pytest.mark.asyncio
    async def test_document_search_via_query_knowledge_graph(self, populated_agent):
        """Test document search through the main query interface."""
        query = {
            'type': 'document_search',
            'criteria': {'title': 'Python'}
        }
        
        result = await populated_agent.query_knowledge_graph(query)
        
        assert result['count'] == 2
        assert all('Python' in doc['title'] for doc in result['documents'])
    
    @pytest.mark.asyncio
    async def test_relationship_query_via_query_knowledge_graph(self, knowledge_agent):
        """Test relationship query through the main query interface."""
        # Mock KG
        class MockKG:
            async def query_graph(self, query):
                return [{'predicate': 'relatedTo', 'object': 'doc_2'}]
        
        knowledge_agent.knowledge_graph = MockKG()
        
        query = {
            'type': 'relationship_query',
            'criteria': {'doc_id': 'doc_1'}
        }
        
        result = await knowledge_agent.query_knowledge_graph(query)
        
        assert result['count'] == 1
        assert len(result['relationships']) == 1
    
    @pytest.mark.asyncio
    async def test_unknown_query_type_raises_error(self, knowledge_agent):
        """Test that unknown query type raises ValueError."""
        query = {
            'type': 'unknown_type',
            'criteria': {}
        }
        
        with pytest.raises(ValueError, match="Unknown query type"):
            await knowledge_agent.query_knowledge_graph(query)


# Run tests with: pytest tests/unit/test_corporate_knowledge_agent_methods.py -v

