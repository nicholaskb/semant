# Qdrant Image Search - Quick Start Guide

## 🚀 Quick Start (3 Steps)

### 1. Start Qdrant

```bash
# Using docker-compose (recommended)
docker-compose up -d qdrant

# Or using docker directly
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest

# Verify it's running
curl http://localhost:6333/health
```

### 2. Store Images in Qdrant (One-time setup)

```python
from kg.services.image_embedding_service import ImageEmbeddingService
from pathlib import Path
import asyncio

async def store_image(image_path: str, image_uri: str):
    service = ImageEmbeddingService()
    embedding, description = await service.embed_image(Path(image_path))
    service.store_embedding(
        image_uri=image_uri,
        embedding=embedding,
        metadata={"description": description}
    )
    print(f"✅ Stored: {image_uri}")

# Store your images
asyncio.run(store_image("image1.jpg", "http://example.org/image1.jpg"))
```

### 3. Search for Similar Images

**Option A: Using the script**
```bash
python find_similar_images.py your_image.jpg 10
```

**Option B: Using Python**
```python
from kg.services.image_embedding_service import ImageEmbeddingService
from pathlib import Path
import asyncio

async def search():
    service = ImageEmbeddingService()
    embedding, _ = await service.embed_image(Path("query.jpg"))
    results = service.search_similar_images(embedding, limit=10)
    for r in results:
        print(f"{r['image_uri']}: {r['score']:.3f}")

asyncio.run(search())
```

**Option C: Using the API**
```bash
curl -X POST http://localhost:8000/api/images/search-similar \
  -F "image_file=@image.jpg" \
  -F "limit=10"
```

## 📚 Full Documentation

See `docs/qdrant_image_search_walkthrough.md` for complete details.

