"""
KG Integration for Midjourney Agent Tools

This module provides integration between the Midjourney agent tools and the 
Knowledge Graph task system, enabling:
1. Task-based image generation
2. Workflow orchestration
3. Result tracking and analytics
"""

from typing import Dict, List, Any, Optional
import json
import uuid
from datetime import datetime
from loguru import logger

from agents.tools.kg_tools import KGTools
from kg.models.graph_manager import KnowledgeGraphManager
from semant.agent_tools.midjourney.kg_logging import KGLogger
from semant.agent_tools.midjourney import REGISTRY as MJ_REGISTRY


class MidjourneyKGIntegration:
    """
    Integrates Midjourney tools with the KG task system.
    
    This allows:
    - Creating image generation tasks in the KG
    - Agents claiming and processing tasks
    - Storing results and metadata in the KG
    - Querying generation history and patterns
    """
    
    def __init__(
        self,
        kg_manager: KnowledgeGraphManager,
        agent_id: str = "midjourney_integration"
    ):
        """
        Initialize the integration.
        
        Args:
            kg_manager: The knowledge graph manager
            agent_id: ID of the agent using this integration
        """
        self.kg = kg_manager
        self.agent_id = agent_id
        self.kg_tools = KGTools(kg_manager, agent_id)
        self.kg_logger = KGLogger(kg=kg_manager, agent_id=agent_id)
        self.mj_tools = {}
        
        # Load all Midjourney tools
        for tool_name, tool_factory in MJ_REGISTRY.items():
            self.mj_tools[tool_name] = tool_factory()
            
        logger.info(f"MidjourneyKGIntegration initialized with {len(self.mj_tools)} tools")
        
    async def create_image_task(
        self,
        prompt: str,
        task_name: Optional[str] = None,
        version: str = "v7",
        aspect_ratio: Optional[str] = None,
        priority: str = "medium",
        additional_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create an image generation task in the KG.
        
        Args:
            prompt: The image generation prompt
            task_name: Optional name for the task
            version: Midjourney version (v6, v7, etc.)
            aspect_ratio: Aspect ratio (16:9, 1:1, etc.)
            priority: Task priority
            additional_params: Additional Midjourney parameters
            
        Returns:
            Task ID
        """
        if not task_name:
            task_name = f"Generate: {prompt[:30]}..."
            
        metadata = {
            "prompt": prompt,
            "version": version,
            "aspect_ratio": aspect_ratio,
            "tool": "mj.imagine",
            **(additional_params or {})
        }
        
        # Create the task
        task_id = await self.kg_tools.create_task_node(
            task_name=task_name,
            task_type="image_generation",
            description=f"Generate image: {prompt}",
            priority=priority,
            metadata=metadata
        )
        
        # Add capability requirement
        await self.kg.add_triple(
            task_id,
            "http://example.org/core#requiresCapability",
            "http://example.org/capability/image_generation"
        )
        
        logger.info(f"Created image task {task_id}: {task_name}")
        return task_id
        
    async def create_book_workflow(
        self,
        title: str,
        pages: List[Dict[str, str]],
        workflow_name: Optional[str] = None
    ) -> str:
        """
        Create a book illustration workflow.
        
        Args:
            title: Book title
            pages: List of pages with title, text, and prompt
            workflow_name: Optional workflow name
            
        Returns:
            Workflow ID
        """
        if not workflow_name:
            workflow_name = f"Book: {title}"
            
        # Create workflow steps for each page
        steps = []
        for i, page in enumerate(pages):
            steps.append({
                "name": f"Illustrate: {page['title']}",
                "type": "image_generation",
                "description": f"Generate illustration for page {i+1}",
                "metadata": {
                    "prompt": page['prompt'],
                    "version": "v7",
                    "aspect_ratio": "16:9",
                    "page_number": i + 1,
                    "page_title": page['title'],
                    "page_text": page['text'],
                    "tool": "mj.imagine"
                }
            })
            
        # Add book compilation step
        steps.append({
            "name": "Compile Book",
            "type": "book_compilation",
            "description": "Compile all illustrations into final book",
            "metadata": {
                "book_title": title,
                "total_pages": len(pages),
                "tool": "mj.book_generator"
            }
        })
        
        # Create the workflow
        workflow_id = await self.kg_tools.create_workflow_node(
            workflow_name=workflow_name,
            workflow_type="sequential",
            steps=steps,
            metadata={
                "book_title": title,
                "total_pages": len(pages),
                "workflow_type": "book_illustration"
            }
        )
        
        logger.info(f"Created book workflow {workflow_id} with {len(steps)} steps")
        return workflow_id
        
    async def process_image_task(self, task_id: str) -> Dict[str, Any]:
        """
        Process an image generation task.
        
        Args:
            task_id: The task to process
            
        Returns:
            Processing result
        """
        # Claim the task
        if not await self.kg_tools.claim_task(task_id):
            return {
                "task_id": task_id,
                "status": "failed",
                "error": "Could not claim task"
            }
            
        try:
            # Get task details
            query = f"""
            PREFIX core: <http://example.org/core#>
            SELECT ?name ?metadata WHERE {{
                <{task_id}> core:taskName ?name ;
                           core:metadata ?metadata .
            }}
            """
            
            results = await self.kg.query_graph(query)
            if not results:
                raise ValueError("Task not found")
                
            task_data = results[0]
            metadata = json.loads(task_data['metadata'])
            
            # Determine which tool to use
            tool_name = metadata.get('tool', 'mj.imagine')
            tool = self.mj_tools.get(tool_name)
            
            if not tool:
                raise ValueError(f"Tool {tool_name} not found")
                
            # Execute the tool
            logger.info(f"Executing {tool_name} for task {task_id}")
            
            if tool_name == "mj.imagine":
                result = await tool.run(
                    prompt=metadata['prompt'],
                    model_version=metadata.get('version', 'v7'),
                    aspect_ratio=metadata.get('aspect_ratio')
                )
            elif tool_name == "mj.action":
                result = await tool.run(
                    task_id=metadata['source_task_id'],
                    action=metadata['action']
                )
            else:
                # Generic tool execution
                result = await tool.run(**metadata)
                
            # Log to KG
            await self.kg_logger.log_tool_call(
                tool_name=tool_name,
                inputs=metadata,
                outputs=result,
                agent_id=self.agent_id
            )
            
            # Update task status
            await self.kg_tools.update_task_status(
                task_id,
                "completed",
                result=result
            )
            
            return {
                "task_id": task_id,
                "status": "completed",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            
            # Mark task as failed
            await self.kg_tools.update_task_status(
                task_id,
                "failed",
                error=str(e)
            )
            
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(e)
            }
            
    async def query_generation_history(
        self,
        limit: int = 10,
        status: Optional[str] = None,
        agent: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query image generation history from the KG.
        
        Args:
            limit: Maximum results to return
            status: Filter by status (completed, failed, etc.)
            agent: Filter by agent ID
            
        Returns:
            List of generation records
        """
        filters = []
        
        if status:
            filters.append(f'?task core:status "{status}" .')
            
        if agent:
            filters.append(f'?task core:assignedTo <http://example.org/agent/{agent}> .')
            
        filter_clause = "\n".join(filters) if filters else ""
        
        query = f"""
        PREFIX core: <http://example.org/core#>
        SELECT ?task ?name ?status ?metadata ?completedAt WHERE {{
            ?task a core:Task ;
                  core:taskType "image_generation" ;
                  core:taskName ?name ;
                  core:status ?status .
            {filter_clause}
            OPTIONAL {{ ?task core:metadata ?metadata }}
            OPTIONAL {{ ?task core:completedAt ?completedAt }}
        }}
        ORDER BY DESC(?completedAt)
        LIMIT {limit}
        """
        
        results = await self.kg.query_graph(query)
        
        # Parse metadata
        for result in results:
            if result.get('metadata'):
                try:
                    result['metadata'] = json.loads(result['metadata'])
                except:
                    pass
                    
        return results
        
    async def get_workflow_images(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Get all images generated for a workflow.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            List of image results
        """
        query = f"""
        PREFIX core: <http://example.org/core#>
        SELECT ?task ?name ?result WHERE {{
            <{workflow_id}> core:hasTask ?task .
            ?task core:taskName ?name ;
                  core:taskType "image_generation" ;
                  core:status "completed" ;
                  core:result ?result .
        }}
        ORDER BY ?task
        """
        
        results = await self.kg.query_graph(query)
        
        # Parse results
        images = []
        for result in results:
            try:
                result_data = json.loads(result['result'])
                images.append({
                    "task": result['task'],
                    "name": result['name'],
                    "image_url": result_data.get('image_url'),
                    "prompt": result_data.get('prompt')
                })
            except:
                pass
                
        return images
        
    async def analyze_generation_patterns(self) -> Dict[str, Any]:
        """
        Analyze image generation patterns from the KG.
        
        Returns:
            Analysis results
        """
        # Query 1: Most common versions
        version_query = """
        PREFIX core: <http://example.org/core#>
        SELECT ?version (COUNT(?task) as ?count) WHERE {
            ?task a core:Task ;
                  core:taskType "image_generation" ;
                  core:metadata ?metadata .
            FILTER(CONTAINS(?metadata, '"version"'))
        }
        GROUP BY ?version
        """
        
        # Query 2: Success rate
        success_query = """
        PREFIX core: <http://example.org/core#>
        SELECT ?status (COUNT(?task) as ?count) WHERE {
            ?task a core:Task ;
                  core:taskType "image_generation" ;
                  core:status ?status .
        }
        GROUP BY ?status
        """
        
        # Query 3: Agent performance
        agent_query = """
        PREFIX core: <http://example.org/core#>
        SELECT ?agent (COUNT(?task) as ?completed) WHERE {
            ?task a core:Task ;
                  core:taskType "image_generation" ;
                  core:status "completed" ;
                  core:assignedTo ?agent .
        }
        GROUP BY ?agent
        ORDER BY DESC(?completed)
        """
        
        # Execute queries
        version_results = await self.kg.query_graph(version_query)
        success_results = await self.kg.query_graph(success_query)
        agent_results = await self.kg.query_graph(agent_query)
        
        # Calculate metrics
        total_tasks = sum(int(r['count']) for r in success_results)
        completed_tasks = next((int(r['count']) for r in success_results if r['status'] == 'completed'), 0)
        success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "success_rate": f"{success_rate:.1f}%",
            "status_distribution": {r['status']: int(r['count']) for r in success_results},
            "top_agents": [
                {
                    "agent": r['agent'].split('/')[-1],
                    "completed": int(r['completed'])
                }
                for r in agent_results[:5]
            ]
        }


# Convenience functions for common operations

async def create_image_generation_plan(
    kg_manager: KnowledgeGraphManager,
    project_name: str,
    image_specs: List[Dict[str, Any]]
) -> str:
    """
    Create a complete image generation plan in the KG.
    
    Args:
        kg_manager: The KG manager
        project_name: Name of the project
        image_specs: List of image specifications
        
    Returns:
        Workflow ID
    """
    integration = MidjourneyKGIntegration(kg_manager)
    
    # Create workflow steps
    steps = []
    for spec in image_specs:
        steps.append({
            "name": spec.get("name", "Generate Image"),
            "type": "image_generation",
            "description": spec.get("description", ""),
            "metadata": {
                "prompt": spec["prompt"],
                "version": spec.get("version", "v7"),
                "aspect_ratio": spec.get("aspect_ratio"),
                "tool": "mj.imagine"
            }
        })
        
    # Create workflow
    kg_tools = KGTools(kg_manager, "planner")
    workflow_id = await kg_tools.create_workflow_node(
        workflow_name=f"Project: {project_name}",
        workflow_type="parallel",  # Images can be generated in parallel
        steps=steps,
        metadata={
            "project": project_name,
            "total_images": len(image_specs)
        }
    )
    
    logger.info(f"Created image generation plan {workflow_id} for {project_name}")
    return workflow_id


async def process_pending_image_tasks(
    kg_manager: KnowledgeGraphManager,
    agent_id: str,
    max_tasks: int = 5
) -> List[Dict[str, Any]]:
    """
    Process pending image generation tasks.
    
    Args:
        kg_manager: The KG manager
        agent_id: ID of the processing agent
        max_tasks: Maximum tasks to process
        
    Returns:
        List of results
    """
    integration = MidjourneyKGIntegration(kg_manager, agent_id)
    kg_tools = KGTools(kg_manager, agent_id)
    
    # Query for pending tasks
    tasks = await kg_tools.query_available_tasks(
        task_types=["image_generation"],
        priority="high"
    )
    
    results = []
    for task in tasks[:max_tasks]:
        logger.info(f"Processing task: {task['name']}")
        result = await integration.process_image_task(task['task'])
        results.append(result)
        
    return results
