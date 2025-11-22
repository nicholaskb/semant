"""
Knowledge Graph Tools for Agent Collaboration

This module provides a comprehensive set of tools that enable agents to:
1. Create and extend nodes in the knowledge graph dynamically
2. Share work and tasks with other agents through SPARQL queries
3. Discover and coordinate with other agents
4. Build complex workflows and plans in the KG
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from loguru import logger
from rdflib import URIRef, Literal, Namespace, RDF
from kg.models.graph_manager import KnowledgeGraphManager
from kg.models.remote_graph_manager import RemoteKnowledgeGraphManager
from agents.core.message_types import AgentMessage


class KGTools:
    """Knowledge Graph tools for agent collaboration and dynamic node creation."""
    
    def __init__(self, kg_manager: Union[KnowledgeGraphManager, RemoteKnowledgeGraphManager], agent_id: str):
        """
        Initialize KG tools with a knowledge graph manager.
        
        Args:
            kg_manager: The knowledge graph manager instance
            agent_id: The ID of the agent using these tools
        """
        self.kg = kg_manager
        self.agent_id = agent_id
        self.logger = logger.bind(agent_id=agent_id, component="KGTools")
        
        # Define namespaces
        self.AGENT = Namespace("http://example.org/agent/")
        self.TASK = Namespace("http://example.org/task/")
        self.WORKFLOW = Namespace("http://example.org/workflow/")
        self.CAPABILITY = Namespace("http://example.org/capability/")
        self.CORE = Namespace("http://example.org/core#")
        
    async def create_task_node(
        self,
        task_name: str,
        task_type: str,
        description: str,
        priority: str = "medium",
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new task node in the knowledge graph that can be executed by agents.
        
        Args:
            task_name: Human-readable name for the task
            task_type: Type of task (e.g., "research", "code_generation", "analysis")
            description: Detailed description of what needs to be done
            priority: Task priority (low, medium, high, critical)
            dependencies: List of task IDs that must complete before this task
            metadata: Additional task-specific metadata
            
        Returns:
            The task ID (URI) of the created task
        """
        task_id = f"{self.TASK}{uuid.uuid4()}"
        timestamp = datetime.utcnow().isoformat()
        
        # Create task node
        await self.kg.add_triple(task_id, str(RDF.type), str(self.CORE.Task))
        await self.kg.add_triple(task_id, str(self.CORE.taskName), task_name)
        await self.kg.add_triple(task_id, str(self.CORE.taskType), task_type)
        await self.kg.add_triple(task_id, str(self.CORE.description), description)
        await self.kg.add_triple(task_id, str(self.CORE.priority), priority)
        await self.kg.add_triple(task_id, str(self.CORE.status), "pending")
        await self.kg.add_triple(task_id, str(self.CORE.createdBy), self.agent_id)
        await self.kg.add_triple(task_id, str(self.CORE.createdAt), timestamp)
        
        # Add dependencies
        if dependencies:
            for dep in dependencies:
                await self.kg.add_triple(task_id, str(self.CORE.dependsOn), dep)
        
        # Add metadata
        if metadata:
            await self.kg.add_triple(task_id, str(self.CORE.metadata), json.dumps(metadata))
            
        self.logger.info(f"Created task node: {task_id} - {task_name}")
        return task_id
        
    async def create_workflow_node(
        self,
        workflow_name: str,
        workflow_type: str,
        steps: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a workflow node that orchestrates multiple tasks.
        
        Args:
            workflow_name: Name of the workflow
            workflow_type: Type of workflow (e.g., "sequential", "parallel", "conditional")
            steps: List of workflow steps with task definitions
            metadata: Additional workflow metadata
            
        Returns:
            The workflow ID (URI)
        """
        workflow_id = f"{self.WORKFLOW}{uuid.uuid4()}"
        timestamp = datetime.utcnow().isoformat()
        
        # Create workflow node
        await self.kg.add_triple(workflow_id, str(RDF.type), str(self.CORE.Workflow))
        await self.kg.add_triple(workflow_id, str(self.CORE.workflowName), workflow_name)
        await self.kg.add_triple(workflow_id, str(self.CORE.workflowType), workflow_type)
        await self.kg.add_triple(workflow_id, str(self.CORE.createdBy), self.agent_id)
        await self.kg.add_triple(workflow_id, str(self.CORE.createdAt), timestamp)
        
        # Create tasks for each step
        task_ids = []
        for i, step in enumerate(steps):
            task_id = await self.create_task_node(
                task_name=step.get("name", f"Step {i+1}"),
                task_type=step.get("type", "generic"),
                description=step.get("description", ""),
                priority=step.get("priority", "medium"),
                dependencies=step.get("dependencies", []),
                metadata=step.get("metadata", {})
            )
            task_ids.append(task_id)
            
            # Link task to workflow
            await self.kg.add_triple(workflow_id, str(self.CORE.hasTask), task_id)
            await self.kg.add_triple(task_id, str(self.CORE.partOfWorkflow), workflow_id)
            await self.kg.add_triple(task_id, str(self.CORE.stepNumber), str(i + 1))
            
        # Add metadata
        if metadata:
            await self.kg.add_triple(workflow_id, str(self.CORE.metadata), json.dumps(metadata))
            
        self.logger.info(f"Created workflow: {workflow_id} with {len(task_ids)} tasks")
        return workflow_id
        
    async def share_task_with_agents(
        self,
        task_id: str,
        required_capabilities: List[str],
        max_agents: int = 1
    ) -> List[str]:
        """
        Share a task with agents that have the required capabilities.
        
        Args:
            task_id: The task to share
            required_capabilities: List of capabilities required to execute the task
            max_agents: Maximum number of agents to assign
            
        Returns:
            List of agent IDs that were assigned the task
        """
        # Find agents with required capabilities
        capability_filter = " ".join([
            f"?agent <{self.CORE}hasCapability> \"{cap}\" ." 
            for cap in required_capabilities
        ])
        
        query = f"""
        PREFIX core: <{self.CORE}>
        SELECT DISTINCT ?agent WHERE {{
            ?agent a core:Agent .
            {capability_filter}
            ?agent core:status "active" .
            FILTER NOT EXISTS {{
                ?agent core:workload ?load .
                FILTER(?load > 5)
            }}
        }}
        LIMIT {max_agents}
        """
        
        results = await self.kg.query_graph(query)
        assigned_agents = []
        
        for result in results:
            agent_uri = result['agent']
            # Assign task to agent
            await self.kg.add_triple(task_id, str(self.CORE.assignedTo), agent_uri)
            await self.kg.add_triple(agent_uri, str(self.CORE.hasAssignedTask), task_id)
            await self.kg.add_triple(task_id, str(self.CORE.assignedAt), datetime.utcnow().isoformat())
            assigned_agents.append(agent_uri)
            
        self.logger.info(f"Shared task {task_id} with {len(assigned_agents)} agents")
        return assigned_agents
        
    async def query_available_tasks(
        self,
        capabilities: Optional[List[str]] = None,
        task_types: Optional[List[str]] = None,
        priority: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query for available tasks that match agent capabilities.
        
        Args:
            capabilities: Filter by required capabilities
            task_types: Filter by task types
            priority: Filter by priority level
            
        Returns:
            List of available tasks with details
        """
        filters = ["?task core:status 'pending' ."]
        
        if capabilities:
            cap_filter = " UNION ".join([
                f"{{ ?task core:requiresCapability <{cap}> }}"
                for cap in capabilities
            ])
            filters.append(f"{{ {cap_filter} }}")
            
        if task_types:
            type_filter = " || ".join([
                f"?type = '{t}'" for t in task_types
            ])
            filters.append(f"FILTER({type_filter})")
            
        if priority:
            filters.append(f"?task core:priority '{priority}' .")
            
        filter_clause = "\n".join(filters)
        
        query = f"""
        PREFIX core: <{self.CORE}>
        SELECT ?task ?name ?type ?description ?priority ?createdBy WHERE {{
            ?task a core:Task ;
                  core:taskName ?name ;
                  core:taskType ?type ;
                  core:description ?description ;
                  core:priority ?priority ;
                  core:createdBy ?createdBy .
            {filter_clause}
            FILTER NOT EXISTS {{
                ?task core:assignedTo ?agent .
            }}
        }}
        ORDER BY DESC(?priority) ?name
        """
        
        results = await self.kg.query_graph(query)
        return results
        
    async def claim_task(self, task_id: str) -> bool:
        """
        Claim a task for execution by this agent.
        
        Args:
            task_id: The task to claim
            
        Returns:
            True if successfully claimed, False otherwise
        """
        # Check if task is available
        check_query = f"""
        PREFIX core: <{self.CORE}>
        SELECT ?status WHERE {{
            <{task_id}> a core:Task ;
                       core:status ?status .
            OPTIONAL {{
                <{task_id}> core:assignedTo ?agent .
            }}
            FILTER(!BOUND(?agent) && ?status = "pending")
        }}
        """
        
        results = await self.kg.query_graph(check_query)
        if not results or len(results) == 0:
            self.logger.warning(f"Task {task_id} is not available")
            return False
            
        # Claim the task
        timestamp = datetime.utcnow().isoformat()
        await self.kg.add_triple(task_id, str(self.CORE.assignedTo), self.agent_id)
        await self.kg.add_triple(task_id, str(self.CORE.claimedAt), timestamp)
        await self.kg.add_triple(task_id, str(self.CORE.status), "in_progress")
        await self.kg.add_triple(self.agent_id, str(self.CORE.workingOn), task_id)
        
        self.logger.info(f"Successfully claimed task {task_id}")
        return True
        
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Update the status of a task.
        
        Args:
            task_id: The task to update
            status: New status (in_progress, completed, failed, blocked)
            result: Task execution result (for completed tasks)
            error: Error message (for failed tasks)
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Update status - remove old status first (status is single-valued)
        await self.kg.remove_triple(task_id, str(self.CORE.status))
        await self.kg.add_triple(task_id, str(self.CORE.status), status)
        await self.kg.add_triple(task_id, str(self.CORE.lastUpdated), timestamp)
        
        if status == "completed" and result:
            await self.kg.add_triple(task_id, str(self.CORE.result), json.dumps(result))
            await self.kg.add_triple(task_id, str(self.CORE.completedAt), timestamp)
            
        if status == "failed" and error:
            await self.kg.add_triple(task_id, str(self.CORE.error), error)
            await self.kg.add_triple(task_id, str(self.CORE.failedAt), timestamp)
            
        self.logger.info(f"Updated task {task_id} status to {status}")
        
    async def discover_agents(
        self,
        capabilities: Optional[List[str]] = None,
        status: str = "active"
    ) -> List[Dict[str, Any]]:
        """
        Discover other agents in the system.
        
        Args:
            capabilities: Filter by required capabilities
            status: Filter by agent status
            
        Returns:
            List of discovered agents with their details
        """
        capability_filter = ""
        if capabilities:
            # Capabilities are stored as strings, not URIs
            capability_filter = " ".join([
                f"?agent core:hasCapability \"{cap}\" ."
                for cap in capabilities
            ])
            
        query = f"""
        PREFIX core: <{self.CORE}>
        SELECT ?agent ?name ?type 
               (GROUP_CONCAT(DISTINCT ?cap; SEPARATOR=",") as ?capabilities) WHERE {{
            ?agent a core:Agent ;
                   core:agentName ?name ;
                   core:agentType ?type ;
                   core:status "{status}" .
            {capability_filter}
            OPTIONAL {{ ?agent core:hasCapability ?cap }}
        }}
        GROUP BY ?agent ?name ?type
        """
        
        results = await self.kg.query_graph(query)
        
        # Parse capabilities
        for result in results:
            if result.get('capabilities'):
                result['capabilities'] = result['capabilities'].split(',')
            else:
                result['capabilities'] = []
                
        return results
        
    async def create_agent_node(
        self,
        agent_name: str,
        agent_type: str,
        capabilities: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new agent node in the knowledge graph.
        
        Args:
            agent_name: Name of the agent
            agent_type: Type of agent (e.g., "research", "coding", "analysis")
            capabilities: List of capability URIs
            metadata: Additional agent metadata
            
        Returns:
            The agent ID (URI)
        """
        agent_id = f"{self.AGENT}{uuid.uuid4()}"
        timestamp = datetime.utcnow().isoformat()
        
        # Create agent node
        await self.kg.add_triple(agent_id, str(RDF.type), str(self.CORE.Agent))
        await self.kg.add_triple(agent_id, str(self.CORE.agentName), agent_name)
        await self.kg.add_triple(agent_id, str(self.CORE.agentType), agent_type)
        await self.kg.add_triple(agent_id, str(self.CORE.status), "active")
        await self.kg.add_triple(agent_id, str(self.CORE.createdAt), timestamp)
        await self.kg.add_triple(agent_id, str(self.CORE.createdBy), self.agent_id)
        
        # Add capabilities
        for capability in capabilities:
            await self.kg.add_triple(agent_id, str(self.CORE.hasCapability), capability)
            
        # Add metadata
        if metadata:
            await self.kg.add_triple(agent_id, str(self.CORE.metadata), json.dumps(metadata))
            
        self.logger.info(f"Created agent node: {agent_id} - {agent_name}")
        return agent_id
        
    async def broadcast_message(
        self,
        message_type: str,
        content: Dict[str, Any],
        target_capabilities: Optional[List[str]] = None
    ) -> str:
        """
        Broadcast a message to agents through the knowledge graph.
        
        Args:
            message_type: Type of message
            content: Message content
            target_capabilities: Target agents with specific capabilities
            
        Returns:
            Message ID
        """
        message_id = f"http://example.org/message/{uuid.uuid4()}"
        timestamp = datetime.utcnow().isoformat()
        
        # Create message node
        await self.kg.add_triple(message_id, str(RDF.type), str(self.CORE.Message))
        await self.kg.add_triple(message_id, str(self.CORE.messageType), message_type)
        await self.kg.add_triple(message_id, str(self.CORE.content), json.dumps(content))
        await self.kg.add_triple(message_id, str(self.CORE.sender), self.agent_id)
        await self.kg.add_triple(message_id, str(self.CORE.timestamp), timestamp)
        await self.kg.add_triple(message_id, str(self.CORE.status), "unread")
        
        # Add target capabilities
        if target_capabilities:
            for cap in target_capabilities:
                await self.kg.add_triple(message_id, str(self.CORE.targetCapability), cap)
                
        self.logger.info(f"Broadcast message {message_id} of type {message_type}")
        return message_id
        
    async def query_messages(
        self,
        message_types: Optional[List[str]] = None,
        status: str = "unread",
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query messages from the knowledge graph.
        
        Args:
            message_types: Filter by message types
            status: Filter by message status
            since: Filter messages since timestamp
            
        Returns:
            List of messages
        """
        filters = [f"?message core:status '{status}' ."]
        
        if message_types:
            type_filter = " || ".join([
                f"?type = '{t}'" for t in message_types
            ])
            filters.append(f"FILTER({type_filter})")
            
        if since:
            filters.append(f"FILTER(?timestamp > '{since}'^^xsd:dateTime)")
            
        # Check if message targets this agent's capabilities
        filters.append("""
        {
            # No target capabilities specified (broadcast to all)
            FILTER NOT EXISTS { ?message core:targetCapability ?cap }
        } UNION {
            # Message targets one of our capabilities
            ?message core:targetCapability ?targetCap .
            <""" + self.agent_id + """> core:hasCapability ?targetCap .
        }
        """)
        
        filter_clause = "\n".join(filters)
        
        query = f"""
        PREFIX core: <{self.CORE}>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?message ?type ?content ?sender ?timestamp WHERE {{
            ?message a core:Message ;
                    core:messageType ?type ;
                    core:content ?content ;
                    core:sender ?sender ;
                    core:timestamp ?timestamp .
            {filter_clause}
        }}
        ORDER BY DESC(?timestamp)
        """
        
        results = await self.kg.query_graph(query)
        
        # Parse content JSON
        for result in results:
            try:
                result['content'] = json.loads(result['content'])
            except:
                pass
                
        return results
        
    async def mark_message_read(self, message_id: str) -> None:
        """Mark a message as read."""
        # Remove old "unread" status before adding "read"
        await self.kg.remove_triple(message_id, str(self.CORE.status), "unread")
        await self.kg.add_triple(message_id, str(self.CORE.status), "read")
        await self.kg.add_triple(message_id, str(self.CORE.readBy), self.agent_id)
        await self.kg.add_triple(message_id, str(self.CORE.readAt), datetime.utcnow().isoformat())
        
    async def get_task_dependencies(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Get all dependencies for a task.
        
        Args:
            task_id: The task to check
            
        Returns:
            List of dependency tasks with their status
        """
        query = f"""
        PREFIX core: <{self.CORE}>
        SELECT ?dep ?name ?status WHERE {{
            <{task_id}> core:dependsOn ?dep .
            ?dep core:taskName ?name ;
                 core:status ?status .
        }}
        """
        
        results = await self.kg.query_graph(query)
        return results
        
    async def create_capability_node(
        self,
        capability_name: str,
        capability_type: str,
        description: str,
        requirements: Optional[List[str]] = None
    ) -> str:
        """
        Create a new capability that agents can possess.
        
        Args:
            capability_name: Name of the capability
            capability_type: Type of capability
            description: What this capability enables
            requirements: List of prerequisite capabilities
            
        Returns:
            Capability URI
        """
        capability_id = f"{self.CAPABILITY}{capability_name.lower().replace(' ', '_')}"
        
        await self.kg.add_triple(capability_id, str(RDF.type), str(self.CORE.Capability))
        await self.kg.add_triple(capability_id, str(self.CORE.capabilityName), capability_name)
        await self.kg.add_triple(capability_id, str(self.CORE.capabilityType), capability_type)
        await self.kg.add_triple(capability_id, str(self.CORE.description), description)
        
        if requirements:
            for req in requirements:
                await self.kg.add_triple(capability_id, str(self.CORE.requires), req)
                
        self.logger.info(f"Created capability: {capability_id}")
        return capability_id
        
    async def query_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get the status of a workflow and all its tasks.
        
        Args:
            workflow_id: The workflow to check
            
        Returns:
            Workflow status with task details
        """
        query = f"""
        PREFIX core: <{self.CORE}>
        SELECT ?task ?name ?status ?step WHERE {{
            <{workflow_id}> core:hasTask ?task .
            ?task core:taskName ?name ;
                  core:status ?status ;
                  core:stepNumber ?step .
        }}
        ORDER BY ?step
        """
        
        results = await self.kg.query_graph(query)
        
        # Calculate workflow status
        statuses = [r['status'] for r in results]
        if all(s == 'completed' for s in statuses):
            workflow_status = 'completed'
        elif any(s == 'failed' for s in statuses):
            workflow_status = 'failed'
        elif any(s in ['in_progress', 'pending'] for s in statuses):
            workflow_status = 'in_progress'
        else:
            workflow_status = 'unknown'
            
        return {
            'workflow_id': workflow_id,
            'status': workflow_status,
            'tasks': results,
            'total_tasks': len(results),
            'completed_tasks': sum(1 for s in statuses if s == 'completed')
        }


class KGToolRegistry:
    """Registry of KG tools that can be discovered and used by agents."""
    
    @staticmethod
    def get_tool_descriptions() -> Dict[str, Dict[str, Any]]:
        """Get descriptions of all available KG tools."""
        return {
            "create_task_node": {
                "description": "Create a new task in the knowledge graph that can be executed by agents",
                "parameters": {
                    "task_name": "Human-readable name for the task",
                    "task_type": "Type of task (research, code_generation, analysis, etc.)",
                    "description": "Detailed description of what needs to be done",
                    "priority": "Task priority (low, medium, high, critical)",
                    "dependencies": "List of task IDs that must complete first",
                    "metadata": "Additional task-specific metadata"
                },
                "returns": "Task ID (URI) of the created task"
            },
            "create_workflow_node": {
                "description": "Create a workflow that orchestrates multiple tasks",
                "parameters": {
                    "workflow_name": "Name of the workflow",
                    "workflow_type": "Type (sequential, parallel, conditional)",
                    "steps": "List of workflow steps with task definitions",
                    "metadata": "Additional workflow metadata"
                },
                "returns": "Workflow ID (URI)"
            },
            "share_task_with_agents": {
                "description": "Share a task with agents that have required capabilities",
                "parameters": {
                    "task_id": "The task to share",
                    "required_capabilities": "List of capabilities needed",
                    "max_agents": "Maximum number of agents to assign"
                },
                "returns": "List of assigned agent IDs"
            },
            "query_available_tasks": {
                "description": "Find available tasks matching agent capabilities",
                "parameters": {
                    "capabilities": "Filter by required capabilities",
                    "task_types": "Filter by task types",
                    "priority": "Filter by priority level"
                },
                "returns": "List of available tasks with details"
            },
            "claim_task": {
                "description": "Claim a task for execution",
                "parameters": {
                    "task_id": "The task to claim"
                },
                "returns": "True if successfully claimed"
            },
            "update_task_status": {
                "description": "Update the status of a task",
                "parameters": {
                    "task_id": "The task to update",
                    "status": "New status (in_progress, completed, failed, blocked)",
                    "result": "Task execution result (for completed tasks)",
                    "error": "Error message (for failed tasks)"
                }
            },
            "discover_agents": {
                "description": "Discover other agents in the system",
                "parameters": {
                    "capabilities": "Filter by required capabilities",
                    "status": "Filter by agent status"
                },
                "returns": "List of discovered agents"
            },
            "broadcast_message": {
                "description": "Broadcast a message to agents through the KG",
                "parameters": {
                    "message_type": "Type of message",
                    "content": "Message content",
                    "target_capabilities": "Target specific capabilities"
                },
                "returns": "Message ID"
            },
            "query_messages": {
                "description": "Query messages from the knowledge graph",
                "parameters": {
                    "message_types": "Filter by message types",
                    "status": "Filter by message status",
                    "since": "Filter messages since timestamp"
                },
                "returns": "List of messages"
            }
        }
