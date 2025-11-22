# Qdrant Image Similarity Search - Complete Walkthrough

This guide walks you through using Qdrant on the server to find similar images.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Starting Qdrant](#starting-qdrant)
3. [Method 1: Using ImageEmbeddingService (Python)](#method-1-using-imageembeddingservice-python)
4. [Method 2: Using the API Endpoint](#method-2-using-the-api-endpoint)
5. [Complete Example Script](#complete-example-script)
6. [Understanding Results](#understanding-results)

---

## Prerequisites

1. **Qdrant Running**: Qdrant should be running on `localhost:6333`
2. **Python Dependencies**: 
   ```bash
   pip install qdrant-client openai pillow
   ```
3. **OpenAI API Key**: Set in your `.env` file as `OPENAI_API_KEY`
4. **Images Indexed**: Images need to be stored in Qdrant first (see "Storing Images" section)

---

## Starting Qdrant

### Option 1: Using Docker Compose (Recommended)

```bash
# Start Qdrant (and other services)
docker-compose up -d qdrant

# Check if it's running
docker ps | grep qdrant

# Verify Qdrant is accessible
curl http://localhost:6333/health
```

### Option 2: Using Docker Directly

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest
```

### Verify Qdrant is Running

```bash
# Check health
curl http://localhost:6333/health

# Should return: {"status":"ok"}
```

---

## Method 0: Indexing Images via the API (Quickest)

Before running searches you need vectors stored in Qdrant. You can now do this
directly from the API without writing a separate ingestion script.

### Endpoint

**POST** `/api/images/index`

### Required form fields

- `image_file` (file): Image to store

### Optional form fields

- `image_type`: `input`, `output`, or `reference` (default: `output`)
- `source_uri`: Custom URI to associate with the image (default auto-generated)
- `description_override`: Provide your own description instead of GPT-4o
- `metadata_json`: JSON object string merged into the stored payload
- `store_in_kg`: `"true"` to also write metadata into the Knowledge Graph
- `verify_public`: `"true"` to wait until the GCS URL is publicly accessible

### Example cURL

```bash
curl -X POST http://localhost:8000/api/images/index \
  -F "image_file=@examples/images/sample_duck.png" \
  -F "image_type=output" \
  -F "store_in_kg=true"
```

### Response

```json
{
  "image_uri": "http://example.org/image/1c8d1e68-7d6c-4d0b-b10d-0f5be73a4e73",
  "description": "A watercolor illustration of ...",
  "gcs_url": "gs://your-bucket/indexed/1c8d1e68-7d6c-4d0b-b10d-0f5be73a4e73.png",
  "public_url": "https://storage.googleapis.com/your-bucket/indexed/1c8d1e68-7d6c-4d0b-b10d-0f5be73a4e73.png",
  "collection": "childrens_book_images",
  "vector_dimension": 1536,
  "metadata": {
    "filename": "sample_duck.png",
    "image_type": "output",
    "description": "...",
    "gcs_url": "gs://...",
    "public_url": "https://..."
  }
}
```

You can immediately search for the indexed image using the methods below.

---

## Method 1: Using ImageEmbeddingService (Python)

This is the programmatic approach - use this when building Python scripts or integrating into your code.

### Step 1: Initialize the Service

```python
from kg.services.image_embedding_service import ImageEmbeddingService
from pathlib import Path

# Initialize service (connects to Qdrant automatically)
service = ImageEmbeddingService(
    qdrant_host="localhost",
    qdrant_port=6333,
    collection_name="childrens_book_images"  # Default collection name
)
```

### Step 2: Generate Embedding for Query Image

```python
import asyncio

async def search_similar(query_image_path: str):
    # Generate embedding for your query image
    query_embedding, description = await service.embed_image(
        Path(query_image_path)
    )
    
    print(f"Image description: {description}")
    print(f"Embedding dimensions: {len(query_embedding)}")
```

### Step 3: Search for Similar Images

```python
    # Search Qdrant for similar images
    results = service.search_similar_images(
        query_embedding=query_embedding,
        limit=10,                    # Top 10 results
        score_threshold=0.7,         # Minimum similarity (0-1)
        filter_metadata=None         # Optional: filter by metadata
    )
    
    # Process results
    for result in results:
        print(f"Image URI: {result['image_uri']}")
        print(f"Similarity Score: {result['score']:.3f}")
        print(f"Metadata: {result['metadata']}")
        print("---")
```

### Complete Python Example

```python
import asyncio
from pathlib import Path
from kg.services.image_embedding_service import ImageEmbeddingService

async def find_similar_images(query_image_path: str, top_k: int = 10):
    """
    Find similar images using Qdrant.
    
    Args:
        query_image_path: Path to the image you want to find similar images for
        top_k: Number of results to return
    """
    # Initialize service
    service = ImageEmbeddingService()
    
    # Generate embedding for query image
    print(f"Processing query image: {query_image_path}")
    query_embedding, description = await service.embed_image(
        Path(query_image_path)
    )
    print(f"Description: {description}\n")
    
    # Search for similar images
    print(f"Searching for top {top_k} similar images...")
    results = service.search_similar_images(
        query_embedding=query_embedding,
        limit=top_k,
        score_threshold=0.6  # Only return images with 60%+ similarity
    )
    
    # Display results
    print(f"\nFound {len(results)} similar images:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['image_uri']}")
        print(f"   Similarity: {result['score']:.3f} ({result['score']*100:.1f}%)")
        if result['metadata']:
            print(f"   Metadata: {result['metadata']}")
        print()
    
    return results

# Run it
if __name__ == "__main__":
    results = asyncio.run(find_similar_images(
        query_image_path="path/to/your/image.jpg",
        top_k=10
    ))
```

---

## Method 2: Using the API Endpoint

Use this when calling from frontend, curl, or other HTTP clients.

### API Endpoint

**POST** `/api/images/search-similar`

### Request Format

- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `image_file` (file, required): The image file to search for
  - `limit` (int, optional): Maximum number of results (default: 10)
  - `score_threshold` (float, optional): Minimum similarity score 0-1

### Response Format

```json
{
  "query_image": "A yellow duckling with orange feet by a pond",
  "results": [
    {
      "image_uri": "http://example.org/book/output_001_a.png",
      "score": 0.95,
      "metadata": {
        "description": "A yellow duck with orange feet in watercolor style",
        "type": "output"
      }
    }
  ],
  "total_found": 5
}
```

### Example: Using curl

```bash
curl -X POST http://localhost:8000/api/images/search-similar \
  -F "image_file=@path/to/your/image.jpg" \
  -F "limit=10" \
  -F "score_threshold=0.7"
```

### Example: Using Python requests

```python
import requests

def search_similar_via_api(image_path: str, limit: int = 10):
    url = "http://localhost:8000/api/images/search-similar"
    
    with open(image_path, 'rb') as f:
        files = {'image_file': f}
        data = {
            'limit': limit,
            'score_threshold': 0.7
        }
        
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        
        return response.json()

# Usage
results = search_similar_via_api("path/to/image.jpg", limit=10)
print(f"Found {results['total_found']} similar images")
for result in results['results']:
    print(f"- {result['image_uri']}: {result['score']:.3f}")
```

### Example: Using JavaScript/Fetch

```javascript
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
```

---

## Complete Example Script

Here's a complete, ready-to-use script:

```python
#!/usr/bin/env python3
"""
Complete example: Find similar images using Qdrant
"""

import asyncio
import sys
from pathlib import Path
from kg.services.image_embedding_service import ImageEmbeddingService

async def main():
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python find_similar_images.py <query_image_path> [top_k]")
        print("Example: python find_similar_images.py image.jpg 10")
        sys.exit(1)
    
    query_image_path = Path(sys.argv[1])
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    if not query_image_path.exists():
        print(f"Error: Image not found: {query_image_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("Qdrant Image Similarity Search")
    print("=" * 60)
    print(f"Query Image: {query_image_path}")
    print(f"Top K: {top_k}\n")
    
    try:
        # Initialize service
        print("1. Connecting to Qdrant...")
        service = ImageEmbeddingService()
        print("   ✓ Connected\n")
        
        # Generate embedding
        print("2. Generating embedding for query image...")
        query_embedding, description = await service.embed_image(query_image_path)
        print(f"   ✓ Generated embedding ({len(query_embedding)} dimensions)")
        print(f"   Description: {description[:100]}...\n")
        
        # Search
        print(f"3. Searching for top {top_k} similar images...")
        results = service.search_similar_images(
            query_embedding=query_embedding,
            limit=top_k,
            score_threshold=0.6
        )
        print(f"   ✓ Found {len(results)} results\n")
        
        # Display results
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)
        
        if not results:
            print("No similar images found (try lowering score_threshold)")
        else:
            for i, result in enumerate(results, 1):
                score = result['score']
                score_bar = "█" * int(score * 20)
                
                print(f"\n{i}. {result['image_uri']}")
                print(f"   Similarity: {score:.3f} ({score*100:.1f}%)")
                print(f"   [{score_bar}]")
                
                if result.get('metadata'):
                    print(f"   Metadata: {result['metadata']}")
        
        print("\n" + "=" * 60)
        print("Search complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

**Save this as `find_similar_images.py` and run:**

```bash
python find_similar_images.py path/to/image.jpg 10
```

---

## Storing Images in Qdrant First

Before you can search, images need to be stored in Qdrant. Here's how:

```python
from kg.services.image_embedding_service import ImageEmbeddingService
from pathlib import Path
import asyncio

async def store_image(image_path: str, image_uri: str, metadata: dict = None):
    """
    Store an image embedding in Qdrant.
    
    Args:
        image_path: Local path to the image file
        image_uri: Unique URI/identifier for this image (e.g., "http://example.org/image1.png")
        metadata: Optional metadata dict (e.g., {"type": "output", "book_id": "123"})
    """
    service = ImageEmbeddingService()
    
    # Generate embedding
    embedding, description = await service.embed_image(Path(image_path))
    
    # Store in Qdrant
    service.store_embedding(
        image_uri=image_uri,
        embedding=embedding,
        metadata={
            "description": description,
            **(metadata or {})
        }
    )
    
    print(f"Stored: {image_uri}")

# Example: Store multiple images
async def store_multiple_images():
    images = [
        ("/path/to/image1.jpg", "http://example.org/image1.jpg", {"type": "input"}),
        ("/path/to/image2.jpg", "http://example.org/image2.jpg", {"type": "output"}),
    ]
    
    for image_path, image_uri, metadata in images:
        await store_image(image_path, image_uri, metadata)

if __name__ == "__main__":
    asyncio.run(store_multiple_images())
```

---

## Understanding Results

### Similarity Scores

- **1.0** = Identical images
- **0.9-0.99** = Very similar (same subject, similar style)
- **0.8-0.89** = Similar (related content, different angles/styles)
- **0.7-0.79** = Somewhat similar (related subjects)
- **< 0.7** = Less similar (may have some shared elements)

### Filtering Results

You can filter by metadata:

```python
results = service.search_similar_images(
    query_embedding=query_embedding,
    limit=10,
    filter_metadata={"type": "output"}  # Only return "output" type images
)
```

### Performance Tips

1. **Set score_threshold**: Use `score_threshold=0.7` to filter low-quality matches
2. **Limit results**: Use `limit=10` for faster responses
3. **Batch operations**: Store multiple images in a batch for efficiency
4. **Cache embeddings**: Reuse embeddings when searching the same image multiple times

---

## Troubleshooting

### Qdrant Connection Error

```python
# Check if Qdrant is running
import requests
response = requests.get("http://localhost:6333/health")
print(response.json())  # Should be {"status":"ok"}
```

### No Results Found

- Check if images are stored in Qdrant first
- Lower `score_threshold` (try 0.5 instead of 0.7)
- Verify collection name matches: `childrens_book_images`

### API Not Available

Make sure your FastAPI server is running:

```bash
python main.py
# or
uvicorn main:app --reload
```

---

## Next Steps

- See `demo_embedding_pairing.py` for a visual demo
- Check `static/frontend_image_search_example.html` for frontend integration
- Review `kg/services/image_embedding_service.py` for full API documentation

