# Instructions for Using `kg_debug_example.py`

## Overview
This script demonstrates how to interact with the `KnowledgeGraphManager` to initialize a knowledge graph, add test data, query the graph, and validate it. It serves as a practical example for debugging and testing knowledge graph functionality.

## Prerequisites
- Ensure you have the required dependencies installed (e.g., `rdflib`, `asyncio`).
- Familiarize yourself with the `KnowledgeGraphManager` class and its methods.

## Step-by-Step Instructions

### 1. **Initialize the Knowledge Graph**
- The script starts by initializing the `KnowledgeGraphManager`:
  ```python
  kg = KnowledgeGraphManager()
  await kg.initialize()
  ```
- This step sets up the knowledge graph for further operations.

### 2. **Add Test Data**
- The script adds test data to the knowledge graph using the `add_triple` method:
  ```python
  await kg.add_triple(
      subject="http://example.org/agent/EmailProcessor",
      predicate="http://example.org/core#hasCapability",
      object="http://example.org/capability/ProcessEmails"
  )
  ```
- Repeat this step to add more triples as needed. Each triple represents a relationship between a subject, predicate, and object in the knowledge graph.

### 3. **Query the Knowledge Graph**
- The script demonstrates how to query the knowledge graph using SPARQL:
  ```python
  query = """
  SELECT ?agent ?capability
  WHERE {
      ?agent <http://example.org/core#hasCapability> ?capability .
  }
  """
  results = await kg.query_graph(query)
  ```
- This query retrieves all agents and their capabilities. Modify the query to suit your specific needs.

### 4. **Check Configuration**
- The script shows how to check the configuration of a specific agent:
  ```python
  config_query = """
  SELECT ?config
  WHERE {
      <http://example.org/agent/EmailProcessor> <http://example.org/core#configuration> ?config .
  }
  """
  config_results = await kg.query_graph(config_query)
  ```
- This query retrieves the configuration of the `EmailProcessor` agent. Adjust the subject and predicate as needed.

### 5. **Validate the Knowledge Graph**
- The script adds a validation rule to ensure all agents have capabilities:
  ```python
  kg.add_validation_rule({
      "type": "required_property",
      "subject_type": "http://example.org/agent/Agent",
      "property": "http://example.org/core#hasCapability"
  })
  ```
- Run validation to check for errors:
  ```python
  validation_results = await kg.validate_graph()
  ```
- Review the validation results to identify any issues.

### 6. **Get Metrics**
- The script retrieves metrics about the knowledge graph:
  ```python
  print(f"Query count: {kg.metrics['query_count']}")
  print(f"Cache hits: {kg.metrics['cache_hits']}")
  print(f"Cache misses: {kg.metrics['cache_misses']}")
  ```
- These metrics provide insights into the performance and usage of the knowledge graph.

### 7. **Export the Knowledge Graph**
- The script exports the knowledge graph in Turtle format:
  ```python
  turtle_data = await kg.export_graph(format='turtle')
  print(turtle_data)
  ```
- This step allows you to inspect the knowledge graph in a human-readable format.

### 8. **Clean Up**
- Finally, the script shuts down the knowledge graph:
  ```python
  await kg.shutdown()
  ```
- This step ensures that all resources are properly released.

## Example Outputs

### Query Results
```
All agents and their capabilities:
Agent: http://example.org/agent/EmailProcessor, Capability: http://example.org/capability/ProcessEmails
Agent: http://example.org/agent/DataAnalyzer, Capability: http://example.org/capability/AnalyzeData
```

### Configuration Results
```
EmailProcessor configuration:
Config: {'max_threads': 5, 'timeout': 30}
```

### Validation Results
```
Validation results:
Total subjects: 2
Total predicates: 3
Total objects: 3
Validation errors: []
Security violations: []
```

### Graph Metrics
```
Graph metrics:
Query count: 2
Cache hits: 0
Cache misses: 2
```

### Exported Graph (Turtle Format)
```
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://example.org/agent/EmailProcessor> <http://example.org/core#hasCapability> <http://example.org/capability/ProcessEmails> .
<http://example.org/agent/EmailProcessor> <http://example.org/core#configuration> {"max_threads": 5, "timeout": 30} .
<http://example.org/agent/EmailProcessor> <http://example.org/core#status> "active" .
<http://example.org/agent/DataAnalyzer> <http://example.org/core#hasCapability> <http://example.org/capability/AnalyzeData> .
```

## Conclusion
By following these instructions, you can effectively use `kg_debug_example.py` to interact with the `KnowledgeGraphManager`, add test data, query the knowledge graph, and validate it. This script serves as a practical guide for debugging and testing knowledge graph functionality. 