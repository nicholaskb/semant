# Qdrant Image Similarity Search - Frontend Integration Guide

This guide explains how to use Qdrant image similarity search from the frontend.

## Overview

The system uses Qdrant vector database to store image embeddings and perform fast similarity searches. When you upload an image, it:

1. Generates an embedding using OpenAI's vision API + text embeddings
2. Searches Qdrant for similar images based on visual content
3. Returns results with similarity scores

## API Endpoint

### `POST /api/images/index`

Use this to seed Qdrant with images (embeddings + metadata) before searching.

**Request:**
- **Method:** POST
- **Content-Type:** multipart/form-data
- **Parameters:**
  - `image_file` (file, required): Image to persist
  - `image_type` (string, optional): `input`, `output`, or `reference`
  - `metadata_json` (string, optional): Extra JSON merged into payload
  - `store_in_kg` (bool, optional): `"true"` to write metadata to the KG

**Response:**
```json
{
  "image_uri": "http://example.org/image/123",
  "public_url": "https://storage.googleapis.com/bucket/indexed/123.png",
  "collection": "childrens_book_images",
  "vector_dimension": 1536,
  "metadata": {
    "image_type": "output",
    "gcs_url": "gs://bucket/indexed/123.png"
  }
}
```

### `POST /api/images/search-similar`

**Request:**
- **Method:** POST
- **Content-Type:** multipart/form-data
- **Parameters:**
  - `image_file` (file, required): The image file to search for
  - `limit` (int, optional): Maximum number of results (default: 10)
  - `score_threshold` (float, optional): Minimum similarity score 0-1 (optional)

**Response:**
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
    },
    ...
  ],
  "total_found": 5
}
```

## Frontend Examples

### 1. HTML/JavaScript Example

See `static/frontend_image_search_example.html` for a complete working example with:
- Drag & drop file upload
- Image preview
- Configurable search parameters
- Results display with images and similarity scores

### 2. Vanilla JavaScript

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

### 3. React Example

```jsx
import { useState } from 'react';

function ImageSearch() {
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    
    const handleSearch = async (file) => {
        setLoading(true);
        const formData = new FormData();
        formData.append('image_file', file);
        formData.append('limit', '10');
        
        try {
            const response = await fetch('/api/images/search-similar', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            setResults(data);
        } catch (error) {
            console.error('Error:', error);
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div>
            <input 
                type="file" 
                accept="image/*" 
                onChange={(e) => handleSearch(e.target.files[0])} 
            />
            {loading && <p>Searching...</p>}
            {results && (
                <div>
                    <h3>Found {results.total_found} similar images</h3>
                    {results.results.map((result, i) => (
                        <div key={i}>
                            <img src={result.image_uri} alt="Result" />
                            <p>Similarity: {(result.score * 100).toFixed(1)}%</p>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
```

### 4. Vue.js Example

```vue
<template>
    <div>
        <input type="file" @change="handleFileChange" accept="image/*" />
        <button @click="search" :disabled="loading">Search</button>
        
        <div v-if="loading">Searching...</div>
        <div v-if="results">
            <h3>Found {{ results.total_found }} similar images</h3>
            <div v-for="(result, index) in results.results" :key="index">
                <img :src="result.image_uri" :alt="`Result ${index + 1}`" />
                <p>Similarity: {{ (result.score * 100).toFixed(1) }}%</p>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    data() {
        return {
            selectedFile: null,
            results: null,
            loading: false
        };
    },
    methods: {
        handleFileChange(event) {
            this.selectedFile = event.target.files[0];
        },
        async search() {
            if (!this.selectedFile) return;
            
            this.loading = true;
            const formData = new FormData();
            formData.append('image_file', this.selectedFile);
            formData.append('limit', '10');
            
            try {
                const response = await fetch('/api/images/search-similar', {
                    method: 'POST',
                    body: formData
                });
                this.results = await response.json();
            } catch (error) {
                console.error('Error:', error);
            } finally {
                this.loading = false;
            }
        }
    }
};
</script>
```

## Search Parameters

### `limit`
- **Type:** Integer
- **Default:** 10
- **Description:** Maximum number of results to return
- **Range:** 1-50 (recommended)

### `score_threshold`
- **Type:** Float
- **Default:** None (no threshold)
- **Description:** Minimum similarity score (0.0 to 1.0)
- **Example:** `0.7` returns only images with 70%+ similarity
- **Recommendation:** Start with `0.6` for broader results, increase to `0.8` for very similar matches

## Understanding Similarity Scores

- **1.0** = Identical images
- **0.9-0.99** = Very similar (same subject, similar style)
- **0.8-0.89** = Similar (related content, different angles/styles)
- **0.7-0.79** = Somewhat similar (related subjects)
- **< 0.7** = Less similar (may have some shared elements)

## Error Handling

The API may return these errors:

- **400 Bad Request:** Invalid file or missing parameters
- **503 Service Unavailable:** Qdrant not running or ImageEmbeddingService not initialized
- **500 Internal Server Error:** Processing error

Example error handling:

```javascript
try {
    const results = await searchSimilarImages(file);
} catch (error) {
    if (error.message.includes('503')) {
        console.error('Qdrant service unavailable. Make sure Qdrant is running.');
    } else {
        console.error('Search failed:', error.message);
    }
}
```

## Prerequisites

1. **Qdrant Running:** Ensure Qdrant is running on `localhost:6333` (or configure via `QDRANT_HOST` and `QDRANT_PORT` env vars)
2. **Images Indexed:** Images must be indexed in Qdrant first (see `ImageEmbeddingService.store_embedding()`)
3. **API Running:** The FastAPI server must be running

## Testing

1. Open `static/frontend_image_search_example.html` in your browser
2. Upload an image
3. Adjust search parameters
4. Click "Search Similar Images"

Or use curl:

```bash
curl -X POST http://localhost:8000/api/images/search-similar \
  -F "image_file=@path/to/image.jpg" \
  -F "limit=10" \
  -F "score_threshold=0.7"
```

## Performance Tips

1. **Limit Results:** Use `limit=10` for faster responses
2. **Set Threshold:** Use `score_threshold=0.7` to filter low-quality matches
3. **Image Size:** Smaller images process faster (API resizes automatically)
4. **Caching:** Consider caching results for frequently searched images

## Next Steps

- See `kg/services/image_embedding_service.py` for backend implementation
- See `demo_image_embedding_service.py` for usage examples
- Check `tests/test_image_embedding_service.py` for test cases

