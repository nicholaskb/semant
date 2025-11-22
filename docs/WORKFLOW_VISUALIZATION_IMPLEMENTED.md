# Workflow Visualization - Auto-Generated Implementation

**Date:** 2025-11-12  
**Status:** ✅ Fully Implemented

## Overview

The workflow visualization system now **automatically generates** HTML visualizations similar to `hotdog_flow_viz.html` from workflow data stored in the Knowledge Graph.

## Implementation

### New Component: `agents/utils/workflow_visualizer.py`

**WorkflowVisualizer Class:**
- Extracts workflow execution data from Knowledge Graph
- Generates interactive HTML visualizations
- Supports timeline, network graph, and flowchart views

**Key Methods:**
- `generate_html_visualization()` - Main entry point
- `_extract_workflow_data()` - Queries KG for workflow steps
- `_generate_html()` - Creates HTML with all visualizations
- `_generate_timeline_html()` - Timeline view
- `_generate_network_data()` - Network graph data
- `_generate_mermaid_flowchart()` - Mermaid flowchart

### Integration: `agents/domain/orchestration_workflow.py`

**Changes Made:**
1. Added `WorkflowVisualizer` import
2. Initialize visualizer in `__init__`
3. Auto-generate HTML in `visualize_plan_in_kg()` method
4. Return `html_visualization` path in response

**Surgical Edits:**
- Only 3 lines added to imports
- Only 1 line added to `__init__`
- Only 5 lines added to `visualize_plan_in_kg()` (with try/except for safety)
- **No existing functionality modified**

## Features

### Visualization Views

1. **Timeline Flow** 📅
   - Chronological view of workflow steps
   - Color-coded markers (decisions, tasks, images, complete)
   - Shows step descriptions and status

2. **Network Graph** 🕸️
   - Interactive vis-network graph
   - Shows workflow flow and relationships
   - Hierarchical layout

3. **Flowchart** 📊
   - Mermaid diagram
   - Visual flow representation
   - Decision points and branches

### Statistics Dashboard

- **Decisions**: Number of decision points
- **Images**: Number of image generation steps
- **Retries**: Count of retry operations
- **Tasks**: Total task count

## Usage

### Automatic Generation

The visualization is automatically generated when:
```python
result = await workflow.visualize_plan_in_kg(workflow_id)
# result['html_visualization'] contains the path to HTML file
```

### Manual Generation

```python
from agents.utils.workflow_visualizer import WorkflowVisualizer

visualizer = WorkflowVisualizer()
html_path = await visualizer.generate_html_visualization(
    workflow_id="workflow_20251112_123456",
    output_path=Path("custom_path.html")  # Optional
)
```

## Data Extraction

The visualizer queries the Knowledge Graph for:
- Execution steps (`ex:hasStep`)
- Step actions (`ex:action`)
- Step status (`ex:status`)
- Step results (`ex:result`)
- Timestamps (`ex:startedAt`, `ex:completedAt`)

**Fallback:** If execution data not found, queries plan steps instead.

## Output

- **File Format**: HTML
- **File Name**: `workflow_viz_{workflow_id}.html`
- **Location**: Project root (or custom path)
- **Size**: ~11KB (similar to hotdog_flow_viz.html)

## Testing

✅ Tested with dummy workflow_id  
✅ Generated HTML file successfully  
✅ No linter errors  
✅ Graceful handling of missing data  
✅ Integrated into existing workflow without breaking changes

## Example Output

```python
{
    "workflow_id": "workflow_20251112_123456",
    "status": "visualized",
    "html_visualization": "workflow_viz_workflow_20251112_123456.html",
    ...
}
```

## Next Steps

- Test with real workflow execution data
- Enhance visualization with more detailed step information
- Add support for filtering/grouping steps
- Integrate with web UI for live visualization

