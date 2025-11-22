# Children's Book Agentic Swarm - System Architecture

**Date:** 2025-01-08  
**Status:** Implementation In Progress  
**Version:** 1.0  

## Overview

An agentic swarm system that creates children's books by:
1. Downloading input/output image pairs from GCS
2. Pairing input images to output images using embeddings
3. Arranging images into a narrative sequence
4. Organizing output images by color in spatial grids (3x3, 3x4)
5. Writing age-appropriate story text
6. Designing complete pages with input image + text + output grid
7. Generating final HTML/PDF book

## System Components

### Phase 1: Data Ingestion & Analysis

#### 1. Image Download & Ingestion Agent
**File:** `agents/domain/image_ingestion_agent.py`  
**Extends:** User's GCS download script  
**Dependencies:** GCS client, KG Manager, ImageEmbeddingService  

**Responsibilities:**
- Download images from GCS buckets (input_kids_monster/, generated_images/)
- Generate embeddings for each image using ImageEmbeddingService
- Store images in KG as `schema:ImageObject` with properties:
  - `schema:contentUrl` (GCS URL)
  - `kg:hasEmbedding` (1536-dim vector)
  - `kg:imageType` ("input" or "output")
  - `schema:name` (filename)
  - `dc:created` (timestamp)
- Store embeddings in Qdrant for fast similarity search

**Existing Code Reused:**
- ✅ `ImageEmbeddingService` (already implemented)
- ✅ `KnowledgeGraphManager` (graph operations)
- ✅ User's GCS download script pattern

---

#### 2. Image Pairing Agent
**File:** `agents/domain/image_pairing_agent.py`  
**Extends:** `BaseAgent`  
**Dependencies:** ImageEmbeddingService, KG Manager  

**Responsibilities:**
- Match each input image to its related output images
- Scoring algorithm (weighted):
  - Embedding similarity: 60%
  - Filename pattern matching: 20%
  - Metadata correlation: 20%
- Create `book:ImagePair` nodes in KG:
  ```turtle
  <pair:uuid> a book:ImagePair ;
    book:hasInputImage <image:input_001.png> ;
    book:hasOutputImages (<image:output_001_a.png> <image:output_001_b.png> ...) ;
    book:pairConfidence 0.95 ;
    book:pairingMethod "embedding+filename" .
  ```
- Flag pairs with confidence < 0.7 for human review

**Existing Code Reused:**
- ✅ `ImageEmbeddingService.search_similar_images()`
- ✅ `ImageAnalysisAgent` patterns

---

### Phase 2: Story Construction

#### 3. Story Sequencing Agent
**File:** `agents/domain/story_sequencing_agent.py`  
**Extends:** `BaseAgent`  
**Dependencies:** GPT-4o, Image Analysis Agent, KG Manager  

**Responsibilities:**
- Analyze all input images for narrative potential
- Research children's book narrative structure
- Generate 3 different story sequences
- Score sequences by:
  - Narrative coherence (40%)
  - Emotional arc (30%)
  - Visual variety (30%)
- Store best sequence in KG:
  ```turtle
  <sequence:uuid> a book:StorySequence ;
    book:hasOrderedPages (<pair:1> <pair:2> ...) ;
    book:sequenceRationale "Begins with character intro..." ;
    book:narrativeArcScore 0.92 .
  ```

**Existing Code Reused:**
- ✅ `ImageAnalysisAgent` for visual analysis
- ✅ GPT-4o for narrative planning
- ✅ `PlannerAgent` patterns for multi-option generation

---

#### 4. Story Writer Agent
**File:** `agents/domain/story_writer_agent.py`  
**Extends:** `BaseAgent`  
**Dependencies:** GPT-4o, KG Manager  

**Responsibilities:**
- Research children's book writing best practices (age 3-7)
- Generate age-appropriate text for each page (50-100 words)
- Store story text in KG:
  ```turtle
  <page:1> book:hasStoryText """
    Once upon a time, there was a little monster named Max.
    Max loved to play in the colorful garden...
  """^^xsd:string ;
    book:textWordCount 45 ;
    book:readingLevel "Grade K-1" .
  ```

**Existing Code Reused:**
- ✅ `AgenticPromptAgent` pattern
- ✅ GPT-4o for text generation

---

### Phase 3: Visual Layout

#### 5. Spatial Color Arrangement Agent
**File:** `agents/domain/spatial_color_agent.py`  
**Extends:** `BaseAgent`  
**Dependencies:** ColorPaletteAgent, KG Manager  

**Responsibilities:**
- Analyze color palette of each output image
- Arrange images in 2D space using:
  - PCA/t-SNE on color vectors for projection
  - Or grid algorithm: group by hue, sort by saturation/brightness
- Compute color harmony scores between adjacent images
- Store spatial positions in KG:
  ```turtle
  <image:output_001.png> 
    book:spatialPosition "0,0"^^xsd:string ;
    book:dominantColor "#FF5733"^^xsd:string ;
    book:colorHarmonyNeighbors (<image:output_002.png> <image:output_003.png>) .
  ```

**Existing Code Reused:**
- ✅ `ColorPaletteAgent` for color analysis
- ✅ `CompositionAgent` patterns

---

#### 6. Grid Layout Decision Agent
**File:** `agents/domain/grid_layout_agent.py`  
**Extends:** `BaseAgent`  
**Dependencies:** Spatial Color Agent, KG Manager  

**Responsibilities:**
- Determine optimal grid size for each page:
  - N ≤ 4: Use 2x2 grid
  - 5 ≤ N ≤ 9: Use 3x3 grid
  - 10 ≤ N ≤ 12: Use 3x4 grid
  - N > 12: Use 4x4 grid OR multiple pages
- Optimize layout by:
  - Color harmony (adjacent cells)
  - Visual balance (distribute colors)
  - Composition variety
- Store layout in KG:
  ```turtle
  <layout:page_1> a book:GridLayout ;
    book:gridDimensions "3x4"^^xsd:string ;
    book:cellAssignments (
      [book:position "0,0"; book:image <image:out_1.png>]
      [book:position "0,1"; book:image <image:out_2.png>]
      ...
    ) ;
    book:colorHarmonyScore 0.89 ;
    book:visualBalanceScore 0.91 .
  ```
- **Anti-Lazy Incentive:** Agent MUST justify grid choice with harmony/balance scores

**Existing Code Reused:**
- ✅ Spatial arrangement patterns from book generators
- ✅ Color analysis from ColorPaletteAgent

---

### Phase 4: Page Design & Review

#### 7. Page Design Agent
**File:** `agents/domain/page_design_agent.py`  
**Extends:** `BaseAgent`  
**Dependencies:** All previous agents, KG Manager  

**Responsibilities:**
- Create complete page design for each page:
  - **Left column:** Input image + story text
  - **Right column:** Output images in grid layout
- Generate design suggestions:
  - Font recommendations
  - Text placement
  - Spacing/margins
  - Background colors
- Create `book:PageDesign` node in KG:
  ```turtle
  <pageDesign:page_1> a book:PageDesign ;
    book:pageNumber 1 ;
    book:leftColumn [
      book:hasInputImage <image:input_001.png> ;
      book:hasStoryText "..." ;
      book:textFont "Comic Sans MS" ;
      book:textSize "18pt"
    ] ;
    book:rightColumn [
      book:hasGridLayout <layout:page_1> ;
      book:gridImages (<img:out_1> <img:out_2> ... <img:out_12>) ;
      book:gridDimensions "3x4"
    ] ;
    book:designSuggestions "Use warm background, high contrast text..." ;
    book:designStatus "pending_review" .
  ```

**Existing Code Reused:**
- ✅ Composition patterns from `generate_complete_book_now.py`
- ✅ Layout generation from book generators

---

#### 8. Design Review Agent
**File:** `agents/domain/design_review_agent.py`  
**Extends:** `BaseAgent`  
**Dependencies:** CriticAgent patterns, KG Manager  

**Responsibilities:**
- Review each `book:PageDesign` for:
  - Completeness (all elements present)
  - Color harmony across images
  - Text readability
  - Visual balance
- Provide feedback and approval:
  ```turtle
  <review:page_1> a book:DesignReview ;
    book:reviewsDesign <pageDesign:page_1> ;
    book:completenessScore 1.0 ;
    book:qualityScore 0.88 ;
    book:feedback "Consider darker text for better contrast" ;
    book:approved true .
  ```
- Update status: `book:designStatus "approved"` or flag for redesign

**Existing Code Reused:**
- ✅ `CriticAgent` patterns
- ✅ Quality review workflows

---

### Phase 5: Final Generation

#### 9. Book Layout Generator Agent
**File:** `agents/domain/book_layout_agent.py`  
**Extends:** `BaseAgent`  
**Dependencies:** All approved designs, KG Manager, GCS  

**Responsibilities:**
- Query KG for all approved `book:PageDesign` nodes
- Generate HTML for each page:
  ```html
  <div class="book-page">
    <div class="left-column">
      <img src="[input_image_url]" class="input-image" />
      <div class="story-text">[story text]</div>
    </div>
    <div class="right-column">
      <div class="image-grid grid-3x4">
        <img src="[output_1_url]" />
        <!-- ... 12 images in 3x4 grid -->
      </div>
    </div>
  </div>
  ```
- Generate responsive CSS
- Convert HTML to PDF using WeasyPrint/pdfkit
- Upload to GCS and store in KG:
  ```turtle
  <book:complete> a schema:Book ;
    book:hasPages (<pageDesign:1> <pageDesign:2> ...) ;
    schema:contentUrl "gs://bucket/book_final.pdf" ;
    schema:encodingFormat "application/pdf" ;
    dc:created "2025-01-08T..."^^xsd:dateTime .
  ```

**Existing Code Reused:**
- ✅ HTML generation from `generate_complete_book_now.py`
- ✅ GCS upload utilities
- ✅ PDF generation patterns

---

### Phase 6: Orchestration

#### 10. Children's Book Orchestrator Agent
**File:** `agents/domain/childrens_book_orchestrator.py`  
**Extends:** `BaseAgent`  
**Dependencies:** All agents above, Orchestration Workflow  

**Responsibilities:**
- Execute 7-step workflow:
  1. **Download & Ingest:** Call ImageIngestionAgent
  2. **Pair Images:** Call ImagePairingAgent
  3. **Sequence Story:** Call StorySequencingAgent
  4. **Arrange Colors:** Call SpatialColorAgent
  5. **Decide Grids:** Call GridLayoutAgent
  6. **Write Story:** Call StoryWriterAgent
  7. **Design Pages:** Call PageDesignAgent
  8. **Review Designs:** Call DesignReviewAgent
  9. **Generate Book:** Call BookLayoutAgent
- Store workflow provenance in KG:
  ```turtle
  <workflow:book_123> a book:BookGenerationWorkflow ;
    prov:startedAtTime "..."^^xsd:dateTime ;
    prov:used (<task:download> <task:pair> ...) ;
    prov:generated <book:complete> ;
    book:workflowStatus "completed" .
  ```
- Research phase before each step

**Existing Code Reused:**
- ✅ `OrchestrationWorkflow` pattern
- ✅ `PlannerAgent` workflow management

---

## KG Schema Extensions

### New Ontology: `kg/schemas/childrens_book_ontology.ttl`

```turtle
@prefix book: <http://example.org/childrens-book#> .
@prefix schema: <http://schema.org/> .
@prefix kg: <http://example.org/kg#> .

# Classes
book:Page a owl:Class ;
  rdfs:subClassOf schema:CreativeWork ;
  rdfs:label "Book Page" .

book:InputImage a owl:Class ;
  rdfs:subClassOf schema:ImageObject ;
  rdfs:label "Input Image" .

book:OutputImage a owl:Class ;
  rdfs:subClassOf schema:ImageObject ;
  rdfs:label "Output Image" .

book:ImagePair a owl:Class ;
  rdfs:label "Image Pair (input → outputs)" .

book:GridLayout a owl:Class ;
  rdfs:label "Grid Layout (2x2, 3x3, 3x4, etc.)" .

book:PageDesign a owl:Class ;
  rdfs:label "Complete Page Design" .

book:StorySequence a owl:Class ;
  rdfs:label "Story Sequence" .

book:DesignReview a owl:Class ;
  rdfs:label "Design Review" .

book:BookGenerationWorkflow a owl:Class ;
  rdfs:label "Book Generation Workflow" .

# Properties
book:hasInputImage a owl:ObjectProperty ;
  rdfs:domain book:ImagePair ;
  rdfs:range book:InputImage .

book:hasOutputImages a owl:ObjectProperty ;
  rdfs:domain book:ImagePair ;
  rdfs:range rdf:List .

book:hasGridLayout a owl:DatatypeProperty ;
  rdfs:domain book:PageDesign ;
  rdfs:range xsd:string .

book:hasStoryText a owl:DatatypeProperty ;
  rdfs:domain book:Page ;
  rdfs:range xsd:string .

book:spatialPosition a owl:DatatypeProperty ;
  rdfs:domain schema:ImageObject ;
  rdfs:range xsd:string ;
  rdfs:comment "x,y coordinates in KG space" .

book:colorHarmonyScore a owl:DatatypeProperty ;
  rdfs:range xsd:float .

book:visualBalanceScore a owl:DatatypeProperty ;
  rdfs:range xsd:float .

book:pairConfidence a owl:DatatypeProperty ;
  rdfs:domain book:ImagePair ;
  rdfs:range xsd:float .

book:designStatus a owl:DatatypeProperty ;
  rdfs:domain book:PageDesign ;
  rdfs:range xsd:string .
```

---

## Data Flow

```
1. GCS Buckets
   ├─ input_kids_monster/
   │  ├─ input_001.png
   │  └─ input_002.png
   └─ generated_images/
      ├─ output_001_a.png
      ├─ output_001_b.png
      └─ ...

2. ImageIngestionAgent
   ↓ (downloads + embeds + stores in KG & Qdrant)

3. Knowledge Graph
   ├─ <image:input_001> a book:InputImage ;
   │    kg:hasEmbedding [1536 floats] ;
   │    schema:contentUrl "gs://..." .
   └─ <image:output_001_a> a book:OutputImage ;
        kg:hasEmbedding [1536 floats] ;
        schema:contentUrl "gs://..." .

4. ImagePairingAgent
   ↓ (similarity search + pairing)

5. Knowledge Graph
   └─ <pair:1> a book:ImagePair ;
        book:hasInputImage <image:input_001> ;
        book:hasOutputImages (<image:output_001_a> ...) .

6. StorySequencingAgent
   ↓ (analyze + sequence)

7. Knowledge Graph
   └─ <sequence:1> a book:StorySequence ;
        book:hasOrderedPages (<pair:1> <pair:2> ...) .

8. SpatialColorAgent + GridLayoutAgent
   ↓ (arrange by color + decide grid)

9. Knowledge Graph
   └─ <layout:page_1> a book:GridLayout ;
        book:gridDimensions "3x4" ;
        book:cellAssignments (...) .

10. StoryWriterAgent
    ↓ (generate text)

11. Knowledge Graph
    └─ <page:1> book:hasStoryText "Once upon a time..." .

12. PageDesignAgent
    ↓ (combine all elements)

13. Knowledge Graph
    └─ <pageDesign:1> a book:PageDesign ;
         book:leftColumn [...] ;
         book:rightColumn [...] .

14. DesignReviewAgent
    ↓ (review + approve)

15. Knowledge Graph
    └─ <pageDesign:1> book:designStatus "approved" .

16. BookLayoutAgent
    ↓ (generate HTML/PDF)

17. Final Output
    ├─ book_final.pdf (uploaded to GCS)
    └─ <book:complete> in KG with all provenance
```

---

## Implementation Checklist

### ✅ Completed
- [x] Task 1: ImageEmbeddingService (`kg/services/image_embedding_service.py`)

### 🔄 In Progress
- [ ] Task 2: KG Schema Extension (`kg/schemas/childrens_book_ontology.ttl`)
- [ ] Task 3: ImageIngestionAgent (`agents/domain/image_ingestion_agent.py`)
- [ ] Task 4: ImagePairingAgent (`agents/domain/image_pairing_agent.py`)
- [ ] Task 5: StorySequencingAgent (`agents/domain/story_sequencing_agent.py`)
- [ ] Task 6: SpatialColorAgent (`agents/domain/spatial_color_agent.py`)
- [ ] Task 7: GridLayoutAgent (`agents/domain/grid_layout_agent.py`)
- [ ] Task 8: StoryWriterAgent (`agents/domain/story_writer_agent.py`)
- [ ] Task 9: PageDesignAgent (`agents/domain/page_design_agent.py`)
- [ ] Task 10: DesignReviewAgent (`agents/domain/design_review_agent.py`)
- [ ] Task 11: BookLayoutAgent (`agents/domain/book_layout_agent.py`)
- [ ] Task 12: ChildrensBookOrchestrator (`agents/domain/childrens_book_orchestrator.py`)
- [ ] Task 13: Integration Tests (`tests/test_childrens_book_swarm.py`)
- [ ] Task 14: CLI Entry Point (`scripts/generate_childrens_book.py`)

---

## Key Design Decisions

### 1. Embedding Strategy
- Use GPT-4o vision to describe images
- Embed descriptions with text-embedding-3-large (1536 dims)
- This ensures consistency with existing DiaryAgent patterns

### 2. Grid Size Incentives
- Agent scoring system penalizes lazy 2x2 grids unless N ≤ 4
- Color harmony and visual balance scores MUST be >= 0.75 for approval
- Forces thoughtful layout decisions

### 3. Provenance Tracking
- Every step logged to KG with timestamps
- Complete audit trail of all decisions
- SPARQL-queryable for analysis

### 4. Quality Gates
- Pairing confidence threshold: 0.7
- Design approval requires completeness + quality scores
- Multi-agent review workflow

---

## Example SPARQL Queries

### Get all image pairs for a book
```sparql
PREFIX book: <http://example.org/childrens-book#>
SELECT ?input ?outputs ?confidence WHERE {
  ?pair a book:ImagePair ;
    book:hasInputImage ?input ;
    book:hasOutputImages ?outputs ;
    book:pairConfidence ?confidence .
}
```

### Get page designs with 3x4 grids
```sparql
PREFIX book: <http://example.org/childrens-book#>
SELECT ?page ?grid WHERE {
  ?page a book:PageDesign ;
    book:hasGridLayout "3x4"^^xsd:string ;
    book:rightColumn ?grid .
}
```

### Get workflow timeline
```sparql
PREFIX book: <http://example.org/childrens-book#>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?step ?time WHERE {
  <workflow:book_123> prov:used ?step .
  ?step prov:startedAtTime ?time .
} ORDER BY ?time
```

---

## Testing Strategy

### Unit Tests
- Each agent tested independently with mock data
- Embedding similarity tests with known image pairs
- Layout algorithm tests with various grid sizes

### Integration Tests
- End-to-end book generation with 3 pages
- Edge cases: odd number of outputs, missing pairs
- Performance tests: 100 images in < 5 minutes

### Quality Tests
- Verify grid sizes match specification (3x3, 3x4)
- Check color harmony scores >= 0.75
- Validate story coherence with GPT-4o

---

## Future Enhancements

1. **Multi-page spreads:** Support for content spanning 2 pages
2. **Interactive elements:** Add clickable regions for digital books
3. **Audio narration:** Generate TTS for story text
4. **Localization:** Support for multiple languages
5. **Style transfer:** Apply consistent artistic style across output images
6. **Character tracking:** Maintain character consistency across pages

---

## Dependencies

### Python Packages
```
openai>=1.0.0
qdrant-client>=1.7.0
rdflib>=7.0.0
pillow>=10.0.0
numpy>=1.24.0
httpx>=0.25.0
google-cloud-storage>=2.10.0
weasyprint>=60.0  # For PDF generation
loguru>=0.7.0
pydantic>=2.0.0
```

### External Services
- OpenAI API (GPT-4o + text-embedding-3-large)
- Qdrant (localhost:6333)
- Google Cloud Storage
- Fuseki triple store (optional, for SPARQL queries)

---

**End of Architecture Document**

