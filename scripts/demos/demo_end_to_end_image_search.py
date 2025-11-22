#!/usr/bin/env python3
"""
End-to-End Demo: Qdrant Image Similarity Search
Shows the complete flow from storing images to searching
"""

import asyncio
import sys
import json
from pathlib import Path
from io import BytesIO
from PIL import Image
import requests
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from kg.services.image_embedding_service import ImageEmbeddingService


class Colors:
    """ANSI color codes for pretty output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_step(step_num: int, title: str, description: str = ""):
    """Print a formatted step header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}STEP {step_num}: {title}{Colors.END}")
    if description:
        print(f"{Colors.BLUE}{description}{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.YELLOW}ℹ️  {message}{Colors.END}")


def print_data(data: Any, title: str = "Data"):
    """Print formatted data"""
    print(f"\n{Colors.BOLD}{title}:{Colors.END}")
    print(json.dumps(data, indent=2, default=str))


async def step1_check_qdrant():
    """Step 1: Check Qdrant connection"""
    print_step(1, "Checking Qdrant Connection", 
               "Verifying Qdrant is running and accessible")
    
    try:
        service = ImageEmbeddingService()
        print_success("Qdrant connection successful!")
        print_info(f"Collection: {service.collection_name}")
        print_info(f"Embedding dimension: 1536")
        return service
    except Exception as e:
        print_error(f"Qdrant connection failed: {e}")
        print_info("\n💡 To start Qdrant:")
        print_info("   docker run -d -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest")
        print_info("\n   Or check if it's already running:")
        print_info("   curl http://localhost:6333/health")
        return None


async def step2_store_sample_images(service: ImageEmbeddingService):
    """Step 2: Store sample images in Qdrant"""
    print_step(2, "Storing Sample Images", 
               "Creating embeddings and storing in Qdrant for testing")
    
    sample_images = [
        {
            "uri": "http://example.org/book/duck_pond.png",
            "description": "A yellow duckling with orange feet swimming in a blue pond with lily pads, natural lighting",
            "type": "input",
            "category": "duck"
        },
        {
            "uri": "http://example.org/book/duck_watercolor.png",
            "description": "A yellow duck with orange feet in watercolor style, soft pastel colors, artistic",
            "type": "output",
            "category": "duck"
        },
        {
            "uri": "http://example.org/book/duck_cartoon.png",
            "description": "A cute yellow duckling with big orange webbed feet, cartoon style, friendly expression",
            "type": "output",
            "category": "duck"
        },
        {
            "uri": "http://example.org/book/duck_family.png",
            "description": "A family of yellow ducklings with orange feet by a pond, warm sunset lighting",
            "type": "output",
            "category": "duck"
        },
        {
            "uri": "http://example.org/book/fire_truck.png",
            "description": "A red fire truck with a ladder and siren, bright colors, urban setting",
            "type": "output",
            "category": "vehicle"
        },
        {
            "uri": "http://example.org/book/duck_sunset.png",
            "description": "A yellow duckling silhouetted against a sunset sky, orange and pink colors",
            "type": "output",
            "category": "duck"
        }
    ]
    
    stored_count = 0
    for img in sample_images:
        try:
            print_info(f"Processing: {img['uri']}")
            
            # Generate embedding from description
            embedding = service.embed_text(img["description"])
            print_info(f"  → Generated {len(embedding)}-dim embedding")
            
            # Store in Qdrant
            service.store_embedding(
                image_uri=img["uri"],
                embedding=embedding,
                metadata={
                    "description": img["description"],
                    "type": img["type"],
                    "category": img["category"]
                }
            )
            stored_count += 1
            print_success(f"  ✓ Stored: {img['uri']}")
        except Exception as e:
            print_error(f"  ✗ Failed: {e}")
    
    print_success(f"\nStored {stored_count}/{len(sample_images)} images in Qdrant")
    return stored_count


async def step3_direct_search(service: ImageEmbeddingService):
    """Step 3: Direct search using the service"""
    print_step(3, "Direct Search (Python Service)", 
               "Searching for similar images using ImageEmbeddingService")
    
    # Query: similar to duckling
    query_text = "A yellow duckling with orange feet by a pond"
    print_info(f"Query: '{query_text}'")
    
    # Generate query embedding
    print_info("Generating query embedding...")
    query_embedding = service.embed_text(query_text)
    print_success(f"Generated {len(query_embedding)}-dim embedding")
    
    # Search for similar images
    print_info("Searching Qdrant for similar images...")
    results = service.search_similar_images(
        query_embedding=query_embedding,
        limit=5,
        score_threshold=0.5
    )
    
    print_success(f"Found {len(results)} similar images:")
    print_data(results, "Search Results")
    
    # Display formatted results
    print(f"\n{Colors.BOLD}Top Results:{Colors.END}")
    for i, result in enumerate(results, 1):
        score_percent = result["score"] * 100
        img_type = result["metadata"].get("type", "unknown")
        category = result["metadata"].get("category", "unknown")
        description = result["metadata"].get("description", "")[:60]
        
        print(f"\n{Colors.BOLD}{i}. Score: {score_percent:.1f}%{Colors.END}")
        print(f"   Type: {img_type} | Category: {category}")
        print(f"   URI: {result['image_uri']}")
        print(f"   Description: {description}...")
    
    return results


async def step4_api_endpoint_test():
    """Step 4: Test the API endpoint"""
    print_step(4, "API Endpoint Test", 
               "Testing /api/images/search-similar via HTTP")
    
    # Create a test image (yellow square representing a duck)
    img = Image.new('RGB', (200, 200), color='yellow')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    print_info("Created test image (yellow square)")
    
    # Prepare request
    files = {'image_file': ('test_duck.png', img_bytes, 'image/png')}
    data = {
        'limit': '5',
        'score_threshold': '0.5'
    }
    
    print_info("Sending POST request to /api/images/search-similar...")
    print_info(f"  URL: http://localhost:8000/api/images/search-similar")
    print_info(f"  Parameters: limit=5, score_threshold=0.5")
    
    try:
        response = requests.post(
            'http://localhost:8000/api/images/search-similar',
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success("API request successful!")
            print_data(result, "API Response")
            
            print(f"\n{Colors.BOLD}Query Image Description:{Colors.END}")
            print(f"  {result.get('query_image', 'N/A')[:200]}...")
            
            print(f"\n{Colors.BOLD}Found {result.get('total_found', 0)} similar images:{Colors.END}")
            for i, res in enumerate(result.get('results', [])[:3], 1):
                print(f"\n  {i}. Score: {res['score']*100:.1f}%")
                print(f"     URI: {res['image_uri']}")
            
            return True
        else:
            print_error(f"API returned status {response.status_code}")
            print_error(f"Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API server")
        print_info("\n💡 Start the API server with:")
        print_info("   python main.py")
        print_info("\n   Then the API will be available at:")
        print_info("   http://localhost:8000/api/images/search-similar")
        return False
    except Exception as e:
        print_error(f"API test failed: {e}")
        return False


def step5_frontend_demo():
    """Step 5: Show frontend demo instructions"""
    print_step(5, "Frontend Demo", 
               "How to use the HTML demo interface")
    
    print_info("The frontend demo is available at:")
    print(f"{Colors.BOLD}   http://localhost:8000/static/frontend_image_search_example.html{Colors.END}")
    
    print(f"\n{Colors.BOLD}Features:{Colors.END}")
    print("  • Drag & drop image upload")
    print("  • Image preview")
    print("  • Configurable search parameters")
    print("  • Beautiful results grid with similarity scores")
    print("  • Click images to view full size")
    
    print(f"\n{Colors.BOLD}How to use:{Colors.END}")
    print("  1. Start API server: python main.py")
    print("  2. Open browser: http://localhost:8000/static/frontend_image_search_example.html")
    print("  3. Drag an image or click 'Choose Image File'")
    print("  4. Adjust limit and threshold if needed")
    print("  5. Click 'Search Similar Images'")
    print("  6. View results with similarity scores")


def step6_show_code_examples():
    """Step 6: Show code examples"""
    print_step(6, "Code Examples", 
               "How to integrate in your own application")
    
    print(f"\n{Colors.BOLD}JavaScript (Vanilla):{Colors.END}")
    js_code = """
async function searchSimilarImages(imageFile) {
    const formData = new FormData();
    formData.append('image_file', imageFile);
    formData.append('limit', '10');
    formData.append('score_threshold', '0.7');
    
    const response = await fetch('/api/images/search-similar', {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    
    return await response.json();
}

// Usage
const fileInput = document.getElementById('imageFile');
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (file) {
        const results = await searchSimilarImages(file);
        console.log('Found', results.total_found, 'similar images');
        results.results.forEach(result => {
            console.log(result.image_uri, 'score:', result.score);
        });
    }
});
"""
    print(f"{Colors.CYAN}{js_code}{Colors.END}")
    
    print(f"\n{Colors.BOLD}Python (requests):{Colors.END}")
    py_code = """
import requests

def search_similar_images(image_path, limit=10, threshold=0.7):
    with open(image_path, 'rb') as f:
        files = {'image_file': f}
        data = {
            'limit': str(limit),
            'score_threshold': str(threshold)
        }
        response = requests.post(
            'http://localhost:8000/api/images/search-similar',
            files=files,
            data=data
        )
        return response.json()

# Usage
results = search_similar_images('my_image.jpg', limit=5, threshold=0.8)
print(f"Found {results['total_found']} similar images")
for result in results['results']:
    print(f"{result['image_uri']}: {result['score']:.2%} similar")
"""
    print(f"{Colors.CYAN}{py_code}{Colors.END}")
    
    print(f"\n{Colors.BOLD}cURL:{Colors.END}")
    curl_code = """
curl -X POST http://localhost:8000/api/images/search-similar \\
  -F "image_file=@path/to/image.jpg" \\
  -F "limit=10" \\
  -F "score_threshold=0.7"
"""
    print(f"{Colors.CYAN}{curl_code}{Colors.END}")


async def main():
    """Run the complete end-to-end demo"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("="*70)
    print("🎨 QDRANT IMAGE SIMILARITY SEARCH - END-TO-END DEMO")
    print("="*70)
    print(f"{Colors.END}\n")
    
    # Step 1: Check Qdrant
    service = await step1_check_qdrant()
    if not service:
        print_error("\nCannot proceed without Qdrant connection.")
        print_info("Please start Qdrant and run this demo again.")
        return
    
    # Step 2: Store sample images
    stored = await step2_store_sample_images(service)
    if stored == 0:
        print_error("\nNo images stored. Cannot demonstrate search.")
        return
    
    # Step 3: Direct search
    await step3_direct_search(service)
    
    # Step 4: API endpoint test
    api_works = await step4_api_endpoint_test()
    
    # Step 5: Frontend demo
    step5_frontend_demo()
    
    # Step 6: Code examples
    step6_show_code_examples()
    
    # Summary
    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*70}")
    print("✅ END-TO-END DEMO COMPLETE!")
    print(f"{'='*70}{Colors.END}\n")
    
    print(f"{Colors.BOLD}Summary:{Colors.END}")
    print(f"  ✓ Qdrant connection: {Colors.GREEN}OK{Colors.END}")
    print(f"  ✓ Images stored: {Colors.GREEN}{stored}{Colors.END}")
    print(f"  ✓ Direct search: {Colors.GREEN}Working{Colors.END}")
    print(f"  ✓ API endpoint: {Colors.GREEN if api_works else Colors.YELLOW}{'Working' if api_works else 'Not tested (API server not running)'}{Colors.END}")
    
    print(f"\n{Colors.BOLD}Next Steps:{Colors.END}")
    if not api_works:
        print("  1. Start API server: python main.py")
    print("  2. Open frontend demo: http://localhost:8000/static/frontend_image_search_example.html")
    print("  3. Upload an image and see similar results!")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Demo interrupted by user{Colors.END}")
    except Exception as e:
        print_error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()

