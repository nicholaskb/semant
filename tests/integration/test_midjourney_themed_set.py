"""Test the Midjourney themed set generation functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import json

# Import the function we're testing
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from main import _generate_theme_aware_prompt, app


class TestThemeAwarePromptGenerator:
    """Test the internal theme-aware prompt generator."""
    
    def test_marvel_theme_detection(self):
        """Test that Marvel/superhero themes generate appropriate content."""
        prompt = _generate_theme_aware_prompt("Marvel superheroes cinematic universe")
        
        # Should contain Marvel theme
        assert "Marvel superheroes cinematic universe" in prompt
        assert "cinematic portrait" in prompt
        
        # Should have superhero-related elements (at least one of these)
        superhero_elements = [
            "vigilante", "hero", "soldier", "guardian", "defender",
            "sorcerer", "innovator", "spy", "titan", "channeler",
            "skyscraper", "rooftop", "lab", "helipad", "command center",
            "repulsors", "shield", "sigil", "webline", "lightning"
        ]
        assert any(element in prompt.lower() for element in superhero_elements), \
            f"Prompt should contain superhero elements: {prompt}"
        
        # Should have standard structure elements
        assert "subject:" in prompt
        assert "setting:" in prompt
        assert "composition:" in prompt
        assert "no text, no watermark" in prompt
    
    def test_fantasy_theme_detection(self):
        """Test that fantasy themes generate appropriate content."""
        prompt = _generate_theme_aware_prompt("Lord of the Rings fantasy medieval")
        
        # Should contain fantasy theme
        assert "Lord of the Rings fantasy medieval" in prompt
        
        # Should have fantasy-related elements
        fantasy_elements = [
            "scout", "captain", "smith", "scholar", "rider",
            "sentry", "mariner", "emissary", "archer", "tracker",
            "mountain", "courtyard", "grasslands", "forest", "archive",
            "cloak", "helm", "banner", "map", "arrow", "blade", "scroll"
        ]
        assert any(element in prompt.lower() for element in fantasy_elements), \
            f"Prompt should contain fantasy elements: {prompt}"
    
    def test_neutral_theme(self):
        """Test that neutral themes generate modern/contemporary content."""
        prompt = _generate_theme_aware_prompt("corporate headshot")
        
        # Should contain the theme
        assert "corporate headshot" in prompt
        
        # Should have modern/neutral elements
        modern_elements = [
            "photographer", "runner", "model", "guitarist", "chef",
            "driver", "stylist", "researcher", "explorer", "director",
            "downtown", "studio", "warehouse", "station", "boardwalk",
            "atrium", "rooftop", "gallery", "street", "diner"
        ]
        assert any(element in prompt.lower() for element in modern_elements), \
            f"Prompt should contain modern elements: {prompt}"
    
    def test_prompt_structure_consistency(self):
        """Test that all prompts follow the expected structure."""
        themes = [
            "Marvel superheroes",
            "fantasy medieval", 
            "professional portrait"
        ]
        
        for theme in themes:
            prompt = _generate_theme_aware_prompt(theme)
            
            # Check required structure elements
            assert "subject:" in prompt
            assert "setting:" in prompt
            assert "composition:" in prompt
            assert "lighting:" in prompt
            assert "mood/color:" in prompt
            assert "style:" in prompt
            assert "action:" in prompt
            assert "details:" in prompt
            assert "no text, no watermark" in prompt
            
            # Check it starts with the theme
            assert prompt.startswith(theme)
            
            # Check it mentions keeping the referenced face
            assert "keep the referenced face as the protagonist" in prompt


@pytest.mark.asyncio
class TestThemedSetEndpoint:
    """Test the /api/midjourney/generate-themed-set endpoint."""
    
    @pytest.fixture
    def test_client(self):
        """Provide a test client for the FastAPI app."""
        from fastapi.testclient import TestClient
        return TestClient(app)
    
    async def test_themed_set_requires_face_urls(self, test_client):
        """Test that the endpoint requires face image URLs."""
        response = test_client.post(
            "/api/midjourney/generate-themed-set",
            json={
                "theme": "Marvel superheroes",
                "face_image_urls": [],  # Empty list should fail
                "count": 3
            }
        )
        assert response.status_code == 400
        assert "face_image_urls must include at least one URL" in response.json()["detail"]
    
    @patch('main._midjourney_client')
    @patch('main.poll_and_store_task')
    async def test_themed_set_marvel_theme(self, mock_poll, mock_client, test_client):
        """Test that Marvel theme generates appropriate prompts."""
        # Mock the Midjourney client
        mock_client.submit_imagine = AsyncMock(return_value={
            "data": {"task_id": "test-task-123"}
        })
        
        response = test_client.post(
            "/api/midjourney/generate-themed-set",
            json={
                "theme": "Marvel superheroes cinematic",
                "face_image_urls": ["https://example.com/face1.jpg"],
                "count": 2
            }
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Should return task list
        assert "tasks" in result
        assert len(result["tasks"]) > 0
        
        # Check that submit_imagine was called with Marvel-themed prompts
        calls = mock_client.submit_imagine.call_args_list
        for call in calls:
            prompt = call.kwargs.get("prompt", "")
            # Should contain Marvel theme or superhero elements
            assert ("Marvel" in prompt or "superhero" in prompt or 
                   any(hero in prompt.lower() for hero in ["titan", "hero", "vigilante"]))
    
    @patch('main._planner', None)  # Set planner to None to test without refinement
    @patch('main._midjourney_client')
    async def test_themed_set_without_refinement(self, mock_client, test_client):
        """Test that themed set works without Planner refinement."""
        mock_client.submit_imagine = AsyncMock(return_value={
            "data": {"task_id": "test-task-456"}
        })
        
        response = test_client.post(
            "/api/midjourney/generate-themed-set",
            json={
                "theme": "Marvel superheroes",
                "face_image_urls": ["https://example.com/face1.jpg"],
                "count": 1
            }
        )
        
        assert response.status_code == 200
        
        # Check that submit_imagine was called
        mock_client.submit_imagine.assert_called_once()
        submitted_prompt = mock_client.submit_imagine.call_args.kwargs["prompt"]
        
        # Should still have Marvel theme elements from internal generator
        assert "Marvel" in submitted_prompt or any(
            hero in submitted_prompt.lower() 
            for hero in ["titan", "hero", "vigilante", "defender"]
        )
    
    @patch('main._midjourney_client')
    async def test_themed_set_version_and_mode(self, mock_client, test_client):
        """Test that themed set uses correct version (v7) and mode (fast)."""
        mock_client.submit_imagine = AsyncMock(return_value={
            "data": {"task_id": "test-task-789"}
        })
        
        response = test_client.post(
            "/api/midjourney/generate-themed-set",
            json={
                "theme": "portrait photography",
                "face_image_urls": ["https://example.com/face1.jpg"],
                "count": 1
            }
        )
        
        assert response.status_code == 200
        
        # Check the parameters passed to submit_imagine
        mock_client.submit_imagine.assert_called_once()
        call_kwargs = mock_client.submit_imagine.call_args.kwargs
        
        assert call_kwargs["model_version"] == "v7"
        assert call_kwargs["process_mode"] == "fast"
        assert call_kwargs.get("oref_url") is not None  # Should use oref for v7
        assert call_kwargs.get("oref_weight") == 120  # Default ow value
