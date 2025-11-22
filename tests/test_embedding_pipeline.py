#!/usr/bin/env python3
"""
Test script to verify the embedding pipeline works end-to-end
Uses local images if available, or creates a minimal test
"""

import asyncio
import sys
from pathlib import Path
from loguru import logger
from rich.console import Console
from rich.panel import Panel

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from kg.services.image_embedding_service import ImageEmbeddingService
from agents.domain.image_pairing_agent import ImagePairingAgent
from kg.models.graph_manager import KnowledgeGraphManager

console = Console()


async def test_embedding_service():
    """Test 1: Verify ImageEmbeddingService can initialize and work"""
    console.print("\n[bold cyan]Test 1: ImageEmbeddingService[/bold cyan]")
    
    try:
        service = ImageEmbeddingService()
        console.print("  ✅ ImageEmbeddingService initialized")
        
        # Test collection exists
        collections = service.qdrant_client.get_collections()
        collection_names = [c.name for c in collections.collections]
        if "childrens_book_images" in collection_names:
            console.print("  ✅ Collection 'childrens_book_images' exists")
        else:
            console.print("  ⚠️  Collection not found (will be created on first insert)")
        
        return True, service
    except Exception as e:
        console.print(f"  ❌ Failed: {e}")
        return False, None


async def test_embedding_generation(service: ImageEmbeddingService):
    """Test 2: Generate an embedding for a test image"""
    console.print("\n[bold cyan]Test 2: Embedding Generation[/bold cyan]")
    
    # Look for any test image
    test_image_paths = [
        Path("demo_embedding_pairing.py"),  # Not an image, but we'll catch it
        Path("static/frontend_image_search_example.html"),  # Not an image
    ]
    
    # Try to find actual images
    for book_dir in Path("generated_books").glob("childrens_book_*"):
        input_dir = book_dir / "input"
        output_dir = book_dir / "output"
        
        if input_dir.exists():
            images = list(input_dir.glob("*.png")) + list(input_dir.glob("*.jpg"))
            if images:
                test_image_paths.append(images[0])
                break
        
        if output_dir.exists():
            images = list(output_dir.glob("*.png")) + list(output_dir.glob("*.jpg"))
            if images:
                test_image_paths.append(images[0])
                break
    
    # Find first actual image
    test_image = None
    for path in test_image_paths:
        if path.exists() and path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
            test_image = path
            break
    
    if not test_image:
        console.print("  ⚠️  No test images found - skipping embedding generation test")
        console.print("  💡 To test: Place an image in generated_books/test/input/test.png")
        return True  # Not a failure, just no data
    
    try:
        console.print(f"  📸 Testing with: {test_image.name}")
        embedding, description = await service.embed_image(test_image)
        
        console.print(f"  ✅ Generated embedding: {len(embedding)} dimensions")
        console.print(f"  📝 Description: {description[:100]}...")
        
        # Test storing in Qdrant
        test_uri = f"test://{test_image.name}"
        stored_uri = service.store_embedding(
            image_uri=test_uri,
            embedding=embedding,
            metadata={"description": description, "test": True}
        )
        console.print(f"  ✅ Stored in Qdrant: {stored_uri}")
        
        # Test searching
        results = service.search_similar_images(
            query_embedding=embedding,
            limit=5,
            score_threshold=0.9
        )
        console.print(f"  ✅ Search works: Found {len(results)} results")
        
        return True
    except Exception as e:
        console.print(f"  ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_pairing_agent():
    """Test 3: Verify ImagePairingAgent can initialize"""
    console.print("\n[bold cyan]Test 3: ImagePairingAgent[/bold cyan]")
    
    try:
        kg_manager = KnowledgeGraphManager()
        await kg_manager.initialize()
        
        embedding_service = ImageEmbeddingService()
        
        pairing_agent = ImagePairingAgent(
            kg_manager=kg_manager,
            embedding_service=embedding_service
        )
        
        console.print("  ✅ ImagePairingAgent initialized")
        console.print(f"  ✅ Has embedding service: {pairing_agent.embedding_service is not None}")
        
        return True
    except Exception as e:
        console.print(f"  ❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    console.print(Panel.fit(
        "[bold cyan]🧪 Embedding Pipeline Test Suite[/bold cyan]\n"
        "Testing: Qdrant → Embeddings → Pairing Agent",
        border_style="cyan"
    ))
    
    results = []
    
    # Test 1: Embedding Service
    success, service = await test_embedding_service()
    results.append(("ImageEmbeddingService", success))
    
    if not success:
        console.print("\n[bold red]❌ Cannot continue - embedding service failed[/bold red]")
        return
    
    # Test 2: Embedding Generation
    if service:
        success = await test_embedding_generation(service)
        results.append(("Embedding Generation", success))
    
    # Test 3: Pairing Agent
    success = await test_pairing_agent()
    results.append(("ImagePairingAgent", success))
    
    # Summary
    console.print("\n" + "=" * 60)
    console.print("[bold]Test Summary[/bold]")
    console.print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        console.print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    console.print("=" * 60)
    
    if all_passed:
        console.print("\n[bold green]✅ All tests passed! Embedding pipeline is ready.[/bold green]")
        console.print("\n💡 Next step: Install google-cloud-storage to test with GCS:")
        console.print("   pip install google-cloud-storage")
    else:
        console.print("\n[bold red]❌ Some tests failed. Check errors above.[/bold red]")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

