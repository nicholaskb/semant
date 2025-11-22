import pytest
import pytest_asyncio
from kg.models.remote_graph_manager import RemoteKnowledgeGraphManager
from unittest.mock import AsyncMock, patch

@pytest_asyncio.fixture
async def remote_graph_manager():
    """Create a fresh remote graph manager instance for testing."""
    return RemoteKnowledgeGraphManager("http://example.org/sparql")

@pytest.mark.asyncio
async def test_query_graph():
    with patch.object(RemoteKnowledgeGraphManager, 'query_graph', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = [{'s': 'subject', 'p': 'predicate', 'o': 'object'}]
        remote_manager = RemoteKnowledgeGraphManager(query_endpoint="http://example.org/sparql")
        results = await remote_manager.query_graph("SELECT ?s ?p ?o WHERE { ?s ?p ?o }")
        assert isinstance(results, list)
        assert results[0]['s'] == 'subject'
        assert results[0]['p'] == 'predicate'
        assert results[0]['o'] == 'object'

@pytest.mark.asyncio
async def test_update_graph():
    with patch.object(RemoteKnowledgeGraphManager, 'update_graph', new_callable=AsyncMock) as mock_update:
        mock_update.return_value = None  # Simulate success
        remote_manager = RemoteKnowledgeGraphManager(query_endpoint="http://example.org/sparql")
        await remote_manager.update_graph("INSERT DATA { <http://example.org/subject> <http://example.org/predicate> <http://example.org/object> }")
        mock_update.assert_awaited_once()

@pytest.mark.asyncio
async def test_import_graph():
    with patch.object(RemoteKnowledgeGraphManager, 'import_graph', new_callable=AsyncMock) as mock_import:
        mock_import.return_value = None  # Simulate success
        remote_manager = RemoteKnowledgeGraphManager(query_endpoint="http://example.org/sparql")
        await remote_manager.import_graph("<http://example.org/subject> <http://example.org/predicate> <http://example.org/object> .", format="turtle")
        mock_import.assert_awaited_once()

@pytest.mark.asyncio
async def test_remote_graph_manager_integration():
    with patch.object(RemoteKnowledgeGraphManager, 'query_graph', new_callable=AsyncMock) as mock_query:
        remote_manager = RemoteKnowledgeGraphManager(query_endpoint="http://example.org/sparql")
        # Simulate sensor data query
        mock_query.return_value = [{"sensor": f"sensor{i}"} for i in range(3)]
        results = await remote_manager.query_graph("sensor query")
        assert len(results) == 3
        # Simulate machine status query
        mock_query.return_value = [
            {"machine": "machine1", "status": "Nominal"},
            {"machine": "machine2", "status": "Maintenance"}
        ]
        results = await remote_manager.query_graph("machine status query")
        assert len(results) == 2
        for result in results:
            assert 'machine' in result
            assert 'status' in result
            assert result['status'] in ["Nominal", "Maintenance", "Error"]
        # Simulate task query
        mock_query.return_value = [{"task": f"task{i}"} for i in range(2)]
        results = await remote_manager.query_graph("task query")
        assert len(results) == 2 