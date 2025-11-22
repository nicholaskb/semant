"""
KG Orchestrator Agent

This agent specializes in using the knowledge graph to:
1. Dynamically create and manage tasks and workflows
2. Coordinate work between multiple agents
3. Build and execute complex plans using KG nodes
"""

from typing import Any, Dict, List, Optional, Set
from agents.core.base_agent import BaseAgent
from agents.core.message_types import AgentMessage
from agents.core.capability_types import Capability
from agents.tools.kg_tools import KGTools, KGToolRegistry
from loguru import logger
import json
import uuid


class KGOrchestratorAgent(BaseAgent):
    """Agent that orchestrates work through the knowledge graph."""
    
    def __init__(self, agent_id: str = "kg_orchestrator", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, "orchestrator", config)
        self.kg_tools: Optional[KGTools] = None
        
    async def initialize(self) -> None:
        """Initialize the agent and KG tools."""
        await super().initialize()
        
        if self.knowledge_graph:
            self.kg_tools = KGTools(self.knowledge_graph, self.agent_id)
            self.logger.info("KG Orchestrator Agent initialized with KG tools")
            
            # Register ourselves in the KG
            await self._register_in_kg()
        else:
            self.logger.warning("No knowledge graph available - operating in limited mode")
            
    async def _register_in_kg(self) -> None:
        """Register this agent in the knowledge graph."""
        if not self.kg_tools:
            return
            
        # Define our capabilities
        capabilities = [
            "http://example.org/capability/task_creation",
            "http://example.org/capability/workflow_orchestration",
            "http://example.org/capability/agent_coordination",
            "http://example.org/capability/kg_management"
        ]
        
        # Create capability nodes if they don't exist
        await self.kg_tools.create_capability_node(
            "task_creation",
            "orchestration",
            "Ability to create and manage tasks in the knowledge graph"
        )
        
        await self.kg_tools.create_capability_node(
            "workflow_orchestration",
            "orchestration",
            "Ability to create and manage complex workflows"
        )
        
        await self.kg_tools.create_capability_node(
            "agent_coordination",
            "orchestration",
            "Ability to coordinate work between multiple agents"
        )
        
        await self.kg_tools.create_capability_node(
            "kg_management",
            "core",
            "Ability to manage and extend the knowledge graph"
        )
        
        # Register ourselves
        agent_uri = f"http://example.org/agent/{self.agent_id}"
        await self.kg_tools.kg.add_triple(agent_uri, "rdf:type", "http://example.org/core#Agent")
        await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#agentName", self.agent_id)
        await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#agentType", "orchestrator")
        await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#status", "active")
        
        for cap in capabilities:
            await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#hasCapability", cap)
            
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        try:
            if message.message_type == "create_task":
                return await self._handle_create_task(message)
            elif message.message_type == "create_workflow":
                return await self._handle_create_workflow(message)
            elif message.message_type == "orchestrate_agents":
                return await self._handle_orchestrate_agents(message)
            elif message.message_type == "query_tasks":
                return await self._handle_query_tasks(message)
            elif message.message_type == "execute_workflow":
                return await self._handle_execute_workflow(message)
            elif message.message_type == "kg_tool":
                return await self._handle_kg_tool(message)
            else:
                return await self._handle_unknown_message(message)
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                message_type="error",
                content={"error": str(e)},
                metadata={"original_message": message.message_type}
            )
            
    async def _handle_create_task(self, message: AgentMessage) -> AgentMessage:
        """Handle task creation request."""
        if not self.kg_tools:
            return self._create_error_response("KG tools not available", message.sender_id)
            
        content = message.content
        task_id = await self.kg_tools.create_task_node(
            task_name=content.get("name", "Unnamed Task"),
            task_type=content.get("type", "generic"),
            description=content.get("description", ""),
            priority=content.get("priority", "medium"),
            dependencies=content.get("dependencies", []),
            metadata=content.get("metadata", {})
        )
        
        # Auto-share with capable agents if requested
        if content.get("auto_assign", False) and content.get("required_capabilities"):
            assigned_agents = await self.kg_tools.share_task_with_agents(
                task_id,
                content["required_capabilities"],
                content.get("max_agents", 1)
            )
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                message_type="task_created",
                content={
                    "task_id": task_id,
                    "assigned_agents": assigned_agents,
                    "status": "assigned" if assigned_agents else "pending"
                }
            )
            
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="task_created",
            content={"task_id": task_id, "status": "pending"}
        )
        
    async def _handle_create_workflow(self, message: AgentMessage) -> AgentMessage:
        """Handle workflow creation request."""
        if not self.kg_tools:
            return self._create_error_response("KG tools not available", message.sender_id)
            
        content = message.content
        workflow_id = await self.kg_tools.create_workflow_node(
            workflow_name=content.get("name", "Unnamed Workflow"),
            workflow_type=content.get("type", "sequential"),
            steps=content.get("steps", []),
            metadata=content.get("metadata", {})
        )
        
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            message_type="workflow_created",
            content={"workflow_id": workflow_id}
        )
        
    async def _handle_orchestrate_agents(self, message: AgentMessage) -> AgentMessage:
        """Handle agent orchestration request."""
        if not self.kg_tools:
            return self._create_error_response("KG tools not available", message.sender_id)
            
        content = message.content
        operation = content.get("operation")
        
        if operation == "discover":
            # Discover agents with specific capabilities
            agents = await self.kg_tools.discover_agents(
                capabilities=content.get("capabilities"),
                status=content.get("status", "active")
            )
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id if hasattr(message, 'sender_id') else "system",
                message_type="agents_discovered",
                content={"agents": agents}
            )
            
        elif operation == "broadcast":
            # Broadcast message to agents
            message_id = await self.kg_tools.broadcast_message(
                message_type=content.get("message_type", "notification"),
                content=content.get("message_content", {}),
                target_capabilities=content.get("target_capabilities")
            )
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id if hasattr(message, 'sender_id') else "system",
                message_type="message_broadcast",
                content={"message_id": message_id}
            )
            
        elif operation == "create_agent":
            # Create new agent node
            agent_id = await self.kg_tools.create_agent_node(
                agent_name=content.get("name", "Unnamed Agent"),
                agent_type=content.get("type", "generic"),
                capabilities=content.get("capabilities", []),
                metadata=content.get("metadata", {})
            )
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id if hasattr(message, 'sender_id') else "system",
                message_type="agent_created",
                content={"agent_id": agent_id}
            )
            
        else:
            return self._create_error_response(f"Unknown orchestration operation: {operation}", message.sender_id if hasattr(message, 'sender_id') else "system")
            
    async def _handle_query_tasks(self, message: AgentMessage) -> AgentMessage:
        """Handle task query request."""
        if not self.kg_tools:
            return self._create_error_response("KG tools not available", message.sender_id)
            
        content = message.content
        tasks = await self.kg_tools.query_available_tasks(
            capabilities=content.get("capabilities"),
            task_types=content.get("task_types"),
            priority=content.get("priority")
        )
        
        return AgentMessage(
            sender_id=self.agent_id,
            message_type="tasks_found",
            content={"tasks": tasks}
        )
        
    async def _handle_execute_workflow(self, message: AgentMessage) -> AgentMessage:
        """Handle workflow execution request."""
        if not self.kg_tools:
            return self._create_error_response("KG tools not available", message.sender_id)
            
        workflow_id = message.content.get("workflow_id")
        if not workflow_id:
            return self._create_error_response("workflow_id required")
            
        # Get workflow status
        status = await self.kg_tools.query_workflow_status(workflow_id)
        
        # If workflow is not started, begin execution
        if status['status'] == 'unknown' or all(t['status'] == 'pending' for t in status['tasks']):
            # Find agents and assign tasks
            for task in status['tasks']:
                task_id = task['task']
                
                # Query task details to get required capabilities
                query = f"""
                PREFIX core: <http://example.org/core#>
                SELECT ?cap WHERE {{
                    <{task_id}> core:requiresCapability ?cap .
                }}
                """
                
                cap_results = await self.kg_tools.kg.query_graph(query)
                if cap_results:
                    capabilities = [r['cap'] for r in cap_results]
                    await self.kg_tools.share_task_with_agents(task_id, capabilities)
                    
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id if hasattr(message, 'sender_id') else "system",
                message_type="workflow_started",
                content={"workflow_id": workflow_id, "status": status}
            )
            
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id if hasattr(message, 'sender_id') else "system",
            message_type="workflow_status",
            content={"workflow_id": workflow_id, "status": status}
        )
        
    async def _handle_kg_tool(self, message: AgentMessage) -> AgentMessage:
        """Handle direct KG tool invocation."""
        if not self.kg_tools:
            return self._create_error_response("KG tools not available", message.sender_id)
            
        tool_name = message.content.get("tool")
        params = message.content.get("parameters", {})
        
        # Get tool method
        if not hasattr(self.kg_tools, tool_name):
            available_tools = list(KGToolRegistry.get_tool_descriptions().keys())
            return self._create_error_response(
                f"Unknown tool: {tool_name}. Available tools: {available_tools}"
            )
            
        try:
            # Execute tool
            tool_method = getattr(self.kg_tools, tool_name)
            result = await tool_method(**params)
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id if hasattr(message, 'sender_id') else "system",
                message_type="kg_tool_result",
                content={
                    "tool": tool_name,
                    "result": result,
                    "success": True
                }
            )
        except Exception as e:
            self.logger.error(f"Error executing KG tool {tool_name}: {e}")
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id if hasattr(message, 'sender_id') else "system",
                message_type="kg_tool_result",
                content={
                    "tool": tool_name,
                    "error": str(e),
                    "success": False
                }
            )
            
    async def _handle_unknown_message(self, message: AgentMessage) -> AgentMessage:
        """Handle unknown message types."""
        available_types = [
            "create_task", "create_workflow", "orchestrate_agents",
            "query_tasks", "execute_workflow", "kg_tool"
        ]
        
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id if hasattr(message, 'sender_id') else "system",
            message_type="error",
            content={
                "error": f"Unknown message type: {message.message_type}",
                "available_types": available_types,
                "kg_tools": list(KGToolRegistry.get_tool_descriptions().keys())
            }
        )
        
    def _create_error_response(self, error: str, recipient_id: str = None) -> AgentMessage:
        """Create an error response message."""
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=recipient_id or "system",
            message_type="error",
            content={"error": error}
        )
    
    def _create_response(self, message_type: str, content: Dict[str, Any], recipient_id: str) -> AgentMessage:
        """Create a response message."""
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            message_type=message_type,
            content=content
        )
        
    async def get_capabilities(self) -> Set[Capability]:
        """Get agent capabilities - returns the Set from parent class."""
        return await super().get_capabilities()
    
    async def get_capabilities_dict(self) -> Dict[str, Any]:
        """Get agent capabilities as a dictionary for external use."""
        base_capabilities = await super().get_capabilities()
        
        # Convert base capabilities to dict format
        base_cap_dict = {
            "base_capabilities": [
                {"type": cap.type.value, "version": cap.version}
                for cap in base_capabilities
            ]
        }
        
        kg_capabilities = {
            "kg_tools": {
                "available": self.kg_tools is not None,
                "tools": list(KGToolRegistry.get_tool_descriptions().keys()) if self.kg_tools else []
            },
            "message_types": [
                "create_task", "create_workflow", "orchestrate_agents",
                "query_tasks", "execute_workflow", "kg_tool"
            ],
            "orchestration": {
                "task_management": True,
                "workflow_creation": True,
                "agent_discovery": True,
                "message_broadcasting": True,
                "dynamic_agent_creation": True
            }
        }
        
        return {**base_cap_dict, **kg_capabilities}
        
    async def create_and_execute_plan(self, plan_description: str, steps: List[Dict[str, Any]]) -> str:
        """
        High-level method to create and execute a complete plan.
        
        Args:
            plan_description: Description of what the plan should accomplish
            steps: List of step definitions
            
        Returns:
            Workflow ID
        """
        if not self.kg_tools:
            raise RuntimeError("KG tools not available")
            
        # Create workflow
        workflow_id = await self.kg_tools.create_workflow_node(
            workflow_name=f"Plan: {plan_description[:50]}",
            workflow_type="sequential",
            steps=steps,
            metadata={
                "description": plan_description,
                "created_by": self.agent_id
            }
        )
        
        # Execute workflow
        execute_msg = AgentMessage(
            sender_id="system",
            recipient_id=self.agent_id,
            message_type="execute_workflow",
            content={"workflow_id": workflow_id}
        )
        
        await self._handle_execute_workflow(execute_msg)
        
        return workflow_id
