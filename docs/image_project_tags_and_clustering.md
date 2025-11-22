# Image Project Tags and Clustering

**Date:** 2025-01-17  
**Status:** ✅ IMPLEMENTED  
**Version:** 1.0

## Overview

This document describes the implementation of project tags and similarity-based clustering for images stored in the Knowledge Graph. These features enable:

1. **Project Tagging**: Tag images with project identifiers for filtering and organization
2. **Similarity Clustering**: Group similar images together using embedding-based clustering

---

## Project Tags

### What Are Project Tags?

Project tags allow you to associate images with specific projects or workflows. When images are ingested, they can be tagged with a `project_id`, which creates a relationship in the Knowledge Graph:

```turtle
@prefix kg: <http://example.org/kg#> .
@prefix project: <http://example.org/project/> .

# Image tagged with project
<http://example.org/image/uuid-123>
    a schema:ImageObject ;
    schema:name "image.png" ;
    kg:relatedToProject project:book_20250117_120000 .

# Project node
project:book_20250117_120000
    a project:Project .
```

### Usage

#### 1. Tag Images During Ingestion

**Via ImageIngestionAgent:**

```python
from agents.domain.image_ingestion_agent import ImageIngestionAgent
from agents.core.message_types import AgentMessage

agent = ImageIngestionAgent()

message = AgentMessage(
    sender_id="user",
    recipient_id="image_ingestion_agent",
    content={
        "action": "ingest_images",
        "input_prefix": "book_illustrations/",
        "output_prefix": "midjourney/",
        "project_id": "book_20250117_120000",  # Tag all images with this project
        "extensions": ["png", "jpg", "jpeg"],
        "overwrite": False,
    },
    message_type="request"
)

response = await agent.process_message(message)
```

**Via ChildrensBookOrchestrator:**

```python
from semant.workflows.childrens_book.orchestrator import ChildrensBookOrchestrator

orchestrator = ChildrensBookOrchestrator(
    bucket_name="my-bucket",
    input_prefix="book_illustrations/",
    output_prefix="midjourney/",
    project_id="book_20250117_120000",  # All ingested images will be tagged
    kg_manager=kg_manager
)

result = await orchestrator.generate_book()
```

#### 2. Query Images by Project

```python
from agents.domain.image_ingestion_agent import ImageIngestionAgent

agent = ImageIngestionAgent()

# Get all images for a specific project
images = await agent.get_ingested_images(project_id="book_20250117_120000")

# Get only input images for a project
input_images = await agent.get_ingested_images(
    image_type="input",
    project_id="book_20250117_120000"
)

# Get all images (no project filter)
all_images = await agent.get_ingested_images()
```

#### 3. SPARQL Query Example

```sparql
PREFIX schema: <http://schema.org/>
PREFIX kg: <http://example.org/kg#>
PREFIX project: <http://example.org/project/>

SELECT ?image ?name ?url WHERE {
    ?image a schema:ImageObject ;
           schema:name ?name ;
           schema:contentUrl ?url ;
           kg:relatedToProject project:book_20250117_120000 .
}
```

### Implementation Details

- **Property**: `kg:relatedToProject` (object property linking image to project)
- **Project URI Format**: `http://example.org/project/{project_id}`
- **Project Type**: `project:Project` (automatically created if not exists)
- **Storage**: Stored in Knowledge Graph as RDF triples
- **Persistence**: Persists across runs (KG uses persistent storage)

---

## Similarity Clustering

### What Is Clustering?

Clustering groups similar images together based on their embedding vectors. Images with cosine similarity >= `min_similarity` are grouped into clusters. This is useful for:

- Finding duplicate or near-duplicate images
- Organizing images by visual theme
- Discovering image groups for batch processing

### Algorithm

The implementation uses **DBSCAN** (Density-Based Spatial Clustering of Applications with Noise):

- **Distance Metric**: Cosine distance (derived from cosine similarity)
- **Parameters**:
  - `min_similarity`: Minimum cosine similarity (0.0-1.0) for images to be in same cluster
  - `min_cluster_size`: Minimum number of images required to form a cluster
- **Output**: 
  - Clusters: Lists of image URIs grouped by similarity
  - Noise: Image URIs that don't belong to any cluster (outliers)

### Usage

#### 1. Cluster Images

```python
from kg.services.image_embedding_service import ImageEmbeddingService
from kg.models.graph_manager import KnowledgeGraphManager

embedding_service = ImageEmbeddingService()
kg_manager = KnowledgeGraphManager(persistent_storage=True)

# List of image URIs to cluster
image_uris = [
    "http://example.org/image/uuid-1",
    "http://example.org/image/uuid-2",
    "http://example.org/image/uuid-3",
    # ... more URIs
]

# Cluster images with min_similarity=0.7, min_cluster_size=2
result = await embedding_service.cluster_images_by_similarity(
    image_uris=image_uris,
    min_similarity=0.7,      # Images must be 70% similar to cluster
    min_cluster_size=2,      # At least 2 images per cluster
    kg_manager=kg_manager    # Optional: store clusters in KG
)

# Result structure:
# {
#     "clusters": [
#         ["http://example.org/image/uuid-1", "http://example.org/image/uuid-2"],
#         ["http://example.org/image/uuid-3", "http://example.org/image/uuid-4"]
#     ],
#     "noise": ["http://example.org/image/uuid-5"],  # Outliers
#     "cluster_uris": [
#         "http://example.org/cluster/cluster_abc123",
#         "http://example.org/cluster/cluster_def456"
#     ]
# }
```

#### 2. Query Clusters from KG

If `kg_manager` is provided, clusters are stored in the Knowledge Graph:

```turtle
@prefix kg: <http://example.org/kg#> .
@prefix cluster: <http://example.org/cluster#> .

# Cluster node
cluster:cluster_abc123
    a cluster:ImageCluster ;
    kg:clusterSize "2" ;
    kg:minSimilarity "0.7" ;
    kg:hasMember <http://example.org/image/uuid-1> ;
    kg:hasMember <http://example.org/image/uuid-2> .

# Image linked to cluster
<http://example.org/image/uuid-1>
    kg:belongsToCluster cluster:cluster_abc123 .
```

**SPARQL Query:**

```sparql
PREFIX kg: <http://example.org/kg#>
PREFIX cluster: <http://example.org/cluster#>

# Get all clusters
SELECT ?cluster ?size WHERE {
    ?cluster a cluster:ImageCluster ;
             kg:clusterSize ?size .
}

# Get images in a specific cluster
SELECT ?image WHERE {
    cluster:cluster_abc123 kg:hasMember ?image .
}

# Get cluster for a specific image
SELECT ?cluster WHERE {
    <http://example.org/image/uuid-1> kg:belongsToCluster ?cluster .
}
```

### Implementation Details

- **Function**: `ImageEmbeddingService.cluster_images_by_similarity()` (async)
- **Algorithm**: DBSCAN (via scikit-learn)
- **Embeddings**: Retrieved from Qdrant (not stored in KG)
- **Cluster Storage**: Optional - stored in KG if `kg_manager` provided
- **Properties**:
  - `kg:belongsToCluster`: Links image to cluster
  - `kg:hasMember`: Links cluster to image
  - `kg:clusterSize`: Number of images in cluster
  - `kg:minSimilarity`: Minimum similarity threshold used

### Dependencies

Clustering requires `scikit-learn`:

```bash
pip install scikit-learn
```

If not available, clustering features are disabled with a warning.

---

## Combined Usage Example

```python
from agents.domain.image_ingestion_agent import ImageIngestionAgent
from kg.services.image_embedding_service import ImageEmbeddingService
from kg.models.graph_manager import KnowledgeGraphManager

# Initialize
kg_manager = KnowledgeGraphManager(persistent_storage=True)
ingestion_agent = ImageIngestionAgent(kg_manager=kg_manager)
embedding_service = ImageEmbeddingService()

# 1. Ingest images with project tag
project_id = "book_20250117_120000"
message = AgentMessage(
    sender_id="user",
    recipient_id="image_ingestion_agent",
    content={
        "action": "ingest_images",
        "input_prefix": "book_illustrations/",
        "output_prefix": "midjourney/",
        "project_id": project_id,
        "extensions": ["png", "jpg", "jpeg"],
    },
    message_type="request"
)
response = await ingestion_agent.process_message(message)

# 2. Get all images for this project
images = await ingestion_agent.get_ingested_images(project_id=project_id)
image_uris = [img["uri"] for img in images]

# 3. Cluster images by similarity
clustering_result = await embedding_service.cluster_images_by_similarity(
    image_uris=image_uris,
    min_similarity=0.7,
    min_cluster_size=2,
    kg_manager=kg_manager
)

print(f"Found {len(clustering_result['clusters'])} clusters")
print(f"{len(clustering_result['noise'])} images are outliers")
```

---

## Benefits

1. **Organization**: Filter images by project for workflow management
2. **Discovery**: Find similar images automatically
3. **Deduplication**: Identify duplicate or near-duplicate images
4. **Batch Processing**: Process clusters of similar images together
5. **Knowledge Graph Integration**: All relationships stored in KG for querying

---

## Notes

- **Persistence**: Both project tags and clusters persist in the Knowledge Graph
- **Performance**: Clustering uses Qdrant for fast embedding retrieval
- **Scalability**: DBSCAN handles large datasets efficiently
- **Optional**: Both features are optional - images work without project tags or clusters

---

## Future Enhancements

- [ ] Hierarchical clustering (nested clusters)
- [ ] Project-based clustering (cluster only images within a project)
- [ ] Cluster visualization tools
- [ ] Automatic cluster naming based on image descriptions
- [ ] Cluster quality metrics (cohesion, separation)

