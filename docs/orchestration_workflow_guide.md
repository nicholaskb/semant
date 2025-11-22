# Comprehensive Orchestration Workflow Guide

## Overview

This guide describes a sophisticated 7-step multi-agent orchestration workflow that takes a text file as input and orchestrates a complete plan creation, review, execution, and analysis cycle with full Knowledge Graph integration.

## The 7-Step Orchestration Process

### Step 1: Create Workflow from Text File
- **Input**: Text file with requirements
- **Process**: Planner agent analyzes text and creates structured plan
- **Output**: Workflow ID, Plan stored in KG
- **KG Storage**: Plan and all steps as RDF triples

### Step 2: Email Notification
- **Trigger**: Plan creation completion
- **Process**: Format plan and send via email for human review
- **Output**: Email with approve/reject instructions
- **KG Update**: Email timestamp and pending_review status

### Step 3: Knowledge Graph Visualization
- **Process**: Create comprehensive KG representation
- **Output**: Visualization URI and SPARQL queries
- **Purpose**: Allow inspection of plan structure in KG
- **Queryable**: All plan details via SPARQL

### Step 4: Multi-Agent Review
- **Reviewers**: Code review agents, analysis agents, etc.
- **Process**: Each agent evaluates the plan
- **Output**: Reviews, recommendations, consensus
- **KG Storage**: All reviews and commentary

### Step 5: Execution Validation
- **Checks**: Agent availability, dependencies, circular refs
- **Process**: Validate execution can succeed
- **Output**: Ready/not ready decision
- **KG Update**: Validation results and readiness status

### Step 6: Monitored Execution
- **Process**: Execute each plan step with monitoring
- **Tracking**: Start/end times, results, errors
- **Output**: Execution results for each step
- **KG Storage**: Complete execution history

### Step 7: Post-Execution Analysis
- **Process**: Analyze execution, gather agent commentary
- **Metrics**: Success rate, timing, performance
- **Output**: Analysis report with agent insights
- **KG Storage**: Analysis and commentary

## API Endpoints

### Create Workflow
```bash
POST /api/orchestration/create-workflow
{
    "text_file": "/path/to/requirements.txt",
    "user_email": "user@example.com",
    "workflow_name": "My Complex Workflow"
}
```

### Execute Step
```bash
POST /api/orchestration/execute-step
{
    "workflow_id": "workflow_20250917_120000_abc123",
    "step": "send_email|visualize|review|validate|execute|analyze",
    "user_email": "user@example.com"  # For send_email step
}
```

## Testing the Workflow

### Quick Test
```bash
# 1. Start the server
python3 main.py

# 2. Run the test script
python3 test_orchestration_workflow.py
```

### Manual Testing
```python
import requests

# Create workflow
response = requests.post(
    "http://localhost:8000/api/orchestration/create-workflow",
    json={
        "text_file": "requirements.txt",
        "user_email": "test@example.com",
        "workflow_name": "Test Workflow"
    }
)
workflow_id = response.json()["workflow_id"]

# Execute each step
for step in ["send_email", "visualize", "review", "validate", "execute", "analyze"]:
    response = requests.post(
        "http://localhost:8000/api/orchestration/execute-step",
        json={"workflow_id": workflow_id, "step": step}
    )
    print(f"{step}: {response.json()}")
```

## Knowledge Graph Schema

### Workflow Entities
```turtle
<http://example.org/workflow/{id}> 
    a ontology:Workflow ;
    ontology:hasPlan <http://example.org/plan/{plan_id}> ;
    ontology:status "created|pending_review|executing|completed" ;
    ontology:userEmail "user@example.com" ;
    ontology:createdAt "2025-09-17T12:00:00" .
```

### Review Entities
```turtle
<http://example.org/review/{workflow_id}/{agent_id}>
    a ontology:Review ;
    ontology:reviewedBy agent:{agent_id} ;
    ontology:reviewOf workflow:{id} ;
    ontology:reviewContent "{JSON}" ;
    ontology:recommendation "approve|reject|revise" .
```

### Execution Entities
```turtle
<http://example.org/execution/{workflow_id}/step/{n}>
    a ontology:ExecutionStep ;
    ontology:startedAt "timestamp" ;
    ontology:completedAt "timestamp" ;
    ontology:status "completed|failed" ;
    ontology:result "{JSON}" .
```

### Analysis Entities
```turtle
<http://example.org/analysis/{workflow_id}>
    a ontology:Analysis ;
    ontology:analyzedAt "timestamp" ;
    ontology:analysisData "{JSON}" ;
    ontology:successRate "0.95" .
```

## SPARQL Queries

### Get Workflow Status
```sparql
PREFIX wf: <http://example.org/ontology#>
SELECT ?status ?plan ?email
WHERE {
    <http://example.org/workflow/{id}> wf:status ?status ;
                                         wf:hasPlan ?plan ;
                                         wf:userEmail ?email .
}
```

### Get All Reviews
```sparql
PREFIX wf: <http://example.org/ontology#>
SELECT ?reviewer ?recommendation ?content
WHERE {
    ?review wf:reviewOf <http://example.org/workflow/{id}> ;
            wf:reviewedBy ?reviewer ;
            wf:recommendation ?recommendation ;
            wf:reviewContent ?content .
}
```

### Get Execution History
```sparql
PREFIX ex: <http://example.org/ontology#>
SELECT ?step ?status ?startedAt ?completedAt
WHERE {
    ?step ex:partOfExecution ?execution .
    ?execution ex:executesWorkflow <http://example.org/workflow/{id}> .
    ?step ex:status ?status ;
          ex:startedAt ?startedAt ;
          ex:completedAt ?completedAt .
}
ORDER BY ?startedAt
```

### Get Agent Commentary
```sparql
PREFIX an: <http://example.org/ontology#>
SELECT ?agent ?commentary ?timestamp
WHERE {
    ?comment an:commentOn <http://example.org/workflow/{id}> ;
             an:commentBy ?agent ;
             an:commentText ?commentary ;
             an:commentedAt ?timestamp .
}
```

## Configuration

### Email Settings
```python
# In orchestration_workflow.py
self.email_integration = EmailIntegration(use_real_email=True)  # Set to True for real emails
```

### Review Agents
```python
# Add custom review agents
review_agents = [
    CodeReviewAgent("code_reviewer"),
    SecurityAgent("security_reviewer"),
    PerformanceAgent("performance_reviewer")
]
workflow = OrchestrationWorkflow(planner, review_agents)
```

## Requirements File Format

The text file should contain:
- **Project name and description**
- **Objectives** (what to accomplish)
- **Requirements** (technical specifications)
- **Constraints** (limitations, deadlines)
- **Deliverables** (expected outputs)

Example:
```text
Project: Data Processing Pipeline

Objectives:
- Process incoming data streams
- Transform and validate data
- Store in data warehouse

Requirements:
- Handle 100K records/hour
- < 5 minute latency
- 99.9% uptime

Deliverables:
- Working pipeline
- Documentation
- Monitoring dashboard
```

## Use Cases

### 1. Software Development Projects
- Parse requirements document
- Generate development plan
- Get team review and approval
- Execute development steps
- Analyze results

### 2. Data Pipeline Creation
- Define data sources and transformations
- Plan ETL workflow
- Validate data quality checks
- Execute pipeline creation
- Monitor performance

### 3. Research Projects
- Parse research proposal
- Plan experiments and analysis
- Review methodology
- Execute research steps
- Analyze and document findings

### 4. Infrastructure Deployment
- Parse infrastructure requirements
- Plan deployment steps
- Security and compliance review
- Execute deployment
- Post-deployment verification

## Troubleshooting

### Workflow Creation Fails
- Check text file exists and is readable
- Verify Planner agent is available
- Check KG is initialized

### Email Not Sending
- Set `use_real_email=True` in EmailIntegration
- Configure EMAIL_SENDER and EMAIL_PASSWORD in .env
- Check email formatting

### Review Agents Not Available
- Ensure review agents are properly initialized
- Check agent registry has required agents
- Verify agent capabilities match requirements

### Execution Validation Fails
- Check all required agents exist
- Verify no circular dependencies
- Ensure input/output mappings are correct

### KG Queries Return Empty
- Verify workflow was created successfully
- Check SPARQL syntax
- Ensure proper namespace prefixes

## Advanced Features

### Custom Review Logic
```python
class CustomReviewAgent(BaseAgent):
    async def review_plan(self, plan):
        # Custom review logic
        if self.check_compliance(plan):
            return {"recommendation": "approve"}
        return {"recommendation": "revise", "issues": [...]}
```

### Execution Hooks
```python
# Add pre/post execution hooks
async def pre_execution_hook(workflow_id):
    # Setup resources
    pass

async def post_execution_hook(workflow_id, results):
    # Cleanup and reporting
    pass
```

### Parallel Execution
```python
# Execute independent steps in parallel
async def execute_parallel_steps(steps):
    tasks = [execute_step(s) for s in steps if not s.dependencies]
    results = await asyncio.gather(*tasks)
    return results
```

## Performance Considerations

- **KG Queries**: Use LIMIT and indexes for large datasets
- **Email**: Batch notifications for multiple workflows
- **Execution**: Parallelize independent steps
- **Reviews**: Cache review results for similar plans
- **Analysis**: Aggregate metrics incrementally

## Security

- **Authentication**: Protect API endpoints with tokens
- **Authorization**: Check user permissions for workflows
- **Data Privacy**: Encrypt sensitive plan content
- **Audit Trail**: Log all actions in KG
- **Input Validation**: Sanitize text file content

## Conclusion

This orchestration workflow provides a complete framework for converting text requirements into executed, monitored, and analyzed workflows with full Knowledge Graph integration. The system ensures transparency, traceability, and multi-agent collaboration throughout the entire process.
