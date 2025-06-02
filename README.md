# Multi-Agent Knowledge Graph System

A hierarchical multi-agent system with a shared knowledge graph for enterprise intelligence and automation. This system enables autonomous agents to collaborate, share knowledge, and make decisions based on a centralized knowledge graph.

## System Architecture

The system is divided into five major components:

### 1. Agent System (`agents/`)
The core agent framework that powers the entire system.

```
agents/
├── core/              # Base agent classes and interfaces
│   ├── base_agent.py          # Abstract base agent class
│   ├── agent_registry.py      # Agent registration and management
│   ├── capability_types.py    # Capability definitions
│   ├── workflow_manager.py    # Workflow orchestration
│   └── agent_integrator.py    # Agent integration utilities
├── domain/            # Domain-specific agent implementations
├── utils/             # Agent utilities and helpers
└── diary/             # Agent activity logging and history
```

Key features:
- **Asynchronous Message Processing**: All agent operations are asynchronous using Python's asyncio
- **Capability-based Routing**: Messages are routed based on agent capabilities
- **State Management**: Thread-safe state management with asyncio locks
- **Error Handling**: Standardized error handling and recovery mechanisms
- **Activity Logging**: Structured logging with diary entries and knowledge graph integration
- **Workflow Management**: Support for complex multi-agent workflows
- **Agent Recovery**: Automatic recovery mechanisms for failed agents
- **Status Monitoring**: Real-time agent status tracking and notifications

### 2. Knowledge Graph (`kg/`)
The central knowledge storage and query system.

```
kg/
├── models/           # Graph models and managers
├── schemas/          # RDF schemas and ontologies
└── queries/          # SPARQL queries and templates
```

Key features:
- RDF triple storage
- SPARQL query interface
- Schema validation
- Namespace management
- Triple validation

### 3. Integration Layer (`integrations/`)
Handles connections to external systems and services.

```
integrations/
├── api/             # API integrations
├── adapters/        # Data adapters
└── connectors/      # System connectors
```

Key features:
- External API integration
- Data format conversion
- Protocol handling
- Authentication management

### 4. Communication System (`communications/`)
Manages inter-agent communication and message routing.

```
communications/
├── protocols/       # Communication protocols
├── routing/         # Message routing
└── events/          # Event management
```

Key features:
- Message routing
- Protocol handling
- Event management
- Message validation

### 5. Testing & Development (`tests/`, `scripts/`, `utils/`)
Supporting tools and tests for development.

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
└── utils/          # Test utilities

scripts/
├── setup/          # Setup scripts
├── demo/           # Demo scripts
└── tools/          # Development tools
```

Key features:
- Comprehensive test suite
- Development utilities
- Demo applications
- Debugging tools

## Getting Started

### Prerequisites

- Python 3.11+
- Git
- Docker (for Neo4j testing)
- Virtual environment (recommended)

### Installation

```bash
# Clone repository
git clone https://github.com/nicholaskb/semant.git
cd semant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize the knowledge graph
python scripts/init_kg.py
```

### Running the System

```bash
# Start the agent system
python scripts/start_agents.py

# Run a demo workflow
python scripts/run_main_chain.py "Your query here"
```

## Development Workflow

### 1. Agent Development

```python
from agents.core.base_agent import BaseAgent
from agents.core.capability_types import Capability, CapabilityType

class MyCustomAgent(BaseAgent):
    def __init__(self):
        capabilities = {Capability(CapabilityType.DATA_PROCESSING, "1.0")}
        super().__init__("my_agent", "custom", capabilities)
        
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        # Process incoming messages
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"status": "processed"},
            message_type="response"
        )
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        # Update knowledge graph
        pass
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        # Query knowledge graph
        pass
```

### 2. Knowledge Graph Integration

```python
# Update knowledge graph
await agent.update_knowledge_graph({
    "subject": "person:john",
    "predicate": "knows",
    "object": "person:jane"
})

# Query knowledge graph
results = await agent.query_knowledge_graph({
    "sparql": "SELECT ?o WHERE { person:john knows ?o }"
})
```

### 2a. Knowledge Graph Debugging & Verification Guide

This guide shows how to use the knowledge graph for debugging, verification, and SPARQL queries.

#### Example: Debugging Agent Capabilities

```python
import asyncio
from kg.models.graph_manager import KnowledgeGraphManager

async def debug_agent_capabilities():
    kg = KnowledgeGraphManager()
    await kg.initialize()
    # Add test data
    await kg.add_triple(
        subject="http://example.org/agent/EmailProcessor",
        predicate="http://example.org/core#hasCapability",
        object="http://example.org/capability/ProcessEmails"
    )
    await kg.add_triple(
        subject="http://example.org/agent/EmailProcessor",
        predicate="http://example.org/core#configuration",
        object={"max_threads": 5, "timeout": 30}
    )
    await kg.add_triple(
        subject="http://example.org/agent/EmailProcessor",
        predicate="http://example.org/core#status",
        object="active"
    )
    await kg.add_triple(
        subject="http://example.org/agent/DataAnalyzer",
        predicate="http://example.org/core#hasCapability",
        object="http://example.org/capability/AnalyzeData"
    )
    # Query all agents and their capabilities
    query = """
    SELECT ?agent ?capability
    WHERE {
        ?agent <http://example.org/core#hasCapability> ?capability .
    }
    """
    results = await kg.query_graph(query)
    print("All agents and their capabilities:")
    for result in results:
        print(f"Agent: {result['agent']}, Capability: {result['capability']}")
    # Query configuration for a specific agent
    config_query = """
    SELECT ?config
    WHERE {
        <http://example.org/agent/EmailProcessor> <http://example.org/core#configuration> ?config .
    }
    """
    config_results = await kg.query_graph(config_query)
    print("EmailProcessor configuration:")
    for result in config_results:
        print(f"Config: {result['config']}")
    # Add validation rule to ensure all agents have capabilities
    kg.add_validation_rule({
        "type": "required_property",
        "subject_type": "http://example.org/agent/Agent",
        "property": "http://example.org/core#hasCapability"
    })
    validation_results = await kg.validate_graph()
    print("Validation results:")
    print(f"Total subjects: {validation_results['subjects']}")
    print(f"Total predicates: {validation_results['predicates']}")
    print(f"Total objects: {validation_results['objects']}")
    print(f"Validation errors: {validation_results['validation_errors']}")
    print(f"Security violations: {validation_results['security_violations']}")
    # Export the graph for inspection
    turtle_data = await kg.export_graph(format='turtle')
    print("Graph in Turtle format:")
    print(turtle_data)
    await kg.shutdown()

if __name__ == "__main__":
    asyncio.run(debug_agent_capabilities())
```

#### Typical Output
```
All agents and their capabilities:
Agent: http://example.org/agent/EmailProcessor, Capability: http://example.org/capability/ProcessEmails
Agent: http://example.org/agent/DataAnalyzer, Capability: http://example.org/capability/AnalyzeData

EmailProcessor configuration:
Config: {"max_threads": 5, "timeout": 30}

Validation results:
Total subjects: 2
Total predicates: 3
Total objects: 4
Validation errors: []
Security violations: []

Graph in Turtle format:
@prefix : <http://example.org/core#> .
@prefix agent: <http://example.org/agent/> .

agent:DataAnalyzer :hasCapability <http://example.org/capability/AnalyzeData> .

agent:EmailProcessor :configuration "{\"max_threads\": 5, \"timeout\": 30}" ;
    :hasCapability <http://example.org/capability/ProcessEmails> ;
    :status "active" .
```

#### How to Use
- **SPARQL Queries:** Use `await kg.query_graph(query)` to run SPARQL and inspect results.
- **Validation:** Add rules and run `await kg.validate_graph()` to check for missing or invalid data.
- **Export:** Use `await kg.export_graph(format='turtle')` to get a human-readable snapshot.
- **Debugging:** Print and inspect results to verify your hypotheses about the graph state.

For more advanced usage, see the `docs/technical_debugging.md` Knowledge Graph Usage Tutorial.

### 3. Message Handling

```python
message = AgentMessage(
    sender="sender_id",
    recipient="recipient_id",
    content={
        "required_capability": CapabilityType.DATA_PROCESSING,
        "data": {"key": "value"}
    }
)
```

## Testing and Development

The system includes a comprehensive testing and development infrastructure to ensure code quality and maintainability.

### Test Structure

```
tests/
├── unit/              # Unit tests
│   ├── agents/        # Agent-specific tests
│   ├── kg/           # Knowledge graph tests
│   └── integration/  # Integration layer tests
├── integration/       # Integration tests
│   ├── workflows/    # Workflow tests
│   ├── performance/  # Performance tests
│   └── security/     # Security tests
├── utils/            # Test utilities
│   ├── mocks/        # Mock implementations
│   ├── generators/   # Test data generators
│   └── benchmarks/   # Performance benchmarks
└── agents/           # Agent-specific tests
    ├── core/         # Core agent tests
    ├── domain/       # Domain-specific tests
    └── integration/  # Agent integration tests
```

### Test Categories

1. **Unit Tests**
   - Core agent functionality
     - Agent registration and initialization
     - Message processing and routing
     - Capability management
     - Knowledge graph integration
   - Knowledge graph operations
     - Triple addition and validation
     - Graph updates and queries
     - Semantic relationship handling
     - Complex query patterns
   - Integration layer
     - API integration verification
     - Authentication management
     - Protocol handling
     - Error recovery

2. **Integration Tests**
   - Multi-agent workflows
     - Agent communication patterns
     - Message routing verification
     - Capability-based interactions
     - Error handling scenarios
   - Knowledge graph integration
     - Ontology loading and validation
     - Schema evolution testing
     - Query performance metrics
     - Cache effectiveness
   - External system integration
     - API connectivity
     - Data transformation
     - Protocol compatibility
     - Security validation

3. **Test Utilities**
   - Mock implementations
     - Configurable capabilities
     - Message history tracking
     - Knowledge graph interaction simulation
     - Error injection capabilities
   - Test data generators
     - Synthetic knowledge graph data
     - Complex relationship patterns
     - Performance test scenarios
     - Security test cases
   - Performance tools
     - Query execution timing
     - Cache hit/miss analysis
     - Resource utilization tracking
     - Scalability testing

### Development Tools

1. **Scripts**
   - Knowledge graph initialization
     - Schema loading
     - Sample data population
     - Validation checks
     - Performance optimization
   - Agent system startup
     - Component initialization
     - Dependency verification
     - Configuration validation
     - Health checks
   - Demo workflows
     - Example scenarios
     - Integration demonstrations
     - Performance showcases
     - Security examples

2. **Debugging Tools**
   - Graph visualization
     - Relationship mapping
     - Query result display
     - Performance metrics
     - Error highlighting
   - Message flow tracking
     - Communication patterns
     - Routing decisions
     - Error propagation
     - Performance bottlenecks
   - Performance profiling
     - Query execution analysis
     - Resource utilization
     - Cache effectiveness
     - Bottleneck identification

3. **Development Utilities**
   - Graph database utilities
     - Schema management
     - Data validation
     - Performance optimization
     - Security configuration
   - TTL validation
     - Schema verification
     - Ontology consistency
     - Relationship validation
     - Performance impact analysis
   - Code review tools
     - Style checking
     - Type verification
     - Documentation validation
     - Security scanning

### Best Practices

1. **Testing**
   - Write comprehensive tests
     - Unit test coverage
     - Integration test scenarios
     - Performance benchmarks
     - Security validation
   - Use appropriate test types
     - Unit tests for components
     - Integration tests for workflows
     - Performance tests for optimization
     - Security tests for validation
   - Maintain test coverage
     - Regular test execution
     - Coverage reporting
     - Performance monitoring
     - Security scanning

2. **Development**
   - Follow coding standards
     - Style guidelines
     - Type hints
     - Documentation
     - Error handling
   - Use version control
     - Feature branches
     - Pull requests
     - Code review
     - Documentation updates
   - Monitor performance
     - Query execution
     - Resource utilization
     - Cache effectiveness
     - Scalability testing

3. **Maintenance**
   - Regular updates
     - Code modifications
     - Configuration changes
     - Dependency updates
     - Security patches
   - Bug fixes
     - Issue tracking
     - Root cause analysis
     - Solution implementation
     - Verification testing
   - Performance optimization
     - Query optimization
     - Resource management
     - Cache tuning
     - Scalability improvements

### Monitoring and Logging

1. **Test Monitoring**
   - Test execution tracking
     - Success/failure rates
     - Performance metrics
     - Coverage statistics
     - Security validation
   - Performance monitoring
     - Query execution time
     - Resource utilization
     - Cache effectiveness
     - Bottleneck identification

2. **Development Logging**
   - Change logging
     - Code modifications
     - Configuration changes
     - Dependency updates
     - Security patches
   - Error logging
     - Test failures
     - Performance issues
     - Security vulnerabilities
     - Integration problems

### Troubleshooting

1. **Common Issues**
   - Test failures
     - Unit test failures
     - Integration test issues
     - Performance test problems
     - Security test violations
   - Performance issues
     - Query performance
     - Resource utilization
     - Cache effectiveness
     - Scalability problems

2. **Debugging Steps**
   - Test analysis
     - Failure investigation
     - Performance profiling
     - Security validation
     - Integration verification
   - Code review
     - Implementation issues
     - Configuration problems
     - Dependency conflicts
     - Security vulnerabilities

3. **Recovery Actions**
   - Test fixes
     - Unit test corrections
     - Integration test updates
     - Performance optimizations
     - Security enhancements
   - System updates
     - Code modifications
     - Configuration changes
     - Dependency updates
     - Security patches

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Update documentation
6. Submit pull request

## License

MIT License - see LICENSE file for details

## Self-Extending Capabilities

The system is designed with self-extending capabilities that allow it to evolve and adapt over time. This is achieved through a combination of knowledge graph-based learning and agent-based architecture.

### Key Features

1. **Knowledge Graph Evolution**
   - Dynamic schema extension through RDF/OWL
   - Automatic relationship discovery
   - Pattern recognition in agent interactions
   - Semantic inference capabilities

2. **Agent Capability Discovery**
   - Automatic capability detection
   - Pattern-based learning
   - Relationship inference
   - Capability composition

3. **Communication Pattern Learning**
   - Message flow analysis
   - Interaction pattern recognition
   - Protocol optimization
   - Capability-based routing

### Getting Started with System Evolution

1. **Understanding the Knowledge Graph**
   - Review the core ontology in `kg/schemas/core.ttl`
   - Study the relationship patterns
   - Learn about capability definitions
   - Understand evolution rules

2. **Contributing to Evolution**
   - Follow the evolution guidelines
   - Implement new capabilities
   - Extend the knowledge graph
   - Test thoroughly

3. **Monitoring Evolution**
   - Track evolution metrics
   - Monitor system stability
   - Review performance
   - Check consistency

### Best Practices

1. **Evolution Management**
   - Follow versioning guidelines
   - Maintain backward compatibility
   - Document changes
   - Test thoroughly

2. **Knowledge Graph Maintenance**
   - Validate changes
   - Check consistency
   - Update documentation
   - Monitor performance

3. **System Health**
   - Monitor components
   - Track performance
   - Check resource usage
   - Detect errors

## Communication System

The system implements a robust communication infrastructure that enables seamless interaction between agents and components. The communication system is designed to be flexible, scalable, and maintainable.

### Key Features

1. **Message Handling**
   - Structured message format
   - Type-based message processing
   - Content validation
   - Error handling

2. **Message Routing**
   - Direct routing to specific agents
   - Capability-based routing
   - Broadcast messaging
   - Dynamic routing rules

3. **Event Management**
   - Event subscription system
   - Notification handling
   - Event queue management
   - System health monitoring

4. **Security**
   - Message validation
   - Capability verification
   - Error recovery
   - Access control

### Getting Started

1. **Creating Messages**
   ```python
   # Basic message
   message = AgentMessage(
       sender="agent_1",
       recipient="agent_2",
       content={"data": "value"},
       message_type="request"
   )
   ```

2. **Routing Messages**
   ```python
   # Direct routing
   response = await registry.route_message(message)
   
   # Capability-based routing
   responses = await registry.route_message_by_capability(
       message,
       CapabilityType.DATA_PROCESSING
   )
   ```

3. **Handling Events**
   ```python
   # Subscribe to events
   await registry.subscribe_to_notifications(
       "capability_change",
       handle_capability_change
   )
   ```

### Best Practices

1. **Message Design**
   - Use clear message types
   - Structure content consistently
   - Include necessary metadata
   - Document message formats

2. **Routing Strategy**
   - Choose appropriate routing method
   - Handle routing errors
   - Monitor message flow
   - Optimize performance

3. **Event Management**
   - Subscribe to relevant events
   - Handle notifications properly
   - Manage event queues
   - Monitor system health

4. **Error Handling**
   - Validate messages
   - Handle errors gracefully
   - Implement recovery
   - Log issues

### Monitoring and Logging

The system includes comprehensive monitoring and logging capabilities:

1. **Message Tracking**
   - Message flow monitoring
   - Performance metrics
   - Error tracking
   - System health checks

2. **Logging**
   - Message logging
   - Error logging
   - Performance logging
   - System state logging

### Troubleshooting

Common issues and their solutions:

1. **Message Routing**
   - Verify message format
   - Check recipient availability
   - Validate capabilities
   - Monitor routing rules

2. **Event Processing**
   - Check event subscriptions
   - Verify notification handlers
   - Monitor event queue
   - Review system logs

3. **Error Recovery**
   - Implement retry logic
   - Handle timeouts
   - Manage deadlocks
   - Restore system state

# Data Engineering Challenges

## Overview

This README provides an overview of the data engineering challenges associated with the project. It includes references to key documents and resources that outline the challenges and requirements.

## Key Documents

- **Data Engineering Challenge: Self-Assembling Multi-Agent System with a Knowledge Graph**  
  This document outlines the challenges and requirements for building a self-assembling multi-agent system with a knowledge graph. It provides detailed insights into the project's goals and technical specifications.

- **System Design Feedback and Recommendations**  
  This document contains feedback and recommendations related to the system design, which may be relevant to understanding the data engineering challenges.

## Additional Resources

- **Current Data Challenge**  
  Refer to `current_data_challenge.txt` for the latest updates and ongoing challenges in the data engineering domain.

## Conclusion

This README serves as a starting point for understanding the data engineering challenges associated with the project. For more detailed information, refer to the documents listed above.
