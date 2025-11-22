import pytest
import httpx
from unittest.mock import AsyncMock, patch

from midjourney_integration.client import MidjourneyClient

@pytest.fixture
def client():
    """Provides a MidjourneyClient instance with a dummy token."""
    return MidjourneyClient(api_token="test-token")

@pytest.fixture
def mock_httpx_client():
    """Mocks the httpx.AsyncClient for controlled API responses."""
    with patch("httpx.AsyncClient") as mock_client_patch:
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=httpx.Response(200, json={"task_id": "default-task-id"}))
        mock_instance.get = AsyncMock()
        
        async def __aenter__(*args, **kwargs):
            return mock_instance

        async def __aexit__(*args, **kwargs):
            pass

        mock_client_patch.return_value.__aenter__ = __aenter__
        mock_client_patch.return_value.__aexit__ = __aexit__
        
        yield mock_instance

@pytest.mark.parametrize(
    "prompt, expected_prompt, mock_response",
    [
        (
            "--oref https://example.com/ref.png --ow 500",
            "image --oref https://example.com/ref.png --ow 500",
            {"task_id": "imagine-task-oref", "status": "pending"},
        ),
        (
            "A cat --v 7 --cref https://example.com/ref.png --cw 100",
            "A cat --v 7",
            {"task_id": "imagine-task-cref", "status": "pending"},
        ),
        (
            "A normal prompt --v 6",
            "A normal prompt --v 6",
            {"task_id": "imagine-task-normal", "status": "pending"},
        ),
    ],
)
async def test_submit_imagine_prompt_handling(
    client, mock_httpx_client, prompt, expected_prompt, mock_response
):
    """
    Tests various prompt transformations:
    1. --oref prefixing.
    2. --cref removal with v7.
    3. Standard prompt preservation.
    """
    mock_httpx_client.post.return_value = httpx.Response(200, json=mock_response)

    result = await client.submit_imagine(prompt=prompt, aspect_ratio="1:1", process_mode="relax")

    # The `_request` method is where the call happens.
    # We inspect the arguments passed to the mock's `post` method.
    mock_httpx_client.post.assert_awaited_once()
    called_with_json = mock_httpx_client.post.call_args.kwargs['json']
    
    assert called_with_json['input']['prompt'] == expected_prompt
    assert result == mock_response

