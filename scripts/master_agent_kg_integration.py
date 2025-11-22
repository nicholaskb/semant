#!/usr/bin/env python3
"""
Master Agent KG Integration Example

Shows how a master agent can use the KG tools to:
1. Spin up new task nodes dynamically
2. Coordinate multiple agents through the KG
3. Execute complex workflows
4. Share results through SPARQL queries
"""

import asyncio
from typing import Dict, List, Any, Optional
from loguru import logger
from kg.models.graph_manager import KnowledgeGraphManager
from agents.domain.kg_orchestrator_agent import KGOrchestratorAgent
from agents.core.base_agent import BaseAgent
from agents.core.message_types import AgentMessage
from agents.tools.kg_tools import KGTools
import json


class MasterAgent(BaseAgent):
    """
    Master agent that orchestrates complex tasks using KG tools.
    This demonstrates how the main agent can leverage KG for coordination.
    """
    
    def __init__(self, agent_id: str = "master_agent"):
        super().__init__(agent_id, "master")
        self.kg_tools: Optional[KGTools] = None
        self.orchestrator: Optional[KGOrchestratorAgent] = None
        
    async def initialize(self) -> None:
        """Initialize the master agent with KG tools."""
        await super().initialize()
        
        if self.knowledge_graph:
            # Initialize KG tools
            self.kg_tools = KGTools(self.knowledge_graph, self.agent_id)
            
            # Create an orchestrator for complex operations
            self.orchestrator = KGOrchestratorAgent(f"{self.agent_id}_orchestrator")
            self.orchestrator.knowledge_graph = self.knowledge_graph
            await self.orchestrator.initialize()
            
            # Register ourselves with advanced capabilities
            await self._register_master_capabilities()
            
            logger.info("Master agent initialized with full KG orchestration capabilities")
            
    async def _register_master_capabilities(self) -> None:
        """Register master agent capabilities in the KG."""
        # Define master capabilities
        master_capabilities = [
            ("strategic_planning", "master", "Ability to create high-level strategic plans"),
            ("agent_spawning", "master", "Ability to create and manage other agents"),
            ("workflow_design", "master", "Ability to design complex multi-agent workflows"),
            ("resource_allocation", "master", "Ability to allocate resources across agents"),
            ("performance_monitoring", "master", "Ability to monitor system-wide performance")
        ]
        
        # Create capability nodes
        cap_uris = []
        for cap_name, cap_type, description in master_capabilities:
            cap_uri = await self.kg_tools.create_capability_node(
                cap_name, cap_type, description
            )
            cap_uris.append(cap_uri)
            
        # Register master agent
        agent_uri = f"http://example.org/agent/{self.agent_id}"
        await self.kg_tools.kg.add_triple(agent_uri, "rdf:type", "http://example.org/core#Agent")
        await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#agentName", self.agent_id)
        await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#agentType", "master")
        await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#status", "active")
        
        for cap_uri in cap_uris:
            await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#hasCapability", cap_uri)
            
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        if message.message_type == "execute_plan":
            return await self._handle_execute_plan(message)
        elif message.message_type == "spawn_agents":
            return await self._handle_spawn_agents(message)
        elif message.message_type == "monitor_system":
            return await self._handle_monitor_system(message)
        else:
            # Delegate to orchestrator for standard operations
            return await self.orchestrator.process_message(message)
            
    async def _handle_execute_plan(self, message: AgentMessage) -> AgentMessage:
        """Execute a high-level plan by breaking it down into tasks."""
        plan = message.content
        plan_name = plan.get("name", "Strategic Plan")
        objectives = plan.get("objectives", [])
        
        logger.info(f"Executing plan: {plan_name}")
        
        # Create a master workflow for the plan
        workflow_steps = []
        
        for i, objective in enumerate(objectives):
            # Analyze objective and create appropriate tasks
            if objective.get("type") == "data_analysis":
                workflow_steps.extend(self._create_analysis_tasks(objective, i))
            elif objective.get("type") == "model_training":
                workflow_steps.extend(self._create_ml_tasks(objective, i))
            elif objective.get("type") == "report_generation":
                workflow_steps.extend(self._create_reporting_tasks(objective, i))
            else:
                workflow_steps.append({
                    "name": f"Objective {i+1}: {objective.get('name', 'Unknown')}",
                    "type": "generic",
                    "description": objective.get('description', ''),
                    "metadata": objective
                })
                
        # Create the workflow
        workflow_id = await self.orchestrator.create_and_execute_plan(
            plan_name,
            workflow_steps
        )
        
        # Monitor execution
        asyncio.create_task(self._monitor_workflow_execution(workflow_id))
        
        return AgentMessage(
            sender_id=self.agent_id,
            message_type="plan_executing",
            content={
                "plan_name": plan_name,
                "workflow_id": workflow_id,
                "total_tasks": len(workflow_steps)
            }
        )
        
    async def _handle_spawn_agents(self, message: AgentMessage) -> AgentMessage:
        """Dynamically create new agents based on requirements."""
        requirements = message.content
        agents_to_create = requirements.get("agents", [])
        
        created_agents = []
        
        for agent_spec in agents_to_create:
            # Create capability nodes for new capabilities
            capabilities = []
            for cap in agent_spec.get("capabilities", []):
                if isinstance(cap, dict):
                    cap_uri = await self.kg_tools.create_capability_node(
                        cap["name"],
                        cap.get("type", "specialized"),
                        cap.get("description", "")
                    )
                    capabilities.append(cap_uri)
                else:
                    capabilities.append(cap)
                    
            # Create the agent node
            agent_id = await self.kg_tools.create_agent_node(
                agent_name=agent_spec["name"],
                agent_type=agent_spec.get("type", "worker"),
                capabilities=capabilities,
                metadata=agent_spec.get("metadata", {})
            )
            
            created_agents.append({
                "id": agent_id,
                "name": agent_spec["name"],
                "capabilities": capabilities
            })
            
            logger.info(f"Spawned agent: {agent_spec['name']} with {len(capabilities)} capabilities")
            
        # Broadcast agent creation notification
        await self.kg_tools.broadcast_message(
            "agent_spawned",
            {
                "spawned_by": self.agent_id,
                "new_agents": created_agents
            }
        )
        
        return AgentMessage(
            sender_id=self.agent_id,
            message_type="agents_spawned",
            content={"agents": created_agents}
        )
        
    async def _handle_monitor_system(self, message: AgentMessage) -> AgentMessage:
        """Monitor system-wide performance using SPARQL queries."""
        monitoring_queries = {
            "active_agents": """
                PREFIX core: <http://example.org/core#>
                SELECT (COUNT(DISTINCT ?agent) as ?count) WHERE {
                    ?agent a core:Agent ;
                           core:status "active" .
                }
            """,
            "pending_tasks": """
                PREFIX core: <http://example.org/core#>
                SELECT (COUNT(DISTINCT ?task) as ?count) WHERE {
                    ?task a core:Task ;
                          core:status "pending" .
                }
            """,
            "in_progress_tasks": """
                PREFIX core: <http://example.org/core#>
                SELECT (COUNT(DISTINCT ?task) as ?count) WHERE {
                    ?task a core:Task ;
                          core:status "in_progress" .
                }
            """,
            "completed_today": """
                PREFIX core: <http://example.org/core#>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                SELECT (COUNT(DISTINCT ?task) as ?count) WHERE {
                    ?task a core:Task ;
                          core:status "completed" ;
                          core:completedAt ?time .
                    FILTER(?time >= xsd:dateTime(CONCAT(STR(YEAR(NOW())), "-", 
                           STR(MONTH(NOW())), "-", STR(DAY(NOW())), "T00:00:00Z")))
                }
            """,
            "agent_workload": """
                PREFIX core: <http://example.org/core#>
                SELECT ?agent (COUNT(?task) as ?workload) WHERE {
                    ?agent a core:Agent ;
                           core:status "active" .
                    OPTIONAL {
                        ?task core:assignedTo ?agent ;
                              core:status "in_progress" .
                    }
                }
                GROUP BY ?agent
                ORDER BY DESC(?workload)
                LIMIT 10
            """
        }
        
        metrics = {}
        
        for metric_name, query in monitoring_queries.items():
            try:
                results = await self.kg_tools.kg.query_graph(query)
                if metric_name == "agent_workload":
                    metrics[metric_name] = results
                else:
                    metrics[metric_name] = results[0]['count'] if results else 0
            except Exception as e:
                logger.error(f"Error running monitoring query {metric_name}: {e}")
                metrics[metric_name] = "error"
                
        return AgentMessage(
            sender_id=self.agent_id,
            message_type="system_metrics",
            content=metrics
        )
        
    def _create_analysis_tasks(self, objective: Dict[str, Any], index: int) -> List[Dict[str, Any]]:
        """Create tasks for data analysis objectives."""
        return [
            {
                "name": f"Collect Data - {objective.get('name', f'Analysis {index}')}",
                "type": "data_collection",
                "description": f"Collect data for: {objective.get('description', '')}",
                "metadata": {"source": objective.get("data_source", "unknown")}
            },
            {
                "name": f"Clean Data - {objective.get('name', f'Analysis {index}')}",
                "type": "data_processing",
                "description": "Clean and prepare data for analysis",
                "metadata": {"operations": ["dedup", "normalize", "validate"]}
            },
            {
                "name": f"Analyze - {objective.get('name', f'Analysis {index}')}",
                "type": "analysis",
                "description": "Perform statistical analysis",
                "metadata": {"methods": objective.get("methods", ["descriptive", "correlation"])}
            }
        ]
        
    def _create_ml_tasks(self, objective: Dict[str, Any], index: int) -> List[Dict[str, Any]]:
        """Create tasks for machine learning objectives."""
        return [
            {
                "name": f"Prepare Training Data - {objective.get('name', f'ML {index}')}",
                "type": "data_preparation",
                "description": "Prepare data for model training",
                "metadata": {"split_ratio": objective.get("split_ratio", "80/20")}
            },
            {
                "name": f"Train Model - {objective.get('name', f'ML {index}')}",
                "type": "ml_training",
                "description": f"Train {objective.get('algorithm', 'default')} model",
                "metadata": {
                    "algorithm": objective.get("algorithm", "random_forest"),
                    "hyperparameters": objective.get("hyperparameters", {})
                }
            },
            {
                "name": f"Evaluate Model - {objective.get('name', f'ML {index}')}",
                "type": "model_evaluation",
                "description": "Evaluate model performance",
                "metadata": {"metrics": objective.get("metrics", ["accuracy", "f1_score"])}
            }
        ]
        
    def _create_reporting_tasks(self, objective: Dict[str, Any], index: int) -> List[Dict[str, Any]]:
        """Create tasks for reporting objectives."""
        return [
            {
                "name": f"Generate Report - {objective.get('name', f'Report {index}')}",
                "type": "reporting",
                "description": f"Generate {objective.get('format', 'PDF')} report",
                "metadata": {
                    "format": objective.get("format", "pdf"),
                    "sections": objective.get("sections", ["summary", "findings", "recommendations"])
                }
            }
        ]
        
    async def _monitor_workflow_execution(self, workflow_id: str) -> None:
        """Monitor workflow execution and log progress."""
        while True:
            try:
                status = await self.kg_tools.query_workflow_status(workflow_id)
                
                logger.info(
                    f"Workflow {workflow_id} progress: "
                    f"{status['completed_tasks']}/{status['total_tasks']} "
                    f"(Status: {status['status']})"
                )
                
                if status['status'] in ['completed', 'failed']:
                    logger.info(f"Workflow {workflow_id} finished with status: {status['status']}")
                    break
                    
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring workflow {workflow_id}: {e}")
                break


async def demonstrate_master_agent():
    """Demonstrate the master agent's KG orchestration capabilities."""
    # Initialize KG
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    # Create master agent
    master = MasterAgent()
    master.knowledge_graph = kg
    await master.initialize()
    
    logger.info("=== Master Agent KG Integration Demo ===")
    
    # Demo 1: Spawn specialized agents
    logger.info("\n1. Spawning specialized agents...")
    spawn_msg = AgentMessage(
        sender_id="demo",
        message_type="spawn_agents",
        content={
            "agents": [
                {
                    "name": "Data Scientist Agent",
                    "type": "specialist",
                    "capabilities": [
                        {
                            "name": "advanced_analytics",
                            "type": "analysis",
                            "description": "Advanced statistical analysis and modeling"
                        },
                        {
                            "name": "ml_expertise",
                            "type": "ml",
                            "description": "Machine learning model development"
                        }
                    ]
                },
                {
                    "name": "Report Writer Agent",
                    "type": "specialist",
                    "capabilities": [
                        {
                            "name": "technical_writing",
                            "type": "documentation",
                            "description": "Technical report writing"
                        },
                        {
                            "name": "data_visualization",
                            "type": "visualization",
                            "description": "Creating charts and visualizations"
                        }
                    ]
                }
            ]
        }
    )
    
    response = await master.process_message(spawn_msg)
    logger.info(f"Spawned {len(response.content['agents'])} agents")
    
    # Demo 2: Execute a complex plan
    logger.info("\n2. Executing a strategic plan...")
    plan_msg = AgentMessage(
        sender_id="demo",
        message_type="execute_plan",
        content={
            "name": "Customer Churn Analysis Project",
            "objectives": [
                {
                    "name": "Customer Data Analysis",
                    "type": "data_analysis",
                    "description": "Analyze customer behavior patterns",
                    "data_source": "customer_db",
                    "methods": ["segmentation", "trend_analysis"]
                },
                {
                    "name": "Churn Prediction Model",
                    "type": "model_training",
                    "description": "Build model to predict customer churn",
                    "algorithm": "gradient_boosting",
                    "hyperparameters": {"n_estimators": 100, "learning_rate": 0.1}
                },
                {
                    "name": "Executive Report",
                    "type": "report_generation",
                    "description": "Generate executive summary with recommendations",
                    "format": "pdf",
                    "sections": ["executive_summary", "key_findings", "recommendations", "next_steps"]
                }
            ]
        }
    )
    
    response = await master.process_message(plan_msg)
    logger.info(f"Plan executing with workflow: {response.content['workflow_id']}")
    
    # Demo 3: Monitor system
    logger.info("\n3. Monitoring system status...")
    monitor_msg = AgentMessage(
        sender_id="demo",
        message_type="monitor_system",
        content={}
    )
    
    response = await master.process_message(monitor_msg)
    metrics = response.content
    
    logger.info("System Metrics:")
    logger.info(f"  Active Agents: {metrics.get('active_agents', 0)}")
    logger.info(f"  Pending Tasks: {metrics.get('pending_tasks', 0)}")
    logger.info(f"  In Progress: {metrics.get('in_progress_tasks', 0)}")
    logger.info(f"  Completed Today: {metrics.get('completed_today', 0)}")
    
    if isinstance(metrics.get('agent_workload'), list):
        logger.info("  Top Agent Workloads:")
        for agent_work in metrics['agent_workload'][:3]:
            logger.info(f"    {agent_work['agent']}: {agent_work['workload']} tasks")
            
    # Demo 4: Direct SPARQL query for custom insights
    logger.info("\n4. Running custom SPARQL analysis...")
    
    custom_query = """
    PREFIX core: <http://example.org/core#>
    SELECT ?capability (COUNT(DISTINCT ?agent) as ?agent_count) 
           (COUNT(DISTINCT ?task) as ?task_count) WHERE {
        ?agent core:hasCapability ?capability .
        OPTIONAL {
            ?task core:requiresCapability ?capability ;
                  core:status ?status .
        }
    }
    GROUP BY ?capability
    ORDER BY DESC(?task_count)
    """
    
    results = await kg.query_graph(custom_query)
    
    logger.info("Capability Usage Analysis:")
    for result in results[:5]:
        logger.info(
            f"  {result['capability']}: "
            f"{result['agent_count']} agents, "
            f"{result['task_count']} tasks"
        )
        
    logger.info("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(demonstrate_master_agent())
