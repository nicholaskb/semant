# How to Use the Children's Book Generator 📚

## Quick Start Guide

### Prerequisites

```bash
# 1. Set required environment variables in .env
OPENAI_API_KEY=your_openai_key_here
GCS_BUCKET_NAME=veo-videos-baro-1759717316
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcs-credentials.json

# 2. Start Qdrant (for vector embeddings)
docker run -p 6333:6333 qdrant/qdrant

# 3. Verify you have images in GCS:
# - gs://your-bucket/input_kids_monster/  (input images)
# - gs://your-bucket/generated_images/    (output images)
```

### Generate a Book (3 Ways)

#### Method 1: CLI Tool (Easiest)
```bash
python scripts/generate_childrens_book.py \
  --title="Max's Monster Adventure" \
  --bucket=veo-videos-baro-1759717316 \
  --input-prefix=input_kids_monster/ \
  --output-prefix=generated_images/ \
  --target-age="4-6"
```

**Output Location:**
- HTML file: `childrens_books/maxs_monster_adventure_[timestamp].html`
- PDF file: `childrens_books/maxs_monster_adventure_[timestamp].pdf`
- KG workflow URI: Printed to console

#### Method 2: Python API
```python
import asyncio
from agents.domain.childrens_book_orchestrator import ChildrensBookOrchestrator

async def generate_my_book():
    orchestrator = ChildrensBookOrchestrator()
    
    result = await orchestrator.generate_book(
        bucket="veo-videos-baro-1759717316",
        input_prefix="input_kids_monster/",
        output_prefix="generated_images/",
        title="My Story"
    )
    
    print(f"✅ Book generated!")
    print(f"   HTML: {result['html_file']}")
    print(f"   Workflow URI: {result['workflow_uri']}")
    print(f"   Duration: {result['duration_seconds']:.1f}s")

# Run it
asyncio.run(generate_my_book())
```

#### Method 3: Step-by-Step (Manual Control)
```python
import asyncio
from agents.domain.image_ingestion_agent import ingest_images_from_gcs
from agents.domain.image_pairing_agent import pair_all_images
from agents.domain.story_sequencing_agent import sequence_all_pairs
from agents.domain.spatial_color_agent import arrange_images_by_color
from agents.domain.grid_layout_agent import create_grid_layouts_for_book
from agents.domain.story_writer_agent import write_story_for_book
from agents.domain.page_design_agent import create_page_designs
from agents.domain.design_review_agent import review_all_designs
from agents.domain.book_layout_agent import generate_final_book

async def generate_step_by_step():
    # Step 1: Download & ingest images
    print("Step 1: Ingesting images...")
    ingest_result = await ingest_images_from_gcs()
    print(f"  ✅ Ingested {ingest_result['total_embeddings_generated']} images")
    
    # Step 2: Pair inputs with outputs
    print("Step 2: Pairing images...")
    pair_result = await pair_all_images()
    print(f"  ✅ Created {pair_result['pairs_count']} pairs")
    
    # Step 3: Sequence into story
    print("Step 3: Sequencing story...")
    sequence_result = await sequence_all_pairs()
    print(f"  ✅ Sequenced {sequence_result['total_pages']} pages")
    
    # Step 4: Arrange by color
    print("Step 4: Arranging by color...")
    color_result = await arrange_images_by_color()
    print(f"  ✅ Arranged {color_result['images_arranged']} images")
    
    # Step 5: Create grid layouts
    print("Step 5: Creating grid layouts...")
    grid_result = await create_grid_layouts_for_book()
    print(f"  ✅ Created {grid_result['layouts_created']} grids")
    
    # Step 6: Write story text
    print("Step 6: Writing story...")
    story_result = await write_story_for_book()
    print(f"  ✅ Wrote text for {story_result['pages_written']} pages")
    
    # Step 7: Create page designs
    print("Step 7: Designing pages...")
    design_result = await create_page_designs()
    print(f"  ✅ Designed {design_result['designs_created']} pages")
    
    # Step 8: Review designs
    print("Step 8: Reviewing designs...")
    review_result = await review_all_designs()
    print(f"  ✅ Reviewed {review_result['reviews_created']} designs")
    
    # Step 9: Generate final book
    print("Step 9: Generating final book...")
    book_result = await generate_final_book()
    print(f"  ✅ Book generated: {book_result['html_file']}")
    
    return book_result

# Run it
result = asyncio.run(generate_step_by_step())
```

---

## Accessing the Final Product

### 1. HTML File
```bash
# Location
cd childrens_books/

# Latest book
ls -lt | head -n 5

# Open in browser
open book_[timestamp].html
```

### 2. Query Knowledge Graph
```python
from kg.models.graph_manager import KnowledgeGraphManager
import asyncio

async def query_book():
    kg = KnowledgeGraphManager()
    await kg.initialize()
    
    # Query for complete books
    query = """
    PREFIX schema: <http://schema.org/>
    PREFIX book: <http://example.org/childrens-book#>
    
    SELECT ?book ?url ?created WHERE {
        ?book a schema:Book ;
              schema:contentUrl ?url .
        OPTIONAL { ?book schema:dateCreated ?created . }
    }
    ORDER BY DESC(?created)
    LIMIT 5
    """
    
    results = await kg.query_graph(query)
    
    for r in results:
        print(f"Book URI: {r['book']}")
        print(f"  HTML: {r['url']}")
        print(f"  Created: {r.get('created', 'N/A')}")
        print()
    
    await kg.shutdown()

asyncio.run(query_book())
```

### 3. Query Specific Book Details
```python
async def get_book_pages(book_uri):
    kg = KnowledgeGraphManager()
    await kg.initialize()
    
    # Get all pages for a book
    query = f"""
    PREFIX book: <http://example.org/childrens-book#>
    PREFIX schema: <http://schema.org/>
    
    SELECT ?page ?pageNum ?text ?inputImg ?gridDims WHERE {{
        <{book_uri}> book:hasPages ?pageList .
        ?pageList rdf:rest*/rdf:first ?page .
        ?page book:pageNumber ?pageNum ;
              book:hasStoryText ?text .
        
        OPTIONAL {{
            ?page book:leftColumn ?leftCol .
            ?leftCol book:hasInputImage ?inputImg .
        }}
        
        OPTIONAL {{
            ?page book:rightColumn ?rightCol .
            ?rightCol book:gridDimensions ?gridDims .
        }}
    }}
    ORDER BY ?pageNum
    """
    
    results = await kg.query_graph(query)
    
    print(f"Book: {book_uri}")
    print("=" * 70)
    
    for r in results:
        print(f"\nPage {r['pageNum']}:")
        print(f"  Text: {r['text'][:100]}...")
        print(f"  Input Image: {r.get('inputImg', 'N/A')}")
        print(f"  Grid: {r.get('gridDims', 'N/A')}")
    
    await kg.shutdown()
```

### 4. View Image Pairs
```python
async def view_image_pairs():
    kg = KnowledgeGraphManager()
    await kg.initialize()
    
    query = """
    PREFIX book: <http://example.org/childrens-book#>
    PREFIX schema: <http://schema.org/>
    
    SELECT ?pair ?inputName ?confidence ?needsReview WHERE {
        ?pair a book:ImagePair ;
              book:hasInputImage ?input ;
              book:pairConfidence ?confidence ;
              book:needsReview ?needsReview .
        ?input schema:name ?inputName .
    }
    ORDER BY DESC(?confidence)
    """
    
    results = await kg.query_graph(query)
    
    print("Image Pairs:")
    print("=" * 70)
    
    for r in results:
        status = "⚠️ NEEDS REVIEW" if r['needsReview'] else "✅ APPROVED"
        print(f"{r['inputName']}: confidence={float(r['confidence']):.3f} {status}")
    
    await kg.shutdown()

asyncio.run(view_image_pairs())
```

### 5. View Grid Layouts
```python
async def view_grid_layouts():
    kg = KnowledgeGraphManager()
    await kg.initialize()
    
    query = """
    PREFIX book: <http://example.org/childrens-book#>
    
    SELECT ?layout ?gridDims ?harmonyScore ?balanceScore ?rationale WHERE {
        ?layout a book:GridLayout ;
                book:gridDimensions ?gridDims ;
                book:colorHarmonyScore ?harmonyScore ;
                book:visualBalanceScore ?balanceScore .
        OPTIONAL { ?layout book:layoutRationale ?rationale . }
    }
    ORDER BY ?layout
    """
    
    results = await kg.query_graph(query)
    
    print("Grid Layouts:")
    print("=" * 70)
    
    for r in results:
        print(f"\nGrid: {r['gridDims']}")
        print(f"  Color Harmony: {float(r['harmonyScore']):.3f}")
        print(f"  Visual Balance: {float(r['balanceScore']):.3f}")
        print(f"  Rationale: {r.get('rationale', 'N/A')}")
    
    await kg.shutdown()

asyncio.run(view_grid_layouts())
```

---

## Output Structure

### Generated Files
```
childrens_books/
├── book_abc12345.html     ← Main HTML book
├── book_abc12345.pdf      ← PDF version (if generated)
└── book_abc12345_meta.json ← Metadata
```

### HTML Structure
```html
<!DOCTYPE html>
<html>
<head>
  <title>Your Book Title</title>
  <style>
    .book-page { display: flex; ... }
    .left-column { ... }          /* Input image + text */
    .right-column { ... }         /* Output image grid */
    .image-grid { ... }
    .grid-3x3 { grid-template-columns: repeat(3, 1fr); }
    .grid-3x4 { grid-template-columns: repeat(4, 1fr); }
  </style>
</head>
<body>
  <div class="book-page">
    <div class="left-column">
      <img src="[GCS URL]" class="input-image"/>
      <div class="story-text">Once upon a time...</div>
    </div>
    <div class="right-column">
      <div class="image-grid grid-3x3">
        <img src="[output_1]"/>
        <img src="[output_2]"/>
        <!-- ... 9 images in 3x3 grid -->
      </div>
    </div>
  </div>
  <!-- More pages... -->
</body>
</html>
```

---

## Querying the Knowledge Graph

### Find All Books
```sparql
PREFIX schema: <http://schema.org/>
PREFIX book: <http://example.org/childrens-book#>

SELECT ?book ?url ?created WHERE {
    ?book a schema:Book ;
          schema:contentUrl ?url .
    OPTIONAL { ?book schema:dateCreated ?created . }
}
ORDER BY DESC(?created)
```

### Find Image Pairs with Low Confidence
```sparql
PREFIX book: <http://example.org/childrens-book#>

SELECT ?pair ?confidence WHERE {
    ?pair a book:ImagePair ;
          book:pairConfidence ?confidence ;
          book:needsReview true .
}
ORDER BY ?confidence
```

### Find Grid Layouts (Check Anti-Lazy Rules)
```sparql
PREFIX book: <http://example.org/childrens-book#>

SELECT ?layout ?dims ?harmony ?balance ?rationale WHERE {
    ?layout a book:GridLayout ;
            book:gridDimensions ?dims ;
            book:colorHarmonyScore ?harmony ;
            book:visualBalanceScore ?balance ;
            book:layoutRationale ?rationale .
}
```

---

## Workflow Results Location

After running the generator, you can find:

### 1. **HTML Book**
```bash
# Location
ls -lt childrens_books/*.html | head -1

# Open in browser
open childrens_books/book_*.html
```

### 2. **KG Workflow URI**
Printed to console at the end:
```
✅ Book generated successfully!
  Workflow URI: http://example.org/workflow/abc-123-def-456
  HTML file: childrens_books/book_abc12345.html
  Duration: 45.2s
```

### 3. **Query All Workflow Data**
```python
async def get_workflow_details(workflow_uri):
    kg = KnowledgeGraphManager()
    await kg.initialize()
    
    query = f"""
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX book: <http://example.org/childrens-book#>
    
    SELECT ?start ?end ?status ?bookGenerated WHERE {{
        <{workflow_uri}> prov:startedAtTime ?start ;
                         prov:endedAtTime ?end ;
                         book:workflowStatus ?status .
        OPTIONAL {{ <{workflow_uri}> prov:generated ?bookGenerated . }}
    }}
    """
    
    results = await kg.query_graph(query)
    
    if results:
        r = results[0]
        print(f"Workflow: {workflow_uri}")
        print(f"  Started: {r['start']}")
        print(f"  Ended: {r['end']}")
        print(f"  Status: {r['status']}")
        print(f"  Book: {r.get('bookGenerated', 'N/A')}")
    
    await kg.shutdown()
```

---

## Example Usage Session

```bash
# Terminal 1: Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Terminal 2: Generate book
cd /Users/nicholasbaro/Python/semant

# Generate
python scripts/generate_childrens_book.py \
  --title="Max's Monster Adventure"

# Output:
# ═══════════════════════════════════════════════════════════
#    Children's Book Generator
# ═══════════════════════════════════════════════════════════
# 
#   Bucket: veo-videos-baro-1759717316
#   Input prefix: input_kids_monster/
#   Output prefix: generated_images/
#   Title: Max's Monster Adventure
# 
# [cyan]Generating book... ████████████████████ 100%
# 
# ✅ Book generated successfully!
# 
#   HTML file: childrens_books/maxs_monster_adventure.html
#   Workflow URI: http://example.org/workflow/abc-123
#   Duration: 42.3s

# Open the book
open childrens_books/maxs_monster_adventure.html
```

---

## What You'll See in the HTML

Each page will have:

### Left Column:
- **Input Image:** Original drawing/photo from `input_kids_monster/`
- **Story Text:** Age-appropriate narrative (50-100 words)
- **Styling:** Comic Sans MS, 18pt, child-friendly

### Right Column:
- **Output Grid:** 3x3 or 3x4 grid of generated/processed images
- **Color Arranged:** Images grouped by color harmony
- **Optimized Layout:** Visually balanced arrangement

### Example Page:
```
┌─────────────────────────────────────────────────────────────┐
│  LEFT COLUMN          │  RIGHT COLUMN                       │
│                       │                                     │
│  [Input Image]        │  ┌─────┬─────┬─────┬─────┐        │
│   Kid's drawing       │  │ Out │ Out │ Out │ Out │        │
│                       │  │  1  │  2  │  3  │  4  │        │
│                       │  ├─────┼─────┼─────┼─────┤        │
│  Story Text:          │  │ Out │ Out │ Out │ Out │  3x4   │
│  "Once upon a time    │  │  5  │  6  │  7  │  8  │  grid  │
│   there was a little  │  ├─────┼─────┼─────┼─────┤        │
│   monster named Max.  │  │ Out │ Out │ Out │ Out │        │
│   Max loved to play   │  │  9  │ 10  │ 11  │ 12  │        │
│   in the colorful     │  └─────┴─────┴─────┴─────┘        │
│   garden..."          │                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Error: "No input images found"
```bash
# Check GCS bucket
gsutil ls gs://veo-videos-baro-1759717316/input_kids_monster/

# Should see:
# gs://.../input_kids_monster/input_001.png
# gs://.../input_kids_monster/input_002.png
# ...
```

### Error: "Connection refused" (Qdrant)
```bash
# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Verify running
curl http://localhost:6333/healthz
```

### Error: "OPENAI_API_KEY not set"
```bash
# Add to .env file
echo "OPENAI_API_KEY=sk-your-key-here" >> .env

# Or export directly
export OPENAI_API_KEY=sk-your-key-here
```

---

## Expected Output Timeline

For a typical book (5 input images, 20 output images):

| Step | Task | Time | Output |
|------|------|------|--------|
| 1 | Download & Ingest | ~2 min | 25 images in KG + embeddings |
| 2 | Pair Images | ~30 sec | 5 image pairs |
| 3 | Sequence Story | ~45 sec | Story order determined |
| 4 | Arrange Colors | ~30 sec | Spatial positions |
| 5 | Create Grids | ~15 sec | 3x3 or 3x4 layouts |
| 6 | Write Story | ~2 min | 5 pages of text |
| 7 | Design Pages | ~30 sec | Complete designs |
| 8 | Review Designs | ~15 sec | Quality checks |
| 9 | Generate Book | ~10 sec | HTML + PDF |

**Total: ~7-8 minutes**

---

## FINAL PRODUCT: What You Get

✅ **HTML File:** Print-ready, responsive children's book  
✅ **PDF File:** High-quality PDF for distribution  
✅ **Knowledge Graph:** Complete provenance of every decision  
✅ **SPARQL Queryable:** All images, pairs, layouts, text stored  
✅ **Embeddings Indexed:** Fast similarity search in Qdrant  
✅ **Grid Layouts:** 3x3 or 3x4 (anti-lazy rules enforced)  
✅ **Color Arranged:** Images grouped by visual harmony  
✅ **Story Text:** Age-appropriate narrative for each page  

🎉 **Your children's book is ready to share!**

