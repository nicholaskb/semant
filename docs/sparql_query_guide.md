# SPARQL Query Guide for Plans

This guide shows how to query plans stored in the Knowledge Graph using SPARQL.

## Methods to Execute SPARQL Queries

### 1. Via HTTP API Endpoint

```bash
# Basic query for all plans
curl -X POST http://localhost:8000/api/kg/sparql-query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "PREFIX plan: <http://example.org/ontology#> PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> SELECT ?plan ?theme ?createdAt WHERE { ?plan rdf:type plan:Plan . ?plan plan:hasTheme ?theme . ?plan plan:createdAt ?createdAt . } ORDER BY DESC(?createdAt) LIMIT 10"
  }'

# Find Marvel-themed plans
curl -X POST http://localhost:8000/api/kg/sparql-query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "PREFIX plan: <http://example.org/ontology#> SELECT ?plan ?theme WHERE { ?plan plan:hasTheme ?theme . FILTER(CONTAINS(LCASE(?theme), \"marvel\")) }"
  }'
```

### 2. Via Python Script

```python
from kg.models.graph_manager import KnowledgeGraphManager

async def query_plans():
    kg = KnowledgeGraphManager()
    await kg.initialize()
    
    query = """
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
    """
    
    results = await kg.query_graph(query)
    return results
```

### 3. Via Agent

```python
from agents.domain.planner_agent import PlannerAgent

async def query_via_agent(planner_agent):
    query = {
        "sparql": """
            PREFIX plan: <http://example.org/ontology#>
            SELECT ?plan ?theme
            WHERE { 
                ?plan plan:hasTheme ?theme .
            }
        """
    }
    
    results = await planner_agent.query_knowledge_graph(query)
    return results
```

## Common SPARQL Queries for Plans

### Get All Plans
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
LIMIT 10
```

### Find Plans by Theme
```sparql
PREFIX plan: <http://example.org/ontology#>

SELECT ?plan ?theme ?createdAt
WHERE {
    ?plan plan:hasTheme ?theme .
    ?plan plan:createdAt ?createdAt .
    FILTER(CONTAINS(LCASE(?theme), "marvel"))
}
ORDER BY DESC(?createdAt)
```

### Get Specific Plan Details
```sparql
PREFIX plan: <http://example.org/ontology#>

SELECT ?predicate ?object
WHERE {
    <http://example.org/plan/plan_20250916_233431> ?predicate ?object .
}
```

### Get Plan with Full JSON Data
```sparql
PREFIX plan: <http://example.org/ontology#>

SELECT ?planData
WHERE {
    <http://example.org/plan/plan_20250916_233431> plan:planData ?planData .
}
```

### Get Steps for a Plan
```sparql
PREFIX plan: <http://example.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?step ?stepNumber ?action ?description ?agent
WHERE {
    ?step rdf:type plan:PlanStep .
    ?step plan:belongsToPlan <http://example.org/plan/plan_20250916_233431> .
    ?step plan:stepNumber ?stepNumber .
    ?step plan:action ?action .
    ?step plan:description ?description .
    ?step plan:assignedAgent ?agent .
}
ORDER BY ?stepNumber
```

### Find Plans Using Specific Agent
```sparql
PREFIX plan: <http://example.org/ontology#>

SELECT DISTINCT ?plan ?theme
WHERE {
    ?plan plan:hasTheme ?theme .
    ?step plan:belongsToPlan ?plan .
    ?step plan:assignedAgent "critic_agent" .
}
```

### Count Plans by Status
```sparql
PREFIX plan: <http://example.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?status (COUNT(?plan) as ?count)
WHERE {
    ?plan rdf:type plan:Plan .
    ?plan plan:status ?status .
}
GROUP BY ?status
ORDER BY DESC(?count)
```

### Find Plans Created Today
```sparql
PREFIX plan: <http://example.org/ontology#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?plan ?theme ?createdAt
WHERE {
    ?plan plan:hasTheme ?theme .
    ?plan plan:createdAt ?createdAt .
    FILTER(?createdAt >= "2025-09-16T00:00:00"^^xsd:dateTime)
}
ORDER BY DESC(?createdAt)
```

### Find Image Generation Plans
```sparql
PREFIX plan: <http://example.org/ontology#>

SELECT ?plan ?theme
WHERE {
    ?plan plan:hasTheme ?theme .
    FILTER(
        CONTAINS(LCASE(?theme), "image") || 
        CONTAINS(LCASE(?theme), "midjourney") ||
        CONTAINS(LCASE(?theme), "portrait") ||
        CONTAINS(LCASE(?theme), "photo")
    )
}
```

### Get Plans with Specific Requirements
```sparql
PREFIX plan: <http://example.org/ontology#>

SELECT ?plan ?theme ?planData
WHERE {
    ?plan plan:hasTheme ?theme .
    ?plan plan:planData ?planData .
    FILTER(CONTAINS(?planData, "dramatic lighting"))
}
```

## Advanced Queries

### Join Plans with Their First Step
```sparql
PREFIX plan: <http://example.org/ontology#>

SELECT ?plan ?theme ?firstStepAction
WHERE {
    ?plan plan:hasTheme ?theme .
    ?step plan:belongsToPlan ?plan .
    ?step plan:stepNumber "1" .
    ?step plan:action ?firstStepAction .
}
```

### Get Plan Execution Timeline
```sparql
PREFIX plan: <http://example.org/ontology#>

SELECT ?plan ?step ?executedAt
WHERE {
    ?step plan:belongsToPlan ?plan .
    ?step plan:executedAt ?executedAt .
}
ORDER BY ?executedAt
```

### Find Related Plans
```sparql
PREFIX plan: <http://example.org/ontology#>

SELECT DISTINCT ?plan1 ?plan2 ?sharedThemeWord
WHERE {
    ?plan1 plan:hasTheme ?theme1 .
    ?plan2 plan:hasTheme ?theme2 .
    FILTER(?plan1 != ?plan2)
    FILTER(CONTAINS(LCASE(?theme1), "marvel") && 
           CONTAINS(LCASE(?theme2), "marvel"))
}
LIMIT 10
```

## SPARQL Query Tips

### 1. Use Prefixes
```sparql
PREFIX plan: <http://example.org/ontology#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
```

### 2. Filter Techniques
```sparql
# Text contains (case-insensitive)
FILTER(CONTAINS(LCASE(?theme), "marvel"))

# Date comparison
FILTER(?createdAt >= "2025-09-16T00:00:00"^^xsd:dateTime)

# Multiple conditions
FILTER(CONTAINS(?theme, "image") || CONTAINS(?theme, "photo"))

# Not equal
FILTER(?status != "cancelled")
```

### 3. Aggregations
```sparql
# Count
SELECT (COUNT(?plan) as ?total)

# Group by
SELECT ?status (COUNT(?plan) as ?count)
GROUP BY ?status

# Having clause
GROUP BY ?agent
HAVING (COUNT(?plan) > 5)
```

### 4. Optional Patterns
```sparql
# Include plans even if they don't have a status
SELECT ?plan ?theme ?status
WHERE {
    ?plan plan:hasTheme ?theme .
    OPTIONAL { ?plan plan:status ?status }
}
```

### 5. Subqueries
```sparql
SELECT ?plan ?theme
WHERE {
    ?plan plan:hasTheme ?theme .
    {
        SELECT ?plan
        WHERE {
            ?step plan:belongsToPlan ?plan .
            ?step plan:assignedAgent "planner" .
        }
    }
}
```

## Parsing Results

### From API Response
```python
import json
import requests

response = requests.post(
    "http://localhost:8000/api/kg/sparql-query",
    json={"query": sparql_query}
)

data = response.json()
results = data["results"]
count = data["count"]

# Process results
for result in results:
    plan_uri = result.get("plan")
    theme = result.get("theme")
    print(f"Plan: {plan_uri}, Theme: {theme}")
```

### Extract Full Plan from JSON
```python
# Query for planData
query = """
PREFIX plan: <http://example.org/ontology#>
SELECT ?planData
WHERE {
    <http://example.org/plan/plan_id> plan:planData ?planData .
}
"""

results = await kg.query_graph(query)
if results and results[0].get("planData"):
    plan = json.loads(results[0]["planData"])
    # Now you have the full plan object
```

## Performance Tips

1. **Use LIMIT** to restrict results
2. **Add indexes** for frequently queried properties
3. **Cache** common queries
4. **Use DISTINCT** to avoid duplicates
5. **Optimize FILTER** conditions (most restrictive first)
6. **Avoid SELECT *** when possible

## Troubleshooting

### No Results?
- Check that plans have been created and stored
- Verify namespace URIs are correct
- Check case sensitivity in filters
- Ensure proper date format for temporal queries

### Query Timeout?
- Add LIMIT clause
- Simplify complex filters
- Break into multiple simpler queries
- Check KG performance metrics

### Syntax Errors?
- Verify PREFIX declarations
- Check bracket matching in WHERE clause
- Ensure proper escaping of quotes in strings
- Validate date/time format

## Example: Complete Workflow

```bash
# 1. Create a plan
curl -X POST http://localhost:8000/api/planner/create-plan \
  -H "Content-Type: application/json" \
  -d '{"theme": "Test workflow", "context": {}}'

# 2. Query for the plan
curl -X POST http://localhost:8000/api/kg/sparql-query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "PREFIX plan: <http://example.org/ontology#> SELECT ?plan ?theme WHERE { ?plan plan:hasTheme ?theme . FILTER(CONTAINS(?theme, \"Test\")) }"
  }'

# 3. Get full plan data
curl -X POST http://localhost:8000/api/kg/sparql-query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "PREFIX plan: <http://example.org/ontology#> SELECT ?planData WHERE { ?plan plan:hasTheme \"Test workflow\" . ?plan plan:planData ?planData . }"
  }'
```

