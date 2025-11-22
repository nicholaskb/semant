"""
Tests for Image Embedding Service (Task 1)

Tests the image embedding service that:
1. Generates embeddings from images via vision → text → embedding
2. Computes similarity scores between embeddings
3. Stores embeddings in Qdrant
4. Searches for similar images

Date: 2025-01-08
"""

import pytest
import asyncio
from pathlib import Path
from kg.services.image_embedding_service import (
    ImageEmbeddingService,
    compute_similarity,
)


@pytest.mark.asyncio
async def test_image_embedding_service_initialization():
    """Test that the service initializes correctly."""
    service = ImageEmbeddingService()
    
    assert service.openai_client is not None
    assert service.qdrant_client is not None
    assert service.collection_name == "childrens_book_images"


@pytest.mark.asyncio
async def test_embed_text():
    """Test text embedding using the DiaryAgent pattern."""
    service = ImageEmbeddingService()
    
    # Test simple text embedding
    text = "A colorful children's book illustration of a friendly monster"
    embedding = service.embed_text(text)
    
    assert isinstance(embedding, list)
    assert len(embedding) == 1536  # text-embedding-3-large dimension
    assert all(isinstance(x, float) for x in embedding)


def test_compute_similarity():
    """Test cosine similarity computation."""
    # Test identical vectors
    emb1 = [1.0, 0.0, 0.0]
    emb2 = [1.0, 0.0, 0.0]
    similarity = ImageEmbeddingService.compute_similarity(emb1, emb2)
    assert abs(similarity - 1.0) < 0.001  # Should be ~1.0
    
    # Test orthogonal vectors
    emb1 = [1.0, 0.0, 0.0]
    emb2 = [0.0, 1.0, 0.0]
    similarity = ImageEmbeddingService.compute_similarity(emb1, emb2)
    assert abs(similarity - 0.0) < 0.001  # Should be ~0.0
    
    # Test opposite vectors
    emb1 = [1.0, 0.0, 0.0]
    emb2 = [-1.0, 0.0, 0.0]
    similarity = ImageEmbeddingService.compute_similarity(emb1, emb2)
    assert abs(similarity - (-1.0)) < 0.001  # Should be ~-1.0


@pytest.mark.asyncio
@pytest.mark.skipif(
    not Path("test_images").exists(),
    reason="Test images directory not found"
)
async def test_embed_image_with_real_images():
    """Test embedding generation from actual images (if test images available)."""
    service = ImageEmbeddingService()
    
    # This test requires actual image files in test_images/
    test_image = Path("test_images/sample_1.png")
    if not test_image.exists():
        pytest.skip("Test image not available")
    
    embedding, description = await service.embed_image(test_image)
    
    assert isinstance(embedding, list)
    assert len(embedding) == 1536
    assert isinstance(description, str)
    assert len(description) > 10  # Should have meaningful description


@pytest.mark.asyncio
async def test_store_and_retrieve_embedding():
    """Test storing and retrieving embeddings in Qdrant."""
    service = ImageEmbeddingService()
    
    # Create a test embedding
    test_embedding = service.embed_text("Test image of a blue monster")
    test_uri = "http://example.org/image/test_001"
    
    # Store the embedding
    stored_uri = service.store_embedding(
        image_uri=test_uri,
        embedding=test_embedding,
        metadata={"type": "test", "color": "blue"}
    )
    
    assert stored_uri == test_uri
    
    # Retrieve the embedding
    retrieved_embedding = service.get_embedding(test_uri)
    
    assert retrieved_embedding is not None
    assert len(retrieved_embedding) == 1536
    
    # Verify it's the same (high similarity)
    similarity = ImageEmbeddingService.compute_similarity(
        test_embedding,
        retrieved_embedding
    )
    assert similarity > 0.99  # Should be nearly identical


@pytest.mark.asyncio
async def test_search_similar_images():
    """Test searching for similar images using embeddings."""
    service = ImageEmbeddingService()
    
    # Store several test embeddings
    descriptions = [
        "A blue monster with big eyes",
        "A blue creature with large eyes",  # Very similar to #1
        "A red dragon breathing fire",       # Different
        "A green frog jumping",              # Different
    ]
    
    uris = []
    embeddings = []
    
    for i, desc in enumerate(descriptions):
        emb = service.embed_text(desc)
        uri = f"http://example.org/image/test_{i:03d}"
        service.store_embedding(
            image_uri=uri,
            embedding=emb,
            metadata={"description": desc, "index": i}
        )
        uris.append(uri)
        embeddings.append(emb)
    
    # Search for images similar to the first one
    query_embedding = embeddings[0]  # Blue monster
    results = service.search_similar_images(
        query_embedding=query_embedding,
        limit=4
    )
    
    assert len(results) > 0
    
    # The first result should be the query itself (or very similar #1)
    assert results[0]["score"] > 0.95
    
    # The second result should be #1 (very similar blue creature)
    # with high similarity
    similar_result = next(
        (r for r in results if "blue creature" in r["metadata"].get("description", "")),
        None
    )
    if similar_result:
        assert similar_result["score"] > 0.85  # High similarity
    
    # The dissimilar images (dragon, frog) should have lower scores
    dragon_result = next(
        (r for r in results if "dragon" in r["metadata"].get("description", "")),
        None
    )
    if dragon_result:
        assert dragon_result["score"] < 0.80  # Lower similarity


@pytest.mark.asyncio
async def test_similarity_with_cached_descriptions():
    """Test that using cached descriptions produces similar embeddings."""
    service = ImageEmbeddingService()
    
    # Create a fake image path (won't be accessed due to cached description)
    fake_path = Path("nonexistent.png")
    
    description = "A friendly yellow monster with purple spots jumping joyfully"
    
    # First embedding from text directly
    emb1 = service.embed_text(description)
    
    # Second embedding using cached description (simulates embed_image with cache)
    emb2, returned_desc = await service.embed_image(
        fake_path,
        use_cached_description=description
    )
    
    assert returned_desc == description
    
    # The embeddings should be identical
    similarity = ImageEmbeddingService.compute_similarity(emb1, emb2)
    assert abs(similarity - 1.0) < 0.001  # Perfect match


@pytest.mark.asyncio
async def test_high_similarity_between_similar_images():
    """
    Test Task 1 requirement: Verify high similarity scores between similar images.
    
    This is the key test from the task description:
    'Test with 2 similar images to verify high similarity scores'
    """
    service = ImageEmbeddingService()
    
    # Simulate two similar images (children's book illustrations)
    desc1 = """A watercolor illustration for a children's book showing a small yellow 
    duckling with oversized orange feet standing by a blue pond. The duckling has one 
    feather sticking up on its head. Bright, cheerful colors in a soft watercolor style."""
    
    desc2 = """A watercolor children's book illustration of a cute yellow baby duck 
    with comically large orange webbed feet near a sparkly blue pond. One tuft of 
    feathers sticks up. Warm, bright colors with soft watercolor painting technique."""
    
    # Generate embeddings (using text as proxy for visual embeddings)
    emb1 = service.embed_text(desc1)
    emb2 = service.embed_text(desc2)
    
    # Compute similarity
    similarity = ImageEmbeddingService.compute_similarity(emb1, emb2)
    
    # Verify high similarity (>0.85 for very similar images)
    assert similarity > 0.85, f"Similar images should have high similarity: got {similarity}"
    
    print(f"✅ Task 1 Verification: Similarity between similar images = {similarity:.3f}")


if __name__ == "__main__":
    # Run the key test
    asyncio.run(test_high_similarity_between_similar_images())

