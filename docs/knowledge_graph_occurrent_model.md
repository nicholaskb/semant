# Knowledge Graph Occurrent Model

## Overview

This document defines the nomenclature and data model for tracking occurrences (occurrents) in the Knowledge Graph. The occurrent model provides a standardized way to track historical jobs, running jobs, and agent interactions over time.

## Core Concepts

### Occurrent
An **occurrent** is any event or occurrence that happens at a specific time with a duration. It represents something that happens in the system rather than something that exists.

### Types of Occurrents

1. **WorkflowOccurrent**: A workflow occurrence that happens at a specific time
2. **JobOccurrent**: A job occurrence that happens at a specific time
3. **AgentOccurrent**: An agent interaction occurrence

## Ontology Structure

### Core Classes

```
:Occurrent
    ↳ :WorkflowOccurrent
    ↳ :JobOccurrent
    ↳ :AgentOccurrent
```

### Properties

#### Temporal Properties
- `:hasOccurrenceTime`: The exact time when an occurrence happened
- `:hasStartTime`: The start time of an occurrence
- `:hasEndTime`: The end time of an occurrence
- `:hasDuration`: The duration of an occurrence

#### Status Properties
- `:hasStatus`: The current status (pending, completed, failed, etc.)
- `:hasResult`: The result or output of an occurrence
- `:hasError`: Any error associated with an occurrence

#### Workflow-Specific Properties
- `:hasTheme`: The theme or purpose of the workflow occurrence
- `:hasWorkflowName`: The name of the workflow occurrence

#### Job-Specific Properties
- `:hasJobType`: The type of job (imagine, action, describe, blend)
- `:hasTaskId`: The unique identifier of the job task
- `:hasProgress`: The progress percentage of the job

#### Agent-Specific Properties
- `:hasAgentId`: The identifier of the agent involved
- `:hasInteractionType`: The type of interaction (message, decision, action)

## Midjourney-Specific Ontology

### Classes

```
:MidjourneyJob
    ↳ :ImagineJob
    ↳ :ActionJob
    ↳ :DescribeJob
    ↳ :BlendJob

:MidjourneyWorkflow
:ImageGeneration
:PromptRefinement
```

### Properties

```
:hasPrompt
:hasModelVersion
:hasAspectRatio
:hasImageUrl
:hasDiscordImageUrl
:hasSeed
:hasJobStatus
:hasTheme
:hasWorkflowName
:containsJob
:hasRefinedPrompt
:hasOriginalPrompt
:hasAgentDecision
:hasParentJob
:hasChildJob
```

## Usage Examples

### Creating a Job Occurrence

```sparql
PREFIX core: <http://example.org/core#>
PREFIX mj: <http://example.org/midjourney#>

# Create occurrence
<http://example.org/midjourney/occurrence/720aa586-53a4-42b2-8e8c-09f579c9b561>
    a core:JobOccurrent ;
    a mj:ImagineJob ;
    core:hasTaskId "720aa586-53a4-42b2-8e8c-09f579c9b561" ;
    core:hasJobType "imagine" ;
    core:hasStatus "completed" ;
    core:hasStartTime "2025-09-25T00:47:14Z"^^xsd:dateTime ;
    core:hasEndTime "2025-09-25T00:47:45Z"^^xsd:dateTime ;
    core:hasProgress 100 ;
    mj:hasPrompt "authoritative prompt here" ;
    mj:hasModelVersion "v7" ;
    core:hasResult "https://storage.googleapis.com/bahroo_public/image.png" .
```

### Querying Historical Jobs

```sparql
PREFIX core: <http://example.org/core#>
PREFIX mj: <http://example.org/midjourney#>

SELECT ?occurrence ?jobType ?taskId ?status ?startTime ?endTime ?progress
WHERE {
    ?occurrence a core:JobOccurrent .
    ?occurrence core:hasJobType ?jobType .
    ?occurrence core:hasTaskId ?taskId .
    ?occurrence core:hasStatus ?status .
    ?occurrence core:hasStartTime ?startTime .
    OPTIONAL { ?occurrence core:hasEndTime ?endTime }
    OPTIONAL { ?occurrence core:hasProgress ?progress }
}
ORDER BY DESC(?startTime)
```

### Querying Running Jobs

```sparql
PREFIX core: <http://example.org/core#>
PREFIX mj: <http://example.org/midjourney#>

SELECT ?occurrence ?jobType ?taskId ?progress
WHERE {
    ?occurrence a core:JobOccurrent .
    ?occurrence core:hasJobType ?jobType .
    ?occurrence core:hasTaskId ?taskId .
    ?occurrence core:hasStatus "in_progress" .
    ?occurrence core:hasProgress ?progress .
    FILTER (?progress < 100)
}
ORDER BY DESC(?progress)
```

## API Endpoints

### List All Occurrences
```
GET /api/midjourney/occurrences
```

Returns all job occurrences in chronological order.

### Get Specific Occurrence
```
GET /api/midjourney/occurrences/{task_id}
```

Returns a specific job occurrence by task ID.

### List Workflows
```
GET /api/list-workflows
```

Returns all workflow occurrences.

### Visualize Workflow
```
POST /api/visualize-workflow
{
    "workflow_id": "workflow-id-here"
}
```

Visualizes a workflow with its constituent jobs and occurrences.

## Integration with Agents

### Logging Job Occurrences

```python
from midjourney_integration.client import log_job_occurrence_to_kg

await log_job_occurrence_to_kg(
    kg_manager=_kg_manager,
    task_id=task_id,
    job_type="imagine",
    status="completed",
    prompt="user prompt here",
    model_version="v7",
    start_time="2025-09-25T00:47:14Z",
    end_time="2025-09-25T00:47:45Z",
    progress=100,
    result="https://storage.googleapis.com/bucket/image.png"
)
```

### Enhanced Polling with KG Logging

```python
from midjourney_integration.client import poll_until_complete

final_payload = await poll_until_complete(
    client=_midjourney_client,
    task_id=task_id,
    kg_manager=_kg_manager  # This enables KG logging
)
```

## Workflow Visualization

The occurrent model enables rich workflow visualization through:

1. **Temporal Tracking**: Each occurrence has precise start/end times
2. **Status Tracking**: Real-time status updates for running jobs
3. **Hierarchical Relationships**: Workflows contain jobs, jobs have parent/child relationships
4. **Agent Interactions**: Tracking of agent decisions and interactions
5. **Error Handling**: Detailed error logging for failed occurrences

## Namespace Consistency

### Corrected Namespace Prefixes

- `wf:` → `http://example.org/ontology#` (for workflows)
- `core:` → `http://example.org/core#` (for core classes)
- `mj:` → `http://example.org/midjourney#` (for Midjourney-specific classes)

### SPARQL Query Examples

```sparql
# List all workflows (corrected namespace)
PREFIX wf: <http://example.org/ontology#>
SELECT ?workflow ?theme WHERE {
    ?workflow a wf:Workflow .
    ?workflow wf:hasTheme ?theme .
}
```

```sparql
# List all job occurrences (new occurrent model)
PREFIX core: <http://example.org/core#>
PREFIX mj: <http://example.org/midjourney#>
SELECT ?occurrence ?jobType ?status WHERE {
    ?occurrence a core:JobOccurrent .
    ?occurrence core:hasJobType ?jobType .
    ?occurrence core:hasStatus ?status .
}
```

## Benefits

1. **Persistent History**: All jobs and workflows are permanently tracked
2. **Real-time Monitoring**: Live status updates for running jobs
3. **Rich Metadata**: Detailed information about each occurrence
4. **Agent Accountability**: Track of agent decisions and interactions
5. **Temporal Queries**: Query by time ranges, durations, etc.
6. **Visualization Ready**: Structured data perfect for visualization tools

## Migration Guide

### From Old Model to Occurrent Model

1. **Existing Jobs**: Convert existing job records to JobOccurrent instances
2. **Workflows**: Convert existing workflows to WorkflowOccurrent instances
3. **Agent Interactions**: Convert agent messages to AgentOccurrent instances
4. **Namespace Updates**: Update all queries to use consistent namespaces

### Migration Script

```python
async def migrate_to_occurrent_model():
    """Migrate existing data to the new occurrent model."""

    # Query existing jobs
    old_jobs_query = """
    SELECT ?job ?prompt ?status WHERE {
        ?job a ex:MidjourneyJob .
        ?job ex:hasPrompt ?prompt .
        ?job ex:hasStatus ?status .
    }
    """

    # Convert to new model
    # ... implementation details

    # Query existing workflows
    old_workflows_query = """
    SELECT ?workflow ?theme WHERE {
        ?workflow a ex:Workflow .
        ?workflow ex:hasTheme ?theme .
    }
    """

    # Convert to new model
    # ... implementation details
```

## Future Enhancements

1. **Performance Metrics**: Add performance tracking to occurrences
2. **Resource Usage**: Track computational resources used by jobs
3. **Quality Metrics**: Add quality scores and ratings to job results
4. **Dependency Tracking**: Track dependencies between occurrences
5. **Anomaly Detection**: Detect unusual patterns in occurrence data

## Conclusion

The occurrent model provides a robust foundation for tracking the temporal aspects of the system. By modeling everything as occurrences with clear temporal boundaries and relationships, we can maintain a complete historical record while supporting real-time monitoring and rich visualization capabilities.
