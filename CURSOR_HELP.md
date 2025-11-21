# Cursor Help Guide

## Quick Answers to Your Questions

### 1. **Can Cursor create tasks in Slack?**
Yes! Cursor for Slack allows you to interact with your codebase and create tasks. Based on your Slack thread, you can:
- Use `@Cursor` to mention Cursor in Slack
- Ask Cursor to create tasks from your repository
- Delegate tasks to agents via the knowledge graph

### 2. **Best Way to Delegate Tasks to Knowledge Graph**
The system supports task delegation through:
- **Agent Registry**: Agents register their capabilities in the knowledge graph
- **TaskMaster Integration**: Use TaskMaster to create and manage tasks (see `.cursor/rules/taskmaster/`)
- **Agent Capabilities**: Each agent declares what it can do, stored in KG

### 3. **Using Gemini Pro**
To configure Gemini Pro for AI operations:
```bash
# Set in environment or config
export GOOGLE_API_KEY="your-key-here"
# Or configure in .taskmaster/config.json via:
task-master models --set-main gemini-pro
```

---

## Available Agents in Your System

### **Core Agents** (Infrastructure)

1. **BaseAgent** - Foundation for all agents
2. **ScientificSwarmAgent** - Enhanced scientific agent with advanced capabilities
3. **AgenticPromptAgent** - Prompt engineering and refinement
4. **ResearchAgent** - Research and data analysis
5. **CodeReviewAgent** - AST-based code analysis
6. **DataHandlerAgent** - Data processing and transformation
7. **SensorAgent** - Sensor data collection
8. **DataProcessorAgent** - Data processing operations
9. **RemoteKGAgent** - Knowledge graph remote operations
10. **TTLValidationAgent** - TTL/RDF validation
11. **FeatureZAgent** - Feature-specific agent
12. **SupervisorAgent** - Agent coordination and management

### **Domain Agents** (Specialized)

#### **Prompt & Image Analysis Workflow**
- **PlannerAgent** - Orchestrates prompt refinement workflow
- **LogoAnalysisAgent** - Logo analysis capabilities
- **AestheticsAgent** - Aesthetic analysis
- **ColorPaletteAgent** - Color palette analysis
- **CompositionAgent** - Composition analysis
- **PromptSynthesisAgent** - Synthesizes prompts from analysis
- **PromptCriticAgent** - Critiques prompts
- **PromptJudgeAgent** - Judges prompt quality
- **PromptConstructionAgent** - Constructs prompts
- **ImageAnalysisAgent** - General image analysis

#### **Code & Development**
- **CodeReviewAgent** - Code review and analysis
- **CriticAgent** - Code criticism and feedback
- **JudgeAgent** - Decision-making agent

#### **Knowledge & Data**
- **CorporateKnowledgeAgent** - Corporate knowledge management
- **DiaryAgent** - Activity logging and history
- **VertexEmailAgent** - Email integration via Vertex AI

#### **Simple Responder Agents**
- **FinanceAgent** - Financial queries
- **CoachingAgent** - Coaching assistance
- **IntelligenceAgent** - Intelligence operations
- **DeveloperAgent** - Development assistance

---

## Agent Capabilities Reference

### **Core Capabilities**
- `DATA_PROCESSING` - Process and transform data
- `SENSOR_READING` - Read sensor data
- `RESEARCH` - Research operations
- `REASONING` - Logical reasoning
- `KNOWLEDGE_GRAPH_QUERY` - Query knowledge graph
- `KNOWLEDGE_GRAPH_UPDATE` - Update knowledge graph
- `MESSAGE_PROCESSING` - Process messages

### **Code Capabilities**
- `CODE_REVIEW` - Review code
- `CODE_GENERATION` - Generate code
- `CODE_TESTING` - Test code
- `CODE_DOCUMENTATION` - Document code
- `CODE_OPTIMIZATION` - Optimize code
- `CODE_DEBUGGING` - Debug code
- `CODE_REFACTORING` - Refactor code
- `STATIC_ANALYSIS` - Static code analysis
- `SECURITY_ANALYSIS` - Security analysis
- `ARCHITECTURE_REVIEW` - Architecture review

### **Image & Design Capabilities**
- `LOGO_ANALYSIS` - Analyze logos
- `AESTHETICS_ANALYSIS` - Aesthetic analysis
- `COLOR_PALETTE_ANALYSIS` - Color analysis
- `COMPOSITION_ANALYSIS` - Composition analysis
- `PROMPT_SYNTHESIS` - Synthesize prompts
- `PROMPT_CRITIQUE` - Critique prompts
- `PROMPT_JUDGMENT` - Judge prompts

### **Agent Management Capabilities**
- `AGENT_MANAGEMENT` - Manage agents
- `AGENT_CREATION` - Create agents
- `AGENT_MONITORING` - Monitor agents
- `CAPABILITY_MANAGEMENT` - Manage capabilities
- `WORKLOAD_BALANCING` - Balance workloads

---

## How to Use Agents

### **1. Create an Agent**
```python
from agents.core.agent_factory import AgentFactory
from agents.core.agent_registry import AgentRegistry

factory = AgentFactory()
registry = AgentRegistry()

# Create agent
agent = await factory.create_agent(
    "code_review_agent",
    agent_id="my_reviewer",
    capabilities={Capability(CapabilityType.CODE_REVIEW, "1.0")}
)

# Register agent
await registry.register_agent(agent)
```

### **2. Query Agents by Capability**
```python
# Find all agents that can review code
code_reviewers = await registry.get_agents_by_capability(
    CapabilityType.CODE_REVIEW
)

# Send message to first available reviewer
if code_reviewers:
    message = AgentMessage(
        sender_id="user",
        recipient_id=code_reviewers[0].agent_id,
        content={"code": "your code here"}
    )
    response = await code_reviewers[0].process_message(message)
```

### **3. Delegate Tasks via Knowledge Graph**
```python
# Agents automatically register in KG when created
# Query KG for agents with specific capabilities
from kg.kg_manager import KnowledgeGraphManager

kg = KnowledgeGraphManager()
await kg.initialize()

query = """
PREFIX sem: <http://example.org/semant#>
SELECT ?agent ?capability
WHERE {
    ?agent sem:hasCapability ?capability .
    ?capability rdf:type sem:CodeReview .
}
"""

results = await kg.query_graph(query)
```

---

## TaskMaster Integration

### **Create Tasks from Repository**
```bash
# Initialize TaskMaster (if not done)
task-master init

# Parse a PRD/requirements file to create tasks
task-master parse-prd requirements.txt

# List all tasks
task-master list

# Get next task to work on
task-master next

# Expand a complex task into subtasks
task-master expand --id=1 --research
```

### **Configure Gemini Pro**
```bash
# Set Gemini Pro as the main model
task-master models --set-main gemini-pro

# Or use interactive setup
task-master models --setup
# Then select Gemini Pro when prompted
```

---

## Knowledge Graph Integration

### **Agent Registration in KG**
When agents are created, they automatically:
1. Register their capabilities in the knowledge graph
2. Create RDF triples linking agent → capability
3. Enable discovery via SPARQL queries

### **Query Agents from KG**
```sparql
PREFIX sem: <http://example.org/semant#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

# Find all agents
SELECT ?agent ?type
WHERE {
    ?agent rdf:type sem:Agent .
    ?agent sem:hasCapability ?cap .
    ?cap rdf:type ?type .
}
```

---

## Quick Commands Reference

### **Agent Operations**
```python
# List all registered agents
agents = registry.get_all_agents()

# Get agent capabilities
caps = await registry.get_agent_capabilities("agent_id")

# Get agent status
status = await registry.get_agent_status("agent_id")

# Route message by capability
responses = await registry.route_message_by_capability(
    message, CapabilityType.CODE_REVIEW
)
```

### **TaskMaster Commands**
```bash
task-master list              # List all tasks
task-master next              # Get next task
task-master show <id>         # Show task details
task-master expand --id=<id>  # Break down task
task-master set-status --id=<id> --status=done  # Mark complete
```

---

## Next Steps

1. **Explore Agents**: Check `/workspace/agents/` directory
2. **Read Documentation**: See `/workspace/agents/agents_readme.md`
3. **Set Up TaskMaster**: Follow `.cursor/rules/taskmaster/dev_workflow.mdc`
4. **Configure Models**: Use `task-master models --setup` to configure Gemini Pro
5. **Create Tasks**: Use TaskMaster to create tasks from your requirements

---

## Need More Help?

- **Agent System**: See `/workspace/agents/agents_readme.md`
- **TaskMaster**: See `.cursor/rules/taskmaster/taskmaster.mdc`
- **Knowledge Graph**: See `/workspace/docs/kg_debug_guide.md`
- **Midjourney Integration**: See `/workspace/midjourney_integration/README.md`

---

**Generated**: Based on codebase analysis
**Last Updated**: 2025-01-21
