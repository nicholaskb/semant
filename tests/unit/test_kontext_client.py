import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from kontext_integration.client import KontextClient, KontextError, poll_until_complete
import httpx
import asyncio

@pytest.fixture
def mock_env():
    with patch.dict("os.environ", {"KONTEXT_API_TOKEN": "fake-token"}):
        yield

@pytest.fixture
def client(mock_env):
    return KontextClient()

@pytest.mark.asyncio
async def test_submit_generate(client):
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"task_id": "task-123"}}
        mock_request.return_value = mock_response

        result = await client.submit_generate(prompt="a cool cat")
        
        assert result == {"data": {"task_id": "task-123"}}
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][1] == "https://api.goapi.ai/api/v1/task"
        assert call_args[1]["json"]["input"]["prompt"] == "a cool cat"
        assert call_args[1]["json"]["model"] == "kontext"

@pytest.mark.asyncio
async def test_submit_action(client):
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"task_id": "task-456"}}
        mock_request.return_value = mock_response

        result = await client.submit_action(origin_task_id="task-123", action="upscale")
        
        assert result == {"data": {"task_id": "task-456"}}
        call_args = mock_request.call_args
        assert call_args[1]["json"]["task_type"] == "upscale"
        assert call_args[1]["json"]["input"]["origin_task_id"] == "task-123"

@pytest.mark.asyncio
async def test_poll_task(client):
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"status": "completed"}}
        mock_request.return_value = mock_response

        result = await client.poll_task("task-123")
        assert result == {"data": {"status": "completed"}}
        assert "task-123" in mock_request.call_args[0][1]

@pytest.mark.asyncio
async def test_error_handling(client):
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("Bad Request", request=None, response=mock_response)
        mock_request.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            await client.submit_generate("fail")

@pytest.mark.asyncio
async def test_poll_until_complete(client):
    # Mock poll_task to return pending twice then completed
    client.poll_task = AsyncMock(side_effect=[
        {"data": {"status": "pending"}},
        {"data": {"status": "pending"}},
        {"data": {"status": "completed", "url": "http://image.png"}}
    ])

    # Use a short interval for test speed
    result = await poll_until_complete(client, "task-123", interval=0.01)
    
    assert result["status"] == "completed"
    assert result["url"] == "http://image.png"
    assert client.poll_task.call_count == 3

