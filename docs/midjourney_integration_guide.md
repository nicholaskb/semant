# Midjourney Integration Guide

## Overview

The Semant platform provides comprehensive integration with Midjourney for AI-powered image generation. This guide covers the architecture, features, API endpoints, and usage examples.

## Table of Contents

1. [Architecture](#architecture)
2. [Features](#features)
3. [Setup & Configuration](#setup--configuration)
4. [API Reference](#api-reference)
5. [Agent Integration](#agent-integration)
6. [Caching System](#caching-system)
7. [Frontend Interface](#frontend-interface)
8. [Examples](#examples)
9. [Troubleshooting](#troubleshooting)

## Architecture

### Component Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Frontend UI   │────▶│  FastAPI Server  │────▶│ Midjourney API  │
│ (midjourney.html)     │   (main.py)       │     │    (GoAPI)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ├── MidjourneyAgent (BaseAgent)
                               ├── PersonaBatchGenerator
                               ├── ImageCache (Redis/File)
                               └── Knowledge Graph (RDF)
```

### Key Components

1. **MidjourneyAgent** (`agents/domain/midjourney_agent.py`)
   - BaseAgent-compatible wrapper for Midjourney services
   - Provides capabilities: IMAGE_GENERATION, IMAGE_DESCRIPTION, IMAGE_BLENDING, etc.
   - Integrates with agent registry for discovery

2. **PersonaBatchGenerator** (`midjourney_integration/persona_batch_generator.py`)
   - Handles batch generation of themed images
   - Rate-limited concurrent processing
   - Version-aware cref/oref handling

3. **ImageCache** (`midjourney_integration/image_cache.py`)
   - Caches generated images to reduce API calls
   - Supports both file-based and Redis caching
   - TTL-based expiration

4. **Frontend UI** (`static/midjourney.html`)
   - Web interface for all Midjourney operations
   - Real-time job tracking
   - Advanced parameter controls

## Features

### Core Capabilities

- **Image Generation**: Text-to-image generation with advanced parameters
- **Image Description**: AI-powered image analysis and description
- **Image Blending**: Combine 2-5 images into new creations
- **Variations**: Create variations of existing images
- **Batch Generation**: Generate themed image sets with persona references
- **Upscaling**: Enhance image resolution
- **Panning/Outpainting**: Extend images in any direction

### Advanced Features

- **Version-aware Processing**: Automatic handling of v6 (cref/cw) vs v7 (oref/ow)
- **Knowledge Graph Integration**: All operations tracked in RDF triples
- **Rate Limiting**: Semaphore-based concurrency control
- **Image Caching**: Reduce redundant API calls
- **GCS Integration**: Automatic upload to Google Cloud Storage
- **Error Recovery**: Comprehensive error handling and retry logic

## Setup & Configuration

### Environment Variables

```bash
# Required
GOAPI_KEY=your_goapi_key_here

# Optional
REDIS_URL=redis://localhost:6379  # For distributed caching
GCS_BUCKET_NAME=your_bucket_name   # For cloud storage
```

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize the system
python main.py
```

## API Reference

### Image Generation

#### POST `/api/midjourney/imagine`

Generate an image from a text prompt.

**Request:**
```json
{
  "prompt": "a beautiful sunset over mountains",
  "aspect_ratio": "16:9",
  "process_mode": "relax",
  "version": "v7"
}
```

**Response:**
```json
{
  "task_id": "abc123",
  "status": "submitted"
}
```

### Image Description

#### POST `/api/midjourney/describe`

Describe an uploaded image using AI.

**Request:**
- Form data with `image_file` upload

**Response:**
```json
{
  "description": "A serene landscape featuring...",
  "prompts": ["sunset landscape", "mountain vista", ...]
}
```

### Image Blending

#### POST `/api/midjourney/blend`

Blend 2-5 images together.

**Request:**
```json
{
  "image_urls": ["url1", "url2", "url3"],
  "dimension": "square"
}
```

**Response:**
```json
{
  "task_id": "xyz789",
  "status": "submitted"
}
```

### Batch Generation

#### POST `/api/persona-batch/generate`

Generate a batch of themed images using persona photos.

**Request:**
```json
{
  "theme": "Lord of the Rings",
  "batch_size": 10,
  "model_version": "v7",
  "persona_urls": ["url1", "url2", "url3", "url4", "url5", "url6"]
}
```

**Response:**
```json
{
  "success": true,
  "batch_id": "batch_abc123_20251031",
  "theme": "Lord of the Rings",
  "total_generated": 10,
  "generated_images": [...],
  "metadata": {...}
}
```

### Job Status

#### GET `/api/midjourney/jobs/{task_id}`

Get the status of a generation task.

**Response:**
```json
{
  "task_id": "abc123",
  "status": "completed",
  "output": {
    "image_url": "https://...",
    "gcs_url": "gs://..."
  }
}
```

## Agent Integration

### Using MidjourneyAgent

```python
from agents.domain.midjourney_agent import MidjourneyAgent
from agents.core.base_agent import AgentMessage

# Initialize agent
agent = MidjourneyAgent(
    agent_id="mj_agent",
    knowledge_graph=kg_manager
)

# Generate image
message = AgentMessage(
    sender_id="user",
    recipient_id="mj_agent",
    content={
        "operation": "generate",
        "prompt": "a futuristic city",
        "version": "v7"
    }
)

response = await agent.process_message(message)
```

### Available Operations

- `generate`: Create image from prompt
- `describe`: Analyze image
- `blend`: Combine images
- `variation`: Create variations
- `batch`: Batch generation
- `upload`: Upload to cloud storage

## Caching System

### Configuration

The caching system automatically caches generated images to reduce API calls.

```python
from midjourney_integration.image_cache import initialize_cache

# Initialize with configuration
cache = await initialize_cache(
    cache_dir=".cache/midjourney",
    ttl_hours=24,
    max_cache_size_mb=500,
    redis_url="redis://localhost:6379"  # Optional
)
```

### Cache Key Generation

Cache keys are generated from:
- Prompt text (normalized)
- Model version
- Aspect ratio
- Process mode
- Reference parameters (cref/oref)

### Cache Management

```python
# Get cache statistics
stats = await cache.get_stats()

# Clear cache
await cache.clear()

# Check specific entry
cached = await cache.get("prompt", version="v7")
```

## Frontend Interface

### Accessing the UI

Navigate to `http://localhost:8000/static/midjourney.html`

### Features

1. **Prompt Input**: Multi-line text area with placeholder support
2. **Image Upload**: Drag-and-drop or click to upload reference images
3. **Advanced Settings**:
   - Character/Style references (cref/sref)
   - Omni references for v7 (oref)
   - Weight controls
   - Aspect ratio selection
   - Exclude parameters

4. **Gallery View**:
   - Real-time job tracking
   - Progress indicators
   - Action buttons (variations, upscale, etc.)
   - Grid/single image display

5. **Specialized Features**:
   - Batch generation with themes
   - Image blending
   - Description generation
   - Trace viewing for debugging

## Examples

### Basic Image Generation

```python
# Using the API directly
import aiohttp

async with aiohttp.ClientSession() as session:
    async with session.post(
        "http://localhost:8000/api/midjourney/imagine",
        data={
            "prompt": "a magical forest with fireflies",
            "aspect_ratio": "16:9",
            "version": "v7"
        }
    ) as response:
        result = await response.json()
        print(f"Task ID: {result['task_id']}")
```

### Persona-Themed Batch

```python
# Generate themed images with personas
async with session.post(
    "http://localhost:8000/api/persona-batch/generate",
    json={
        "theme": "Star Wars universe",
        "batch_size": 5,
        "persona_urls": [
            "url1", "url2", "url3",
            "url4", "url5", "url6"
        ]
    }
) as response:
    batch = await response.json()
    print(f"Generated {batch['total_generated']} images")
```

### Using Knowledge Graph

```python
# Query generated images from KG
query = """
PREFIX ex: <http://example.org/>
SELECT ?prompt ?imageUrl WHERE {
    ?gen ex:prompt ?prompt ;
         ex:imageUrl ?imageUrl .
}
LIMIT 10
"""

results = await kg_manager.query_graph(query)
```

## Troubleshooting

### Common Issues

1. **SSL Certificate Errors**
   - Set `REQUESTS_CA_BUNDLE` environment variable
   - Or use `verify=False` for development (not recommended for production)

2. **Rate Limiting**
   - Adjust `max_concurrent` in PersonaBatchGenerator
   - Use process_mode="relax" for non-urgent tasks

3. **Cache Issues**
   - Clear cache: `await cache.clear()`
   - Check cache stats: `await cache.get_stats()`
   - Verify Redis connection if using distributed cache

4. **Version Conflicts**
   - v6: Use `--cref` and `--cw` parameters
   - v7: Use `--oref` and `--ow` parameters
   - System auto-detects and handles version requirements

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### API Error Codes

- `400`: Invalid parameters
- `401`: Authentication failed (check GOAPI_KEY)
- `429`: Rate limited
- `500`: Internal server error
- `503`: Service unavailable

## Performance Optimization

1. **Use Caching**: Enable Redis for distributed caching
2. **Batch Operations**: Use PersonaBatchGenerator for multiple images
3. **Process Mode**: Use "relax" mode for better queue management
4. **Image Compression**: Optimize uploaded images before processing
5. **Concurrent Limits**: Adjust semaphore limits based on API tier

## Security Considerations

1. **API Keys**: Store securely in environment variables
2. **File Uploads**: Validate file types and sizes
3. **Prompt Injection**: Sanitize user inputs
4. **Rate Limiting**: Implement per-user limits
5. **Access Control**: Use authentication for production

## Support & Resources

- [Midjourney Documentation](https://docs.midjourney.com)
- [GoAPI Documentation](https://goapi.ai/docs)
- [Project Repository](https://github.com/your-repo)
- [Issue Tracker](https://github.com/your-repo/issues)

---

Last Updated: 2025-10-31
