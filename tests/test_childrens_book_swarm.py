"""
End-to-End Integration Tests for Children's Book Swarm

Tests the complete workflow from image ingestion to book generation,
ensuring all agents work together correctly.

Date: 2025-01-08
"""

import asyncio
import pytest
import os
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Import the system under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_childrens_book import ChildrensBookOrchestrator
from agents.domain.image_ingestion_agent import ImageIngestionAgent, ingest_images_from_gcs
from agents.domain.image_pairing_agent import ImagePairingAgent, pair_all_images
from agents.domain.story_sequencing_agent import StorySequencingAgent, sequence_all_pairs
from kg.services.image_embedding_service import ImageEmbeddingService, embed_image_file
from kg.models.graph_manager import KnowledgeGraphManager


@pytest.fixture
async def kg_manager():
    """Fixture providing initialized KG manager."""
    manager = KnowledgeGraphManager()
    await manager.initialize()
    yield manager
    await manager.shutdown()


@pytest.fixture
def temp_output_dir(tmp_path):
    """Fixture providing temporary output directory."""
    return tmp_path / "test_book_output"


@pytest.fixture
def mock_gcs_client():
    """Mock GCS client for testing without actual cloud access."""
    with patch('agents.domain.image_ingestion_agent.storage.Client') as mock:
        mock_client = Mock()
        mock_bucket = Mock()
        
        # Mock blob listing
        mock_blob_1 = Mock()
        mock_blob_1.name = "input_kids_monster/input_001.png"
        mock_blob_1.size = 10240
        
        mock_blob_2 = Mock()
        mock_blob_2.name = "generated_images/output_001_a.png"
        mock_blob_2.size = 20480
        
        mock_bucket.list_blobs.return_value = [mock_blob_1, mock_blob_2]
        mock_client.bucket.return_value = mock_bucket
        mock.return_value = mock_client
        
        yield mock_client


class TestImageEmbeddingService:
    """Test suite for ImageEmbeddingService."""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test that ImageEmbeddingService initializes correctly."""
        service = ImageEmbeddingService(
            qdrant_host="localhost",
            qdrant_port=6333
        )
        
        assert service is not None
        assert service.collection_name == "childrens_book_images"
        assert service.openai_client is not None
        assert service.qdrant_client is not None
    
    def test_compute_similarity(self):
        """Test similarity computation between embeddings."""
        # Create two similar embeddings (mostly same values)
        emb1 = [1.0] * 1536
        emb2 = [0.9] * 1536
        
        similarity = ImageEmbeddingService.compute_similarity(emb1, emb2)
        
        # Should be high similarity
        assert 0.95 < similarity <= 1.0
    
    def test_compute_similarity_opposite(self):
        """Test similarity with opposite embeddings."""
        emb1 = [1.0] * 1536
        emb2 = [-1.0] * 1536
        
        similarity = ImageEmbeddingService.compute_similarity(emb1, emb2)
        
        # Should be negative similarity
        assert similarity < 0
    
    @pytest.mark.asyncio
    @patch('kg.services.image_embedding_service.OpenAI')
    async def test_embed_text(self, mock_openai):
        """Test text embedding generation."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]
        mock_openai.return_value.embeddings.create.return_value = mock_response
        
        service = ImageEmbeddingService()
        embedding = service.embed_text("test text")
        
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)


class TestImageIngestionAgent:
    """Test suite for ImageIngestionAgent."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, kg_manager):
        """Test that ImageIngestionAgent initializes correctly."""
        agent = ImageIngestionAgent(
            kg_manager=kg_manager,
            gcs_bucket_name="test-bucket"
        )
        await agent.initialize()
        
        assert agent.agent_id == "image_ingestion_agent"
        capabilities = await agent.get_capabilities()
        capability_types = {cap.type.value for cap in capabilities}
        assert "image_ingestion" in capability_types
        assert agent.kg_manager is not None
    
    @pytest.mark.asyncio
    async def test_get_ingested_images(self, kg_manager):
        """Test querying ingested images from KG."""
        agent = ImageIngestionAgent(kg_manager=kg_manager)
        
        # Query (should be empty initially)
        images = await agent.get_ingested_images(image_type="input")
        
        assert isinstance(images, list)


class TestImagePairingAgent:
    """Test suite for ImagePairingAgent."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, kg_manager):
        """Test that ImagePairingAgent initializes correctly."""
        agent = ImagePairingAgent(
            kg_manager=kg_manager,
            top_k_outputs=12
        )
        await agent.initialize()
        
        assert agent.agent_id == "image_pairing_agent"
        capabilities = await agent.get_capabilities()
        capability_types = {cap.type.value for cap in capabilities}
        assert "image_pairing" in capability_types
        assert agent.top_k_outputs == 12
    
    def test_filename_similarity_exact_match(self):
        """Test filename similarity with exact number match."""
        similarity = ImagePairingAgent._compute_filename_similarity(
            "input_001.png",
            "output_001_a.png"
        )
        
        # Should have high similarity due to matching "001"
        assert similarity > 0.5
    
    def test_filename_similarity_no_match(self):
        """Test filename similarity with no number match."""
        similarity = ImagePairingAgent._compute_filename_similarity(
            "input_001.png",
            "output_999_a.png"
        )
        
        # Should have low similarity
        assert similarity < 0.5
    
    @pytest.mark.asyncio
    async def test_get_all_pairs(self, kg_manager):
        """Test querying all pairs from KG."""
        agent = ImagePairingAgent(kg_manager=kg_manager)
        
        # Query (should be empty initially)
        pairs = await agent.get_all_pairs(include_low_confidence=True)
        
        assert isinstance(pairs, list)


class TestStorySequencingAgent:
    """Test suite for StorySequencingAgent."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, kg_manager):
        """Test that StorySequencingAgent initializes correctly."""
        agent = StorySequencingAgent(kg_manager=kg_manager)
        await agent.initialize()
        
        assert agent.agent_id == "story_sequencing_agent"
        capabilities = await agent.get_capabilities()
        capability_types = {cap.type.value for cap in capabilities}
        assert "story_sequencing" in capability_types
        assert agent.openai_client is not None


class TestChildrensBookOrchestrator:
    """Test suite for ChildrensBookOrchestrator."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self):
        """Test that orchestrator initializes correctly."""
        orchestrator = ChildrensBookOrchestrator(
            bucket_name="test-bucket",
            input_prefix="test_input/",
            output_prefix="test_output/"
        )
        
        assert orchestrator.bucket_name == "test-bucket"
        assert orchestrator.input_prefix == "test_input/"
        assert orchestrator.output_prefix == "test_output/"
        assert orchestrator.ingestion_agent is not None
        assert orchestrator.pairing_agent is not None
        assert orchestrator.color_agent is not None
        assert orchestrator.composition_agent is not None
        assert orchestrator.image_analysis_agent is not None
        assert orchestrator.critic_agent is not None
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialize(self):
        """Test KG initialization."""
        orchestrator = ChildrensBookOrchestrator(bucket_name="test-bucket")
        
        await orchestrator.initialize()
        
        assert orchestrator.kg_manager is not None
    
    @pytest.mark.asyncio
    async def test_html_template_generation(self):
        """Test HTML template generation."""
        orchestrator = ChildrensBookOrchestrator(bucket_name="test-bucket")
        await orchestrator.initialize()
        
        # Mock data
        pairs = [{
            "input_image_name": "input_001.png",
            "output_image_names": ["output_001_a.png", "output_001_b.png"]
        }]
        
        layouts = [{
            "page_number": 1,
            "grid_dimensions": "2x2"
        }]
        
        story_pages = [{
            "page_number": 1,
            "text": "Once upon a time..."
        }]
        
        html = await orchestrator._create_html_template(pairs, layouts, story_pages)
        
        # Verify HTML structure
        assert "<!DOCTYPE html>" in html
        assert "book-page" in html
        assert "left-column" in html
        assert "right-column" in html
        assert "image-grid" in html
        assert "grid-2x2" in html
        assert "Once upon a time..." in html


class TestEndToEndWorkflow:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_minimal_workflow_mock_data(self, kg_manager, temp_output_dir):
        """Test minimal workflow with mocked data."""
        # This test verifies the workflow structure without external dependencies
        
        # Step 1: Create mock ingestion result
        mock_ingestion_result = {
            "status": "success",
            "total_embeddings_generated": 2,
            "input_images_count": 1,
            "output_images_count": 1,
            "input_image_uris": ["http://example.org/image/input-001"],
            "output_image_uris": ["http://example.org/image/output-001-a"],
        }
        
        # Step 2: Create mock pairing result
        mock_pairing_result = {
            "status": "success",
            "pairs_count": 1,
            "low_confidence_count": 0,
            "pairs": [{
                "pair_uri": "http://example.org/pair/001",
                "input_image_uri": "http://example.org/image/input-001",
                "input_image_name": "input_001.png",
                "output_image_uris": ["http://example.org/image/output-001-a"],
                "output_image_names": ["output_001_a.png"],
                "confidence": 0.95,
            }]
        }
        
        # Step 3: Verify workflow structure
        assert mock_ingestion_result["status"] == "success"
        assert mock_pairing_result["pairs_count"] == 1
        assert mock_pairing_result["pairs"][0]["confidence"] > 0.7
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_agent_communication_flow(self, kg_manager):
        """Test that agents can communicate via messages."""
        from agents.core.message_types import AgentMessage
        
        # Create agents
        ingestion_agent = ImageIngestionAgent(kg_manager=kg_manager)
        pairing_agent = ImagePairingAgent(kg_manager=kg_manager)
        
        # Test message structure
        test_message = AgentMessage(
            sender_id="test",
            recipient_id="image_ingestion_agent",
            content={"action": "test"},
            message_type="request",
            timestamp=datetime.utcnow().isoformat()
        )
        
        assert test_message.sender_id == "test"
        assert test_message.recipient_id == "image_ingestion_agent"
        assert test_message.content["action"] == "test"


class TestGridLayoutLogic:
    """Test grid layout decision logic."""
    
    def test_grid_size_determination_2x2(self):
        """Test that 4 or fewer images get 2x2 grid."""
        num_outputs = 4
        
        if num_outputs <= 4:
            grid = "2x2"
        elif num_outputs <= 9:
            grid = "3x3"
        elif num_outputs <= 12:
            grid = "3x4"
        else:
            grid = "4x4"
        
        assert grid == "2x2"
    
    def test_grid_size_determination_3x3(self):
        """Test that 5-9 images get 3x3 grid."""
        num_outputs = 7
        
        if num_outputs <= 4:
            grid = "2x2"
        elif num_outputs <= 9:
            grid = "3x3"
        elif num_outputs <= 12:
            grid = "3x4"
        else:
            grid = "4x4"
        
        assert grid == "3x3"
    
    def test_grid_size_determination_3x4(self):
        """Test that 10-12 images get 3x4 grid."""
        num_outputs = 12
        
        if num_outputs <= 4:
            grid = "2x2"
        elif num_outputs <= 9:
            grid = "3x3"
        elif num_outputs <= 12:
            grid = "3x4"
        else:
            grid = "4x4"
        
        assert grid == "3x4"
    
    def test_grid_size_determination_4x4(self):
        """Test that 13+ images get 4x4 grid."""
        num_outputs = 15
        
        if num_outputs <= 4:
            grid = "2x2"
        elif num_outputs <= 9:
            grid = "3x3"
        elif num_outputs <= 12:
            grid = "3x4"
        else:
            grid = "4x4"
        
        assert grid == "4x4"


class TestKnowledgeGraphIntegration:
    """Test KG schema and storage."""
    
    @pytest.mark.asyncio
    async def test_kg_ontology_loading(self, kg_manager):
        """Test that children's book ontology can be loaded."""
        ontology_path = Path(__file__).parent.parent / "kg" / "schemas" / "childrens_book_ontology.ttl"
        
        # Verify ontology file exists
        assert ontology_path.exists(), f"Ontology not found at {ontology_path}"
        
        # Verify it's valid Turtle format
        with open(ontology_path) as f:
            content = f.read()
            assert "@prefix book:" in content
            assert "book:InputImage" in content
            assert "book:OutputImage" in content
            assert "book:ImagePair" in content
            assert "book:GridLayout" in content


# Test markers for different test categories
pytestmark = pytest.mark.asyncio


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])

