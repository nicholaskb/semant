#!/usr/bin/env python3
"""
Demonstration of KG Orchestration Tools

This script shows how agents can:
1. Create tasks and workflows in the knowledge graph
2. Discover and coordinate with other agents
3. Share work through SPARQL queries
4. Build complex execution plans dynamically
"""

import asyncio
from loguru import logger
from kg.models.graph_manager import KnowledgeGraphManager
from agents.domain.kg_orchestrator_agent import KGOrchestratorAgent
from agents.core.message_types import AgentMessage
from agents.core.base_agent import BaseAgent
from agents.tools.kg_tools import KGTools
import json


class WorkerAgent(BaseAgent):
    """Simple worker agent that can claim and execute tasks from the KG."""
    
    def __init__(self, agent_id: str, capabilities: list):
        super().__init__(agent_id, "worker")
        self.capabilities = capabilities
        self.kg_tools = None
        
    async def initialize(self) -> None:
        await super().initialize()
        
        if self.knowledge_graph:
            self.kg_tools = KGTools(self.knowledge_graph, self.agent_id)
            
            # Register in KG
            agent_uri = f"http://example.org/agent/{self.agent_id}"
            await self.kg_tools.kg.add_triple(agent_uri, "rdf:type", "http://example.org/core#Agent")
            await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#agentName", self.agent_id)
            await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#agentType", "worker")
            await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#status", "active")
            
            for cap in self.capabilities:
                await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#hasCapability", cap)
                
            logger.info(f"Worker {self.agent_id} registered with capabilities: {self.capabilities}")
            
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        return AgentMessage(
            sender_id=self.agent_id,
            message_type="acknowledgment",
            content={"status": "received"}
        )
        
    async def work(self):
        """Main work loop - check for tasks and execute them."""
        while True:
            try:
                # Check for messages
                messages = await self.kg_tools.query_messages(
                    status="unread"
                )
                
                for msg in messages:
                    logger.info(f"{self.agent_id} received message: {msg['type']}")
                    await self.kg_tools.mark_message_read(msg['message'])
                    
                # Query for available tasks matching our capabilities
                tasks = await self.kg_tools.query_available_tasks(
                    capabilities=self.capabilities
                )
                
                if tasks:
                    # Claim the first available task
                    task = tasks[0]
                    task_id = task['task']
                    
                    if await self.kg_tools.claim_task(task_id):
                        logger.info(f"{self.agent_id} claimed task: {task['name']}")
                        
                        # Simulate task execution
                        await asyncio.sleep(2)
                        
                        # Complete the task
                        await self.kg_tools.update_task_status(
                            task_id,
                            "completed",
                            result={"output": f"Task {task['name']} completed by {self.agent_id}"}
                        )
                        
                        logger.info(f"{self.agent_id} completed task: {task['name']}")
                        
            except Exception as e:
                logger.error(f"{self.agent_id} error in work loop: {e}")
                
            await asyncio.sleep(1)


async def demo_basic_orchestration():
    """Demonstrate basic task creation and orchestration."""
    logger.info("=== Basic Orchestration Demo ===")
    
    # Initialize knowledge graph
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    # Create orchestrator
    orchestrator = KGOrchestratorAgent("master_orchestrator")
    orchestrator.knowledge_graph = kg
    await orchestrator.initialize()
    
    # Create a simple task
    create_task_msg = AgentMessage(
        sender_id="demo",
        message_type="create_task",
        content={
            "name": "Analyze Dataset",
            "type": "analysis",
            "description": "Perform statistical analysis on the sales dataset",
            "priority": "high",
            "metadata": {
                "dataset": "sales_2024.csv",
                "required_outputs": ["summary_stats", "visualization"]
            }
        }
    )
    
    response = await orchestrator.process_message(create_task_msg)
    logger.info(f"Task created: {response.content}")
    
    return kg, orchestrator


async def demo_workflow_creation():
    """Demonstrate workflow creation with multiple steps."""
    logger.info("\n=== Workflow Creation Demo ===")
    
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    orchestrator = KGOrchestratorAgent("workflow_orchestrator")
    orchestrator.knowledge_graph = kg
    await orchestrator.initialize()
    
    # Create a multi-step workflow
    workflow_msg = AgentMessage(
        sender_id="demo",
        message_type="create_workflow",
        content={
            "name": "Data Processing Pipeline",
            "type": "sequential",
            "steps": [
                {
                    "name": "Data Collection",
                    "type": "data_collection",
                    "description": "Collect data from multiple sources",
                    "metadata": {"sources": ["api", "database", "files"]}
                },
                {
                    "name": "Data Cleaning",
                    "type": "data_processing",
                    "description": "Clean and normalize the collected data",
                    "dependencies": [],  # Will depend on previous step
                    "metadata": {"operations": ["dedup", "normalize", "validate"]}
                },
                {
                    "name": "Feature Engineering",
                    "type": "data_processing",
                    "description": "Create features for ML model",
                    "metadata": {"techniques": ["scaling", "encoding", "selection"]}
                },
                {
                    "name": "Model Training",
                    "type": "ml_training",
                    "description": "Train machine learning model",
                    "metadata": {"algorithm": "random_forest", "cv_folds": 5}
                },
                {
                    "name": "Generate Report",
                    "type": "reporting",
                    "description": "Create final analysis report",
                    "metadata": {"format": "pdf", "include_visualizations": True}
                }
            ]
        }
    )
    
    response = await orchestrator.process_message(workflow_msg)
    workflow_id = response.content['workflow_id']
    logger.info(f"Workflow created: {workflow_id}")
    
    # Query workflow status
    status = await orchestrator.kg_tools.query_workflow_status(workflow_id)
    logger.info(f"Workflow status: {json.dumps(status, indent=2)}")
    
    return kg, orchestrator, workflow_id


async def demo_multi_agent_coordination():
    """Demonstrate multiple agents coordinating through the KG."""
    logger.info("\n=== Multi-Agent Coordination Demo ===")
    
    # Initialize shared knowledge graph
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    # Create orchestrator
    orchestrator = KGOrchestratorAgent("coordinator")
    orchestrator.knowledge_graph = kg
    await orchestrator.initialize()
    
    # Create specialized worker agents
    workers = [
        WorkerAgent("data_agent", [
            "http://example.org/capability/data_collection",
            "http://example.org/capability/data_processing"
        ]),
        WorkerAgent("ml_agent", [
            "http://example.org/capability/ml_training",
            "http://example.org/capability/model_evaluation"
        ]),
        WorkerAgent("report_agent", [
            "http://example.org/capability/reporting",
            "http://example.org/capability/visualization"
        ])
    ]
    
    # Initialize workers with shared KG
    for worker in workers:
        worker.knowledge_graph = kg
        await worker.initialize()
        
    # Start worker tasks
    worker_tasks = [asyncio.create_task(worker.work()) for worker in workers]
    
    # Broadcast a message to all agents
    broadcast_msg = AgentMessage(
        sender_id="demo",
        message_type="orchestrate_agents",
        content={
            "operation": "broadcast",
            "message_type": "notification",
            "message_content": {
                "announcement": "New project starting",
                "project_id": "ML_PROJECT_001"
            }
        }
    )
    
    await orchestrator.process_message(broadcast_msg)
    logger.info("Broadcast sent to all agents")
    
    # Create tasks with specific capability requirements
    tasks_to_create = [
        {
            "name": "Collect Training Data",
            "type": "data_collection",
            "required_capabilities": ["http://example.org/capability/data_collection"],
            "auto_assign": True
        },
        {
            "name": "Train ML Model",
            "type": "ml_training",
            "required_capabilities": ["http://example.org/capability/ml_training"],
            "auto_assign": True
        },
        {
            "name": "Generate Performance Report",
            "type": "reporting",
            "required_capabilities": ["http://example.org/capability/reporting"],
            "auto_assign": True
        }
    ]
    
    for task_def in tasks_to_create:
        create_msg = AgentMessage(
            sender_id="demo",
            message_type="create_task",
            content=task_def
        )
        response = await orchestrator.process_message(create_msg)
        logger.info(f"Task '{task_def['name']}' assigned to: {response.content.get('assigned_agents', [])}")
        
    # Let agents work for a bit
    await asyncio.sleep(10)
    
    # Cancel worker tasks
    for task in worker_tasks:
        task.cancel()
        
    return kg, orchestrator


async def demo_dynamic_plan_execution():
    """Demonstrate dynamic plan creation and execution."""
    logger.info("\n=== Dynamic Plan Execution Demo ===")
    
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    orchestrator = KGOrchestratorAgent("plan_executor")
    orchestrator.knowledge_graph = kg
    await orchestrator.initialize()
    
    # Create a dynamic plan based on discovered agents
    discover_msg = AgentMessage(
        sender_id="demo",
        message_type="orchestrate_agents",
        content={
            "operation": "discover",
            "status": "active"
        }
    )
    
    response = await orchestrator.process_message(discover_msg)
    available_agents = response.content['agents']
    logger.info(f"Discovered {len(available_agents)} active agents")
    
    # Build a plan based on available capabilities
    plan_steps = []
    
    # Check what capabilities we have available
    all_capabilities = set()
    for agent in available_agents:
        all_capabilities.update(agent.get('capabilities', []))
        
    logger.info(f"Available capabilities: {all_capabilities}")
    
    # Dynamically create plan steps based on capabilities
    if "http://example.org/capability/data_collection" in all_capabilities:
        plan_steps.append({
            "name": "Gather Data",
            "type": "data_collection",
            "description": "Collect required data from sources",
            "required_capabilities": ["http://example.org/capability/data_collection"]
        })
        
    if "http://example.org/capability/ml_training" in all_capabilities:
        plan_steps.append({
            "name": "Train Model",
            "type": "ml_training",
            "description": "Train predictive model",
            "required_capabilities": ["http://example.org/capability/ml_training"]
        })
        
    # Execute the dynamic plan
    if plan_steps:
        workflow_id = await orchestrator.create_and_execute_plan(
            "Dynamic ML Pipeline",
            plan_steps
        )
        logger.info(f"Executing dynamic plan: {workflow_id}")
        
    return kg, orchestrator


async def demo_sparql_coordination():
    """Demonstrate coordination through SPARQL queries."""
    logger.info("\n=== SPARQL Coordination Demo ===")
    
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    # Direct SPARQL query example
    logger.info("Running SPARQL queries for coordination:")
    
    # Query 1: Find all pending tasks
    pending_tasks_query = """
    PREFIX core: <http://example.org/core#>
    SELECT ?task ?name ?type ?priority WHERE {
        ?task a core:Task ;
              core:taskName ?name ;
              core:taskType ?type ;
              core:priority ?priority ;
              core:status "pending" .
    }
    ORDER BY DESC(?priority)
    """
    
    results = await kg.query_graph(pending_tasks_query)
    logger.info(f"Found {len(results)} pending tasks")
    
    # Query 2: Find agents and their current workload
    agent_workload_query = """
    PREFIX core: <http://example.org/core#>
    SELECT ?agent ?name (COUNT(?task) as ?workload) WHERE {
        ?agent a core:Agent ;
               core:agentName ?name ;
               core:status "active" .
        OPTIONAL {
            ?task core:assignedTo ?agent ;
                  core:status "in_progress" .
        }
    }
    GROUP BY ?agent ?name
    ORDER BY ?workload
    """
    
    results = await kg.query_graph(agent_workload_query)
    logger.info("Agent workloads:")
    for result in results:
        logger.info(f"  {result['name']}: {result['workload']} active tasks")
        
    # Query 3: Find completed tasks in last hour
    completed_query = """
    PREFIX core: <http://example.org/core#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT ?task ?name ?completedAt ?result WHERE {
        ?task a core:Task ;
              core:taskName ?name ;
              core:status "completed" ;
              core:completedAt ?completedAt .
        OPTIONAL { ?task core:result ?result }
    }
    ORDER BY DESC(?completedAt)
    LIMIT 10
    """
    
    results = await kg.query_graph(completed_query)
    logger.info(f"Recent completed tasks: {len(results)}")
    
    return kg


async def main():
    """Run all demonstrations."""
    kg_instances = []
    try:
        # Basic orchestration
        kg, _ = await demo_basic_orchestration()
        kg_instances.append(kg)
        
        # Workflow creation
        kg, _, _ = await demo_workflow_creation()
        kg_instances.append(kg)
        
        # Multi-agent coordination
        kg, _ = await demo_multi_agent_coordination()
        kg_instances.append(kg)
        
        # Dynamic plan execution
        kg, _ = await demo_dynamic_plan_execution()
        kg_instances.append(kg)
        
        # SPARQL coordination
        kg = await demo_sparql_coordination()
        kg_instances.append(kg)
        
        logger.info("\n=== All demonstrations completed successfully ===")
        
    except Exception as e:
        logger.error(f"Error in demonstration: {e}")
        raise
    finally:
        # Cleanup all KG instances
        for kg in kg_instances:
            if kg:
                try:
                    await kg.shutdown()
                except Exception as e:
                    logger.warning(f"Error shutting down KG: {e}")


if __name__ == "__main__":
    asyncio.run(main())
