#!/usr/bin/env python3
"""
Add Children's Book Generation Tasks to TaskMaster

This script adds all 13 tasks for the children's book agentic swarm to TaskMaster.
It ensures proper dependency ordering and comprehensive task definitions.

Date: 2025-01-08
"""

import json
from pathlib import Path
from typing import Dict, List, Any

# Define all 13 children's book tasks
CHILDRENS_BOOK_TASKS = [
    {
        "id": 100,  # Start at 100 to avoid conflicts
        "title": "Extend KG Schema for Children's Book Pages",
        "description": "Create RDF ontology for children's book data model with classes for pages, images, layouts, and designs.",
        "details": """1. Create kg/schemas/childrens_book_ontology.ttl
2. Define classes:
   - book:Page (extends schema:CreativeWork)
   - book:InputImage (extends schema:ImageObject)
   - book:OutputImage (extends schema:ImageObject)
   - book:ImagePair (links input → outputs)
   - book:GridLayout (3x3, 3x4, 2x2, 4x4)
   - book:PageDesign (complete page with all elements)
3. Define properties:
   - book:hasInputImage, book:hasOutputImages (ordered list)
   - book:hasGridLayout (literal: "3x3", "3x4")
   - book:hasStoryText, book:hasDesignSuggestions
   - book:sequenceOrder (for story ordering)
   - book:colorHarmonyScore, book:spatialPosition (x,y)
4. Add namespace to KG manager
5. Document all classes and properties with rdfs:comment""",
        "testStrategy": "Load ontology into KG, query for all classes and properties. Verify namespace resolution. Create sample instances of each class.",
        "priority": "high",
        "dependencies": [],
        "status": "pending",
        "subtasks": []
    },
    {
        "id": 101,
        "title": "Image Download & KG Ingestion Agent",
        "description": "Agent that downloads images from GCS, generates embeddings, and stores in KG with Qdrant indexing.",
        "details": """1. Create agents/domain/image_ingestion_agent.py extending BaseAgent
2. Reuse user's GCS download script logic
3. For each image (input + output):
   - Download from GCS (if not cached)
   - Generate embedding using ImageEmbeddingService
   - Store in KG as schema:ImageObject with:
     * schema:contentUrl (GCS URL)
     * kg:hasEmbedding (vector)
     * kg:imageType ("input" or "output")
     * schema:name (filename)
     * dc:created (timestamp)
   - Store embedding in Qdrant with image URI as ID
4. Use KGLogger pattern from semant/agent_tools/midjourney/kg_logging.py
5. Batch processing for efficiency (process 10 images at a time)
6. Progress tracking in KG""",
        "testStrategy": "Download 5 test images, verify all in KG with embeddings. Query Qdrant for similarity. Test with missing files.",
        "priority": "high",
        "dependencies": [100],  # Needs KG schema
        "status": "pending",
        "subtasks": []
    },
    {
        "id": 102,
        "title": "Image Pairing Agent",
        "description": "Agent that pairs input images with related output images using embedding similarity and metadata.",
        "details": """1. Create agents/domain/image_pairing_agent.py extending BaseAgent
2. Algorithm:
   - Query KG for all kg:imageType "input" images
   - For each input image:
     * Get embedding from Qdrant
     * Query Qdrant for top-N similar images with kg:imageType "output"
     * Score by:
       - Embedding similarity (60% weight)
       - Filename pattern matching (20% weight) [e.g., "kid_01" → "kid_01_monster_a"]
       - Metadata correlation (20% weight) [upload time, size]
   - Create book:ImagePair in KG:
       <pair:uuid> a book:ImagePair ;
         book:hasInputImage <image:input_001.png> ;
         book:hasOutputImages (<image:output_001_a.png> <image:output_001_b.png> ...) ;
         book:pairConfidence 0.95 ;
         book:pairingMethod "embedding+filename" .
3. Incentive: Pairs with confidence < 0.7 trigger human review flag
4. Store all pairing attempts (even low confidence) for analysis""",
        "testStrategy": "Pair 3 inputs to 9 outputs. Verify correct groupings. Test edge cases: no matches, multiple perfect matches.",
        "priority": "high",
        "dependencies": [101],  # Needs images in KG with embeddings
        "status": "pending",
        "subtasks": []
    },
    {
        "id": 103,
        "title": "Story Sequencing Agent",
        "description": "Agent that arranges input images in narrative order using visual analysis and LLM reasoning.",
        "details": """1. Create agents/domain/story_sequencing_agent.py extending BaseAgent
2. Research phase using GPT-4o:
   - "What makes a good children's book narrative arc?"
   - "How to sequence images into a story?"
3. Algorithm:
   - Analyze all input images for narrative potential:
     * Character presence (using ImageAnalysisAgent)
     * Action/emotion progression
     * Setting changes
   - Use LLM to propose 3 different sequences with rationale
   - Score each sequence by:
     * Narrative coherence (40%): logical flow, cause-effect
     * Emotional arc (30%): variety, climax, resolution
     * Visual variety (30%): color, composition changes
4. Store best sequence in KG:
     <sequence:uuid> a book:StorySequence ;
       book:hasOrderedPages (<pair:1> <pair:2> <pair:3> ...) ;
       book:sequenceRationale "Begins with character intro..." ;
       book:narrativeArcScore 0.92 .
5. Also store rejected sequences for comparison""",
        "testStrategy": "Sequence 6 random images. Verify logical order. Test with ambiguous images (no clear sequence).",
        "priority": "high",
        "dependencies": [102],  # Needs image pairs
        "status": "pending",
        "subtasks": []
    },
    {
        "id": 104,
        "title": "Spatial Color Arrangement Agent",
        "description": "Agent that arranges output images in 2D space by color similarity for visually harmonious layouts.",
        "details": """1. Create agents/domain/spatial_color_agent.py extending BaseAgent
2. For each set of output images (from Task 102 pairs):
   - Analyze color using existing ColorPaletteAgent
   - Extract dominant colors (RGB vectors)
   - Compute color harmony score between all pairs
   - Arrange in 2D KG space using:
     * Option A: PCA/t-SNE on color vectors for 2D projection
     * Option B: Grid algorithm - group by hue, sort by saturation/brightness
3. Store spatial positions in KG:
     <image:output_001.png> book:spatialPosition "0,0"^^xsd:string ;
       book:dominantColor "#FF5733"^^xsd:string ;
       book:colorHarmonyNeighbors (<image:output_002.png> <image:output_003.png>) .
4. Algorithm ensures visually pleasing neighbors (high color harmony)
5. Reuse patterns from agents/domain/color_palette_agent.py""",
        "testStrategy": "Arrange 12 images. Verify color gradients. Test with monochrome images, extreme colors.",
        "priority": "high",
        "dependencies": [101],  # Needs images in KG
        "status": "pending",
        "subtasks": []
    },
    {
        "id": 105,
        "title": "Grid Layout Decision Agent",
        "description": "Agent that determines optimal grid layout (2x2, 3x3, 3x4, 4x4) for each page's output images.",
        "details": """1. Create agents/domain/grid_layout_agent.py extending BaseAgent
2. For each page's output images:
   - Count images: N
   - Decision tree:
     * If N ≤ 4: Use 2x2 grid
     * If 5 ≤ N ≤ 9: Use 3x3 grid
     * If 10 ≤ N ≤ 12: Use 3x4 grid
     * If N > 12: Use 4x4 grid OR split across multiple pages
3. Optimize layout by:
   - Color harmony (adjacent cells from Task 104)
   - Visual balance (distribute colors evenly)
   - Composition variety (alternate close-ups and wide shots)
4. Store in KG:
     <layout:page_1> a book:GridLayout ;
       book:gridDimensions "3x4"^^xsd:string ;
       book:cellAssignments (
         [book:position "0,0"; book:image <image:out_1.png>]
         [book:position "0,1"; book:image <image:out_2.png>]
         ...
       ) ;
       book:colorHarmonyScore 0.89 ;
       book:visualBalanceScore 0.91 .
5. **INCENTIVE:** Agent MUST justify grid choice with scores. Lazy 2x2 grids penalized unless N ≤ 4.
6. Include optimization reasoning in KG""",
        "testStrategy": "Test with 6, 9, 12, 15 images. Verify optimal grids. Test penalty for unjustified 2x2.",
        "priority": "high",
        "dependencies": [104],  # Needs color arrangement
        "status": "pending",
        "subtasks": []
    },
    {
        "id": 106,
        "title": "Story Writer Agent",
        "description": "Agent that generates age-appropriate story text for each page based on images and narrative context.",
        "details": """1. Create agents/domain/story_writer_agent.py extending BaseAgent
2. Research phase:
   - "Children's book writing best practices (age 3-7)"
   - "Story pacing and sentence structure for kids"
3. For each page (from Task 103 sequence):
   - Get input image description (from ImageAnalysisAgent)
   - Get narrative context (position in sequence, previous pages)
   - Generate age-appropriate text (50-100 words)
   - Style guidelines:
     * Simple vocabulary
     * Short sentences
     * Repetition for rhythm
     * Onomatopoeia encouraged
     * Emotional engagement
4. Store in KG:
     <page:1> book:hasStoryText \"\"\"
       Once upon a time, there was a little monster named Max.
       Max loved to play in the colorful garden...
     \"\"\"^^xsd:string ;
       book:textWordCount 45 ;
       book:readingLevel "Grade K-1" ;
       book:emotionalTone "joyful" .
5. Reuse patterns from GPT-4o similar to agents/domain/agentic_prompt_agent.py""",
        "testStrategy": "Generate story for 5 pages. Verify coherence, age-appropriateness. Test with different emotional arcs.",
        "priority": "medium",
        "dependencies": [103],  # Needs story sequence
        "status": "pending",
        "subtasks": []
    },
    {
        "id": 107,
        "title": "Page Design Agent",
        "description": "Agent that creates complete page layouts combining input image, story text, and output grid.",
        "details": """1. Create agents/domain/page_design_agent.py extending BaseAgent
2. For EACH page:
   - Gather all components:
     * Input image (left column) from Task 102 pair
     * Story text (left column, below input) from Task 106
     * Output images (right column) from Task 102 pair
     * Grid layout spec (from Task 105)
   - Generate design suggestions:
     * Font recommendations (Comic Sans MS, Arial Rounded)
     * Text placement (padding, alignment)
     * Spacing/margins
     * Background colors (complement dominant image colors)
3. Create complete PageDesign node in KG:
     <pageDesign:page_1> a book:PageDesign ;
       book:pageNumber 1 ;
       book:leftColumn [
         book:hasInputImage <image:input_001.png> ;
         book:hasStoryText "..." ;
         book:textFont "Comic Sans MS" ;
         book:textSize "18pt" ;
         book:textColor "#333333"
       ] ;
       book:rightColumn [
         book:hasGridLayout <layout:page_1> ;
         book:gridImages (<img:out_1> <img:out_2> ... <img:out_12>) ;
         book:gridDimensions "3x4"
       ] ;
       book:designSuggestions "Use warm background, high contrast text..." ;
       book:designStatus "pending_review" .
4. Reuse composition patterns from book generators like generate_complete_book_now.py""",
        "testStrategy": "Create design for 3 pages (different grid sizes). Verify all elements present and positioned correctly.",
        "priority": "high",
        "dependencies": [102, 105, 106],  # Needs pairs, grids, and text
        "status": "pending",
        "subtasks": []
    },
    {
        "id": 108,
        "title": "Design Review Agent",
        "description": "Agent that reviews page designs for completeness and quality, providing feedback and approval.",
        "details": """1. Create agents/domain/design_review_agent.py extending BaseAgent
2. Review each book:PageDesign:
   - Check completeness:
     ✅ Input image present?
     ✅ Story text present?
     ✅ All output images in grid?
     ✅ Grid dimensions specified?
   - Check quality:
     * Color harmony across images
     * Text readability (contrast, font size)
     * Visual balance (not top-heavy, sides balanced)
     * Appropriate white space
3. Provide feedback:
     <review:page_1> a book:DesignReview ;
       book:reviewsDesign <pageDesign:page_1> ;
       book:completenessScore 1.0 ;
       book:qualityScore 0.88 ;
       book:feedback "Consider darker text for better contrast. Excellent color harmony." ;
       book:approved true .
4. If approved: book:designStatus "approved"
5. If rejected: Flag for redesign with specific issues
6. Reuse patterns from agents/domain/critic_agent.py""",
        "testStrategy": "Review 3 designs (good, mediocre, poor). Verify appropriate scores and feedback.",
        "priority": "medium",
        "dependencies": [107],  # Needs page designs
        "status": "pending",
        "subtasks": []
    },
    {
        "id": 109,
        "title": "HTML/PDF Layout Generator",
        "description": "Agent that generates final HTML and PDF book from approved page designs.",
        "details": """1. Create agents/domain/book_layout_agent.py extending BaseAgent
2. Query KG for all approved book:PageDesign nodes (ordered by pageNumber)
3. Generate HTML for each page:
   <div class=\"book-page\">
     <div class=\"left-column\">
       <img src=\"[input_image_url]\" class=\"input-image\" />
       <div class=\"story-text\">[story text]</div>
     </div>
     <div class=\"right-column\">
       <div class=\"image-grid grid-3x4\">
         <img src=\"[output_1_url]\" />
         <img src=\"[output_2_url]\" />
         <!-- ... N images in MxN grid -->
       </div>
     </div>
   </div>
4. CSS:
   - Responsive design
   - Print-friendly (@media print)
   - Grid layouts using CSS Grid
   - Page breaks
5. Generate PDF using WeasyPrint or pdfkit
6. Store in GCS and KG:
   <book:complete> a schema:Book ;
     book:hasPages (<pageDesign:1> <pageDesign:2> ...) ;
     schema:contentUrl "gs://bucket/childrens_book_final.pdf" ;
     schema:encodingFormat "application/pdf" ;
     dc:created "2025-01-08T..."^^xsd:dateTime .
7. Extend patterns from generate_complete_book_now.py HTML generation""",
        "testStrategy": "Generate PDF with 3 pages (different grids). Verify layout matches designs. Test print rendering.",
        "priority": "high",
        "dependencies": [108],  # Needs approved designs
        "status": "pending",
        "subtasks": []
    },
    {
        "id": 110,
        "title": "Children's Book Orchestrator Agent",
        "description": "Main orchestrator that coordinates all agents to execute the complete book generation workflow.",
        "details": """1. Create agents/domain/childrens_book_orchestrator.py extending BaseAgent
2. Implements 9-step workflow:
   Step 1: Download & Ingest
     - Call ImageIngestionAgent (Task 101)
     - Download images from GCS
     - Store in KG with embeddings
   Step 2: Pair Images
     - Call ImagePairingAgent (Task 102)
     - Match inputs to outputs
   Step 3: Sequence Story
     - Call StorySequencingAgent (Task 103)
     - Order pages for narrative
   Step 4: Arrange Colors
     - Call SpatialColorAgent (Task 104)
     - Position images in 2D color space
   Step 5: Decide Grids
     - Call GridLayoutAgent (Task 105)
     - Determine 3x3, 3x4 layouts
   Step 6: Write Story
     - Call StoryWriterAgent (Task 106)
     - Generate text for each page
   Step 7: Design Pages
     - Call PageDesignAgent (Task 107)
     - Create complete page designs
   Step 8: Review Designs
     - Call DesignReviewAgent (Task 108)
     - Quality check and approval
   Step 9: Generate Book
     - Call BookLayoutAgent (Task 109)
     - Create final HTML/PDF
3. Store workflow in KG:
   <workflow:book_123> a book:BookGenerationWorkflow ;
     prov:startedAtTime "..."^^xsd:dateTime ;
     prov:used (<task:download> <task:pair> <task:sequence> ...) ;
     prov:generated <book:complete> ;
     book:workflowStatus "completed" .
4. Research phase: Query best practices for each step before executing
5. Reuse patterns from agents/core/orchestration_workflow.py""",
        "testStrategy": "End-to-end test with 3 input images, 9 outputs. Verify all 9 steps execute. Generate complete PDF.",
        "priority": "critical",
        "dependencies": [101, 102, 103, 104, 105, 106, 107, 108, 109],  # Needs ALL agents
        "status": "pending",
        "subtasks": []
    },
    {
        "id": 111,
        "title": "Integration Testing Suite for Children's Book Swarm",
        "description": "Comprehensive test suite covering all book generation scenarios and edge cases.",
        "details": """1. Create tests/test_childrens_book_swarm.py
2. Test scenarios:
   - Small book (2 pages, 2x2 grids)
     * 2 input images, 8 output images
     * Verify simple workflow
   - Medium book (5 pages, 3x3 grids)
     * 5 input images, 45 output images
     * Test sequencing logic
   - Large book (10 pages, 3x4 grids)
     * 10 input images, 120 output images
     * Test scalability
   - Edge cases:
     * Odd number of outputs per input
     * Missing image pairs
     * Low confidence pairings
     * Images with similar colors
3. Verify for each scenario:
   - All images in KG with embeddings
   - All pairs created with confidence scores
   - Story coherent and age-appropriate
   - Grids optimal (not lazy 2x2)
   - PDF generated successfully
   - All KG nodes properly linked
4. Performance tests:
   - Embedding generation speed
   - SPARQL query efficiency
   - PDF generation time
5. Mock external services (GCS, Qdrant) where appropriate""",
        "testStrategy": "Run all scenarios. 100% pass rate. Coverage > 90% for new agents.",
        "priority": "high",
        "dependencies": [110],  # Needs orchestrator complete
        "status": "pending",
        "subtasks": []
    },
    {
        "id": 112,
        "title": "CLI Entry Point for Children's Book Generation",
        "description": "Command-line interface for generating children's books with configurable parameters.",
        "details": """1. Create scripts/generate_childrens_book.py
2. CLI arguments:
   --bucket: GCS bucket name (default: from env GCS_BUCKET_NAME)
   --input-prefix: GCS prefix for input images (default: "input_kids_monster/")
   --output-prefix: GCS prefix for output images (default: "generated_images/")
   --title: Book title (required)
   --target-age: Target age range (default: "3-7")
   --output-dir: Local output directory (default: "childrens_books/")
   --grid-preference: Preferred grid size (optional: "3x3", "3x4", "auto")
3. Workflow:
   - Parse arguments and validate
   - Initialize ChildrensBookOrchestrator
   - Set configuration from CLI args
   - Call orchestrator.run()
   - Report progress with rich progress bars
   - Output final PDF location
4. Integration:
   - Extend user's GCS download script patterns
   - Store all outputs in specified directory
   - Log workflow URI for KG queries
5. Example usage:
   python scripts/generate_childrens_book.py \\
     --title=\"Max's Monster Adventure\" \\
     --target-age=\"4-6\" \\
     --grid-preference=\"3x3\"
6. Output:
   - PDF at childrens_books/maxs_monster_adventure.pdf
   - Workflow URI for KG inspection
   - Summary statistics""",
        "testStrategy": "CLI test with sample data. Verify all args work. Test error handling for missing bucket.",
        "priority": "medium",
        "dependencies": [110],  # Needs orchestrator
        "status": "pending",
        "subtasks": []
    }
]


def add_tasks_to_taskmaster(tasks_file: Path, new_tasks: List[Dict[str, Any]]) -> None:
    """
    Add new tasks to TaskMaster JSON file.
    
    Args:
        tasks_file: Path to tasks.json
        new_tasks: List of task dictionaries to add
    """
    # Load existing tasks
    with open(tasks_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get master tasks
    master_tasks = data.get("master", {}).get("tasks", [])
    
    # Find highest existing ID
    max_id = max([t.get("id", 0) for t in master_tasks], default=0)
    print(f"Highest existing task ID: {max_id}")
    
    # Check if children's book tasks already exist
    existing_ids = {t.get("id") for t in master_tasks}
    new_task_ids = {t.get("id") for t in new_tasks}
    
    if new_task_ids & existing_ids:
        overlap = new_task_ids & existing_ids
        print(f"⚠️  Warning: Task IDs {overlap} already exist. Skipping conflicting tasks.")
        new_tasks = [t for t in new_tasks if t.get("id") not in existing_ids]
    
    if not new_tasks:
        print("✅ All children's book tasks already exist in TaskMaster!")
        return
    
    # Add new tasks
    master_tasks.extend(new_tasks)
    data["master"]["tasks"] = master_tasks
    
    # Write back
    with open(tasks_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Added {len(new_tasks)} children's book tasks to TaskMaster!")
    print(f"   Task IDs: {sorted([t['id'] for t in new_tasks])}")


def main():
    """Main function to add children's book tasks."""
    # Find tasks.json
    project_root = Path.cwd()
    tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
    
    if not tasks_file.exists():
        print(f"❌ TaskMaster tasks file not found: {tasks_file}")
        print("   Please initialize TaskMaster first with: task-master init")
        return 1
    
    print("=" * 60)
    print("Adding Children's Book Generation Tasks to TaskMaster")
    print("=" * 60)
    print()
    
    # Add tasks
    add_tasks_to_taskmaster(tasks_file, CHILDRENS_BOOK_TASKS)
    
    print()
    print("=" * 60)
    print("Task Summary:")
    print("=" * 60)
    for task in CHILDRENS_BOOK_TASKS:
        deps = f" [deps: {task['dependencies']}]" if task['dependencies'] else ""
        print(f"  {task['id']}: {task['title']}{deps}")
    
    print()
    print("📋 Next steps:")
    print("   1. Review tasks: task-master list --status=pending")
    print("   2. View next task: task-master next")
    print("   3. Start work: task-master show 100")
    print()
    print("🤖 Agents can now access these tasks via TaskMasterAccessor!")
    
    return 0


if __name__ == "__main__":
    exit(main())

