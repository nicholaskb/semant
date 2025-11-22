# Planner Knowledge Graph Integration

## Overview

The Planner agent can now create structured plans and store them directly in the Knowledge Graph as RDF triples. This enables:

- **Persistent Plan Storage**: Plans are stored as semantic data that can be queried
- **Reusable Workflows**: Plans can be retrieved and executed multiple times
- **Plan Versioning**: Track plan evolution and execution history
- **SPARQL Queries**: Query plans by theme, status, agent, or any other property
- **Multi-Agent Orchestration**: Plans coordinate multiple agents for complex workflows

## Architecture

### Plan Structure
```json
{
  "id": "plan_20250917_120000",
  "theme": "Marvel superheroes image generation workflow",
  "created_at": "2025-09-17T12:00:00",
  "created_by": "planner",
  "context": {
    "count": 5,
    "image_urls": ["..."],
    "requirements": "..."
  },
  "steps": [
    {
      "step": 1,
      "action": "analyze_theme",
      "description": "Analyze the theme to identify key visual elements",
      "agent": "planner",
      "output": "theme_analysis"
    },
    // ... more steps
  ],
  "status": "created"
}
```

### RDF Triple Storage

Plans are stored as RDF triples with the following ontology:

```turtle
@prefix plan: <http://example.org/ontology#> .
@prefix agent: <http://example.org/agent/> .

# Plan node
<http://example.org/plan/plan_20250917_120000> 
    a plan:Plan ;
    plan:hasTheme "Marvel superheroes image generation workflow" ;
    plan:createdBy agent:planner ;
    plan:createdAt "2025-09-17T12:00:00" ;
    plan:status "created" ;
    plan:planData "{...}" .  # Full JSON stored for quick retrieval

# Step nodes
<http://example.org/plan/plan_20250917_120000/step/1>
    a plan:PlanStep ;
    plan:belongsToPlan <http://example.org/plan/plan_20250917_120000> ;
    plan:stepNumber "1" ;
    plan:action "analyze_theme" ;
    plan:description "..." ;
    plan:assignedAgent "planner" .
```

## API Endpoints

### 1. Create Plan
```bash
POST /api/planner/create-plan
Content-Type: application/json

{
  "theme": "Marvel superheroes image generation workflow",
  "context": {
    "count": 5,
    "image_urls": ["https://example.com/face1.jpg"],
    "requirements": "High quality cinematic portraits",
    "version": "v7"
  }
}
```

Response:
```json
{
  "id": "plan_20250917_120000",
  "theme": "Marvel superheroes image generation workflow",
  "created_at": "2025-09-17T12:00:00",
  "steps": [...],
  "kg_stored": true
}
```

### 2. Retrieve Plan
```bash
GET /api/planner/get-plan/{plan_id}
```

### 3. List Plans
```bash
GET /api/planner/list-plans?theme_filter=image
```

Response:
```json
{
  "plans": [
    {
      "id": "plan_20250917_120000",
      "theme": "Marvel superheroes image generation workflow",
      "created_at": "2025-09-17T12:00:00",
      "status": "created"
    }
  ],
  "count": 1
}
```

### 4. Execute Plan Step
```bash
POST /api/planner/execute-step
Content-Type: application/json

{
  "plan_id": "plan_20250917_120000",
  "step_number": 1
}
```

## Plan Types

### Image Generation Plans
Automatically created when theme contains "midjourney" or "image":
1. Analyze theme
2. Generate prompts
3. Refine prompts
4. Critique prompts
5. Finalize prompts
6. Submit jobs

### Research Plans
Created for themes containing "research":
1. Define scope
2. Gather information
3. Analyze data
4. Create report

### Generic Workflow Plans
Default for other themes:
1. Analyze requirements
2. Design solution
3. Implement
4. Review
5. Finalize

## Testing

Run the test script to verify the integration:
```bash
python3 test_planner_kg_integration.py
```

This will:
1. Create a plan and store it in KG
2. Retrieve the plan by ID
3. Execute a plan step
4. List all plans
5. Filter plans by theme

## SPARQL Queries

### Find All Plans
```sparql
PREFIX plan: <http://example.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?plan ?theme ?createdAt ?status
WHERE {
  ?plan rdf:type plan:Plan .
  ?plan plan:hasTheme ?theme .
  ?plan plan:createdAt ?createdAt .
  ?plan plan:status ?status .
}
ORDER BY DESC(?createdAt)
```

### Find Plans by Theme
```sparql
PREFIX plan: <http://example.org/ontology#>

SELECT ?plan ?theme
WHERE {
  ?plan plan:hasTheme ?theme .
  FILTER(CONTAINS(LCASE(?theme), "marvel"))
}
```

### Find Steps for a Plan
```sparql
PREFIX plan: <http://example.org/ontology#>

SELECT ?step ?action ?agent
WHERE {
  ?step plan:belongsToPlan <http://example.org/plan/plan_20250917_120000> .
  ?step plan:action ?action .
  ?step plan:assignedAgent ?agent .
}
ORDER BY ?step
```

### Find Plans Using Specific Agent
```sparql
PREFIX plan: <http://example.org/ontology#>

SELECT DISTINCT ?plan ?theme
WHERE {
  ?plan rdf:type plan:Plan .
  ?plan plan:hasTheme ?theme .
  ?step plan:belongsToPlan ?plan .
  ?step plan:assignedAgent "critic_agent" .
}
```

## Use Cases

### 1. Reusable Image Generation Workflows
Create a plan once for a specific theme (e.g., "cyberpunk portraits"), then execute it multiple times with different reference images.

### 2. Complex Multi-Agent Pipelines
Design workflows that coordinate multiple specialized agents (analysis, synthesis, critique, judgment) in a specific sequence.

### 3. Workflow Versioning
Track how plans evolve over time, compare different versions, and maintain an audit trail of executions.

### 4. Template Library
Build a library of plan templates in the KG that can be customized for specific needs.

### 5. Execution History
Query the KG to find:
- Which plans have been executed
- When steps were executed
- Success/failure rates
- Performance metrics

## Integration with Existing Systems

### Midjourney Integration
Plans can include steps that:
- Generate prompts using the theme
- Submit images to Midjourney
- Process results
- Store outputs in KG

### Agent Coordination
Plans automatically route messages to appropriate agents based on step assignments.

### Knowledge Graph Benefits
- Plans are semantic data, not just JSON blobs
- Can link plans to other entities (users, projects, results)
- Query across multiple dimensions
- Build knowledge networks around workflows

## Future Enhancements

1. **Plan Templates**: Pre-built plans for common workflows
2. **Conditional Steps**: If/then logic in plan execution
3. **Parallel Execution**: Steps that can run simultaneously
4. **Plan Composition**: Combine smaller plans into larger workflows
5. **Execution Monitoring**: Real-time tracking of plan progress
6. **Plan Optimization**: Learn from execution history to improve plans
7. **Visual Plan Editor**: UI for creating and modifying plans

## Troubleshooting

### Plan Not Stored in KG
- Check that Knowledge Graph is initialized
- Verify Planner has KG access
- Check server logs for KG errors

### Plan Retrieval Fails
- Ensure plan ID is correct
- Check that KG query endpoint is configured
- Verify plan was successfully stored

### Step Execution Errors
- Confirm target agent exists and is registered
- Check that step number is valid
- Review agent message handling

## Example: Complete Workflow

```python
# Create a themed image generation plan
plan = create_plan(
    theme="Cyberpunk character portraits",
    context={
        "count": 10,
        "style": "neon-lit, futuristic",
        "image_urls": ["face1.jpg", "face2.jpg"]
    }
)

# Execute the plan
for step in plan["steps"]:
    result = execute_step(plan["id"], step["step"])
    print(f"Step {step['step']}: {result['status']}")

# Query results from KG
results = query_kg(f"""
    SELECT ?output
    WHERE {{
        <http://example.org/plan/{plan['id']}/step/6> 
        plan:output ?output .
    }}
""")
```

## Security Considerations

- Plans are stored with creator attribution
- Access control can be implemented via KG security
- Sensitive context data should be encrypted
- Plan execution requires appropriate permissions

## Performance

- Plans are cached in KG for fast retrieval
- Step execution is asynchronous
- SPARQL queries are optimized with indexes
- Large plans (100+ steps) may require pagination

## Conclusion

The Planner-KG integration transforms the Planner from a stateless coordinator into a powerful workflow engine with persistent, queryable plan storage. This enables sophisticated multi-agent orchestrations while maintaining full semantic traceability through the Knowledge Graph.

