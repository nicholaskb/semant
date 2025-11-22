# Agent Book Generator Tool Guide

## Overview

The `BookGeneratorTool` is a powerful agent tool that enables AI agents to create complete illustrated books using Midjourney, Google Cloud Storage, and Knowledge Graph integration.

## Tool Registration

The tool is registered in the agent tools registry as:
```python
"mj.book_generator": BookGeneratorTool
```

## How Agents Use This Tool

### 1. Discovery

Agents can discover the tool through the registry:

```python
from semant.agent_tools.midjourney import REGISTRY

# List all available tools
available_tools = list(REGISTRY.keys())
# ['mj.imagine', 'mj.describe', ..., 'mj.book_generator']
```

### 2. Initialization

Agents create an instance of the tool:

```python
# Get the tool factory
book_tool_factory = REGISTRY.get("mj.book_generator")

# Create tool instance
book_tool = book_tool_factory()
```

### 3. Book Generation

Agents call the tool with book content:

```python
result = await book_tool.run(
    title="Book Title",
    pages=[
        {
            "title": "Page Title",
            "text": "Page content text...",
            "prompt": "Midjourney prompt for illustration..."
        },
        # More pages...
    ],
    max_pages_to_illustrate=6  # Cost control
)
```

## Input Format

### Required Fields

- `title` (str): The book title
- `pages` (List[Dict]): List of page dictionaries

### Page Dictionary Structure

Each page must contain:
- `title` (str): Page title/chapter name
- `text` (str): The story text for this page
- `prompt` (str): Midjourney prompt for generating the illustration

### Optional Parameters

- `workflow_id` (str): Custom workflow ID (auto-generated if not provided)
- `output_dir` (str): Custom output directory (default: `agent_books/{workflow_id}`)
- `max_pages_to_illustrate` (int): Maximum pages to illustrate (default: 6)

## Output Format

The tool returns a dictionary containing:

```python
{
    "workflow_id": "book_20250917_123456",
    "title": "Book Title",
    "pages_generated": 6,
    "total_pages": 12,
    "output_files": {
        "markdown": "agent_books/book_20250917_123456/book.md",
        "metadata": "agent_books/book_20250917_123456/metadata.json"
    },
    "generated_images": {
        1: {
            "job_id": "uuid",
            "task_id": "midjourney-task-id",
            "image_url": "https://cdn.midjourney.com/...",
            "gcs_url": "https://storage.googleapis.com/..."
        },
        # More pages...
    }
}
```

## Knowledge Graph Integration

All book generation activities are logged to the Knowledge Graph:

### Workflow Logging
- Tool calls are logged with `mj:ToolCall` nodes
- Each illustration creates a `schema:ImageObject` node
- Pages are linked with `dc:isPartOf` relationships

### SPARQL Query Examples

Agents can query generated books:

```sparql
# Get all illustrations for a book
PREFIX schema: <http://schema.org/>
PREFIX dc: <http://purl.org/dc/terms/>

SELECT ?page ?title ?image_url ?gcs_url
WHERE {
    ?page dc:isPartOf <http://example.org/book/WORKFLOW_ID> .
    ?page dc:title ?title .
    OPTIONAL { ?page schema:url ?image_url }
    OPTIONAL { ?page schema:contentUrl ?gcs_url }
}
ORDER BY ?page
```

## Features

### Automatic Processing
- **Midjourney Generation**: Submits prompts and polls for completion
- **GCS Upload**: Downloads and uploads images to Google Cloud Storage
- **Knowledge Graph**: Stores all metadata as RDF triples
- **Output Generation**: Creates Markdown and JSON files

### Error Handling
- Graceful failure on individual page errors
- Continues generation even if some pages fail
- Logs all errors to Knowledge Graph

### Cost Control
- `max_pages_to_illustrate` parameter limits API calls
- Uses "relax" mode for better availability
- Rate limiting between generations

## Example: Children's Book

```python
# Agent creates a children's book
book_content = {
    "title": "The Little Robot's Dream",
    "pages": [
        {
            "title": "A Robot Wakes Up",
            "text": "In a small workshop, a little robot opened its eyes for the first time.",
            "prompt": "Cute small robot waking up in cozy workshop, warm lighting, children's book illustration --ar 16:9 --v 6"
        },
        {
            "title": "The Dream",
            "text": "The robot dreamed of exploring the stars.",
            "prompt": "Small robot looking up at starry night sky through window, dreamy atmosphere, watercolor style --ar 16:9 --v 6"
        }
    ]
}

# Generate the book
result = await book_tool.run(**book_content)
```

## Integration with Other Agent Tools

The BookGeneratorTool can be combined with other tools:

1. **mj.describe**: Analyze existing images for style reference
2. **mj.imagine**: Generate additional standalone illustrations
3. **mj.action**: Upscale or create variations of book illustrations
4. **mj.gcs_mirror**: Mirror additional assets to GCS

## Best Practices for Agents

1. **Prompt Engineering**: Include style keywords like "children's book", "watercolor", "illustration"
2. **Aspect Ratio**: Use consistent aspect ratios (16:9 works well for books)
3. **Version Control**: Specify Midjourney version (--v 6) for consistency
4. **Cost Management**: Set appropriate `max_pages_to_illustrate` limits
5. **Error Recovery**: Check `pages_generated` vs `total_pages` to identify failures

## Troubleshooting

### No Images Generated
- Check MIDJOURNEY_API_TOKEN in environment
- Verify prompts are valid Midjourney syntax
- Check API response for error messages

### GCS Upload Failures
- Verify GCS_BUCKET_NAME is set
- Check GOOGLE_APPLICATION_CREDENTIALS
- Ensure bucket has public access configured

### Knowledge Graph Issues
- Ensure KG manager is initialized
- Check for valid RDF triple syntax
- Verify namespace URIs are correct

## Summary

The BookGeneratorTool empowers agents to:
- **Create** complete illustrated books autonomously
- **Store** all content in queryable Knowledge Graph
- **Generate** professional Midjourney illustrations
- **Manage** costs with configurable limits
- **Output** publication-ready files

Agents can now offer book creation as a service, handling everything from story to final illustrated output!

