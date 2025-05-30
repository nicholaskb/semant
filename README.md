# Multi-Agent Knowledge Graph System

A hierarchical multi-agent system with a shared knowledge graph for enterprise intelligence and automation.

## System Architecture

### Core Components
- **Knowledge Graph Layer**: Central shared memory using RDF/TTL format
- **Agent Hierarchy**: Master Orchestrator, CEO Agent, and specialized Domain Agents
- **Communication Protocol**: Graph-based messaging with structured feedback logging

### Agent Types
1. **Top Level**
   - Master Orchestrator Agent
   - CEO Agent (executive oversight)
   - Judge Agent (system validation)

2. **Domain Agents**
   - Corporate Knowledge Agent
   - Diary Agent
   - Finance Agent
   - Coaching Agent
   - Intelligence Agent
   - Developer Agent
   - Knowledge Graph Consultant
   - OpenAI Knowledge Graph Engineer
   - Knowledge Graph VP Lead

## Setup and Installation

1. Clone the repository:
```bash
git clone https://github.com/nicholaskb/semant.git
cd semant
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the knowledge graph:
```bash
python scripts/init_kg.py
```

4. Start the agent system:
```bash
python scripts/start_agents.py
```

## Project Structure

```
semant/
├── agents/                 # Agent implementations
│   ├── core/              # Core agent classes
│   ├── domain/            # Domain-specific agents
│   └── utils/             # Agent utilities
├── kg/                    # Knowledge graph
│   ├── models/           # Graph models
│   ├── queries/          # SPARQL queries
│   └── schemas/          # RDF schemas
├── tests/                # Test suite
├── scripts/              # Utility scripts
└── docs/                # Documentation
```

## Development

### Adding New Agents
1. Create agent class in `agents/domain/`
2. Implement required interfaces
3. Add to agent registry
4. Update documentation

### Extending Knowledge Graph
1. Define new schemas in `kg/schemas/`
2. Add queries in `kg/queries/`
3. Update models in `kg/models/`

## Testing

Run the test suite:
```bash
pytest tests/
```

## License

MIT License - see LICENSE file for details
