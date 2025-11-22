import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from pathlib import Path
import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from midjourney_integration.client import MidjourneyClient

class TestNanoBananaIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Provide a dummy token to bypass validation
        self.client = MidjourneyClient(api_token="dummy_token")

    @patch('httpx.AsyncClient.post')
    async def test_nano_banana_model_selection(self, mock_post):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = {"id": "test-id", "status": "success"}
        
        # Configure the mock to return the response
        mock_post.return_value = mock_response

        # Call the method with nano-banana model
        response = await self.client.submit_imagine("test prompt", aspect_ratio=None, process_mode=None, model_version="nano-banana")

        # Verify the request was made with correct parameters
        args, kwargs = mock_post.call_args
        
        # Check payload
        payload = kwargs['json']
        self.assertEqual(payload['model'], 'nano-banana')
        self.assertEqual(payload['input']['prompt'], 'test prompt')
        
        # Verify response
        self.assertEqual(response['id'], 'test-id')
        self.assertEqual(response['status'], 'success')

    @patch('httpx.AsyncClient.post')
    async def test_default_model_selection(self, mock_post):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = {"id": "test-id", "status": "success"}
        mock_post.return_value = mock_response

        # Call with default (no model specified)
        await self.client.submit_imagine("test prompt", aspect_ratio=None, process_mode=None)

        # Verify payload uses default 'midjourney'
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        self.assertEqual(payload['model'], 'midjourney')

    @patch('httpx.AsyncClient.post')
    async def test_other_model_version(self, mock_post):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.json.return_value = {"id": "test-id", "status": "success"}
        mock_post.return_value = mock_response

        # Call with v6
        await self.client.submit_imagine("test prompt", aspect_ratio=None, process_mode=None, model_version="v6")

        # Verify payload uses default 'midjourney' but includes version in input
        args, kwargs = mock_post.call_args
        payload = kwargs['json']
        self.assertEqual(payload['model'], 'midjourney')
        self.assertEqual(payload['input']['version'], 'v6')

if __name__ == '__main__':
    unittest.main()


