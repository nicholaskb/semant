# Book Framework Optimization - Using image_url

## ✅ Enhancement Complete

### What Was Fixed

**Enhanced `ImageEmbeddingService.search_similar_images()`** to return `image_url` field:
- Extracts `gcs_url` from metadata
- Converts `gs://bucket/path` → `https://storage.googleapis.com/bucket/path`
- Adds `image_url` to all search results
- Falls back to `image_uri` if no `gcs_url` in metadata

### Current State

✅ **Service Method Enhanced**: `search_similar_images()` now returns `image_url`  
✅ **API Endpoint Enhanced**: Already returns `image_url`  
⚠️ **Book Framework**: Can now use `image_url` but may need minor updates

## How Book Framework Can Leverage This

### Option 1: Use image_url from Pairing Agent (Recommended)

The `ImagePairingAgent` calls `search_similar_images()` and gets results with `image_url`. It should:

1. **Store `image_url` in pair data** when available
2. **Return `image_url` in pairing results** 
3. **Book generator uses `image_url` directly** instead of querying KG

**Current Flow:**
```python
# Pairing agent gets search results
similar_images = self.embedding_service.search_similar_images(...)
# Gets: {image_uri: "...", image_url: "https://...", ...}

# But only stores image_uri in pairs
output_uri = output_result["image_uri"]  # ← Only stores URI

# Book generator has to query KG separately
for uri in output_uris:
    query = "SELECT ?url WHERE { <uri> schema:contentUrl ?url }"
    # ← Extra KG query!
```

**Optimized Flow:**
```python
# Pairing agent gets search results (now with image_url)
similar_images = self.embedding_service.search_similar_images(...)
# Gets: {image_uri: "...", image_url: "https://...", ...}

# Store both URI and URL
output_uri = output_result["image_uri"]
output_url = output_result.get("image_url", "")  # ← Use image_url!

# Store in pair data
pair_data = {
    "output_image_uris": [output_uri],
    "output_image_urls": [output_url],  # ← New field!
}

# Book generator uses URLs directly
image_urls = pair.get("output_image_urls", [])  # ← No KG query needed!
```

### Option 2: Create URI→URL Mapping

If modifying pairing agent is complex, create a helper that maps URIs to URLs:

```python
async def _get_image_urls_from_pairs(self, pairs):
    """Extract image URLs from pairing results."""
    uri_to_url = {}
    
    for pair in pairs:
        # Pairing agent should have stored image_urls
        uris = pair.get("output_image_uris", [])
        urls = pair.get("output_image_urls", [])  # ← New field
        
        for uri, url in zip(uris, urls):
            if url and url.startswith("https://"):
                uri_to_url[uri] = url
    
    return uri_to_url
```

## Benefits

### Before:
- ❌ Pairing agent only stores URIs
- ❌ Book generator queries KG separately for each image
- ❌ Multiple SPARQL queries per book generation
- ❌ Slower book generation

### After:
- ✅ Pairing agent can store URLs from search results
- ✅ Book generator uses URLs directly
- ✅ No extra KG queries needed
- ✅ Faster book generation

## Implementation Steps

1. ✅ **Enhanced Service** - `search_similar_images()` returns `image_url`
2. ⚠️ **Update Pairing Agent** - Store `image_url` in pair data (optional but recommended)
3. ⚠️ **Update Book Generator** - Use `image_url` from pairs instead of querying KG

## Recommendation

**Update `ImagePairingAgent`** to:
- Extract `image_url` from search results
- Store `image_url` in pair data structure
- Return `image_urls` alongside `output_image_uris`

This way the book generator can use URLs directly without extra KG queries.

## Files to Update (Optional Optimization)

1. `agents/domain/image_pairing_agent.py` - Store `image_url` in pairs
2. `scripts/generate_childrens_book.py` - Use `image_url` from pairs instead of KG queries

**Note**: The current code still works (it queries KG), but this optimization would make it faster and more efficient.

