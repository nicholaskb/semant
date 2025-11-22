#!/usr/bin/env python3
"""
KG Tools + Midjourney Integration Demo

This demonstrates how the new KG tools work with the existing Midjourney 
integration to create a powerful image generation workflow system where:

1. Agents can create image generation tasks in the KG
2. Specialized Midjourney agents claim and execute these tasks
3. Results are stored back in the KG for other agents to use
4. Complex workflows orchestrate multi-step image projects
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger

# KG and agent imports
from kg.models.graph_manager import KnowledgeGraphManager
from agents.tools.kg_tools import KGTools
from agents.domain.kg_orchestrator_agent import KGOrchestratorAgent
from agents.core.base_agent import BaseAgent
from agents.core.message_types import AgentMessage

# Midjourney imports
from midjourney_integration.client import MidjourneyClient
from semant.agent_tools.midjourney import REGISTRY as MJ_REGISTRY
from semant.agent_tools.midjourney.kg_logging import KGLogger


class MidjourneyKGAgent(BaseAgent):
    """
    Agent that bridges Midjourney tools with the KG task system.
    It can:
    1. Query the KG for image generation tasks
    2. Execute them using Midjourney tools
    3. Store results back in the KG
    """
    
    def __init__(self, agent_id: str = "midjourney_kg_agent"):
        super().__init__(agent_id, "image_generator")
        self.kg_tools: Optional[KGTools] = None
        self.mj_client: Optional[MidjourneyClient] = None
        self.mj_tools = {}
        self.kg_logger: Optional[KGLogger] = None
        
    async def initialize(self) -> None:
        """Initialize the agent with KG and Midjourney tools."""
        await super().initialize()
        
        if self.knowledge_graph:
            # Initialize KG tools
            self.kg_tools = KGTools(self.knowledge_graph, self.agent_id)
            
            # Initialize KG logger for Midjourney
            self.kg_logger = KGLogger(kg=self.knowledge_graph, agent_id=self.agent_id)
            
            # Register capabilities
            await self._register_capabilities()
            
            # Initialize Midjourney client if token available
            if os.getenv("MIDJOURNEY_API_TOKEN"):
                self.mj_client = MidjourneyClient()
                
                # Load Midjourney tools from registry
                for tool_name, tool_factory in MJ_REGISTRY.items():
                    self.mj_tools[tool_name] = tool_factory()
                    
                logger.info(f"Loaded {len(self.mj_tools)} Midjourney tools")
            else:
                logger.warning("MIDJOURNEY_API_TOKEN not set - operating in simulation mode")
                
    async def _register_capabilities(self) -> None:
        """Register agent capabilities in the KG."""
        capabilities = [
            ("image_generation", "midjourney", "Generate images from text prompts"),
            ("image_upscaling", "midjourney", "Upscale generated images"),
            ("image_variation", "midjourney", "Create variations of images"),
            ("image_description", "midjourney", "Describe images in detail"),
            ("workflow_execution", "orchestration", "Execute image generation workflows")
        ]
        
        cap_uris = []
        for cap_name, cap_type, description in capabilities:
            cap_uri = await self.kg_tools.create_capability_node(
                cap_name, cap_type, description
            )
            cap_uris.append(cap_uri)
            
        # Register agent with capabilities
        agent_uri = f"http://example.org/agent/{self.agent_id}"
        await self.kg_tools.kg.add_triple(agent_uri, "rdf:type", "http://example.org/core#Agent")
        await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#agentName", self.agent_id)
        await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#agentType", "image_generator")
        await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#status", "active")
        
        for cap_uri in cap_uris:
            await self.kg_tools.kg.add_triple(agent_uri, "http://example.org/core#hasCapability", cap_uri)
            
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        if message.message_type == "generate_image":
            return await self._handle_generate_image(message)
        elif message.message_type == "process_workflow":
            return await self._handle_workflow(message)
        else:
            return AgentMessage(
                sender_id=self.agent_id,
                message_type="acknowledgment",
                content={"status": "received", "message_type": message.message_type}
            )
            
    async def _handle_generate_image(self, message: AgentMessage) -> AgentMessage:
        """Handle direct image generation request."""
        prompt = message.content.get("prompt", "")
        version = message.content.get("version", "v7")
        aspect_ratio = message.content.get("aspect_ratio")
        
        if not self.mj_client:
            # Simulation mode
            result = {
                "task_id": f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "status": "simulated",
                "prompt": prompt,
                "image_url": f"https://simulated.image/{prompt.replace(' ', '_')}.png"
            }
        else:
            # Real Midjourney generation
            imagine_tool = self.mj_tools.get("mj.imagine")
            if not imagine_tool:
                return self._create_error_response("Imagine tool not available")
                
            result = await imagine_tool.run(
                prompt=prompt,
                model_version=version,
                aspect_ratio=aspect_ratio
            )
            
        # Log to KG
        if self.kg_logger:
            await self.kg_logger.log_tool_call(
                tool_name="mj.imagine",
                inputs={"prompt": prompt, "version": version},
                outputs=result,
                agent_id=self.agent_id
            )
            
        return AgentMessage(
            sender_id=self.agent_id,
            message_type="image_generated",
            content=result
        )
        
    async def _handle_workflow(self, message: AgentMessage) -> AgentMessage:
        """Handle workflow processing request."""
        workflow_id = message.content.get("workflow_id")
        
        if not workflow_id or not self.kg_tools:
            return self._create_error_response("Invalid workflow request")
            
        # Get workflow status from KG
        status = await self.kg_tools.query_workflow_status(workflow_id)
        
        results = []
        for task in status['tasks']:
            if task['status'] == 'pending':
                # Process this task
                task_result = await self._process_image_task(task['task'])
                results.append(task_result)
                
        return AgentMessage(
            sender_id=self.agent_id,
            message_type="workflow_processed",
            content={
                "workflow_id": workflow_id,
                "processed_tasks": len(results),
                "results": results
            }
        )
        
    async def _process_image_task(self, task_id: str) -> Dict[str, Any]:
        """Process a single image generation task from the KG."""
        # Get task details
        query = f"""
        PREFIX core: <http://example.org/core#>
        SELECT ?name ?description ?metadata WHERE {{
            <{task_id}> core:taskName ?name ;
                       core:description ?description .
            OPTIONAL {{ <{task_id}> core:metadata ?metadata }}
        }}
        """
        
        results = await self.kg_tools.kg.query_graph(query)
        if not results:
            return {"task_id": task_id, "error": "Task not found"}
            
        task_data = results[0]
        metadata = json.loads(task_data.get('metadata', '{}'))
        
        # Claim the task
        if not await self.kg_tools.claim_task(task_id):
            return {"task_id": task_id, "error": "Could not claim task"}
            
        try:
            # Generate image based on task
            prompt = metadata.get('prompt', task_data['description'])
            
            if self.mj_client and "mj.imagine" in self.mj_tools:
                # Real generation
                imagine_tool = self.mj_tools["mj.imagine"]
                result = await imagine_tool.run(
                    prompt=prompt,
                    model_version=metadata.get('version', 'v7'),
                    aspect_ratio=metadata.get('aspect_ratio')
                )
            else:
                # Simulation
                result = {
                    "status": "completed",
                    "image_url": f"https://simulated.image/{task_id}.png",
                    "prompt": prompt
                }
                
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
            
    async def work_loop(self):
        """Main work loop - continuously check for and process image tasks."""
        while True:
            try:
                # Query for available image generation tasks
                tasks = await self.kg_tools.query_available_tasks(
                    task_types=["image_generation", "midjourney"],
                    capabilities=["http://example.org/capability/image_generation"]
                )
                
                if tasks:
                    logger.info(f"Found {len(tasks)} image generation tasks")
                    
                    for task in tasks[:3]:  # Process up to 3 tasks at a time
                        task_id = task['task']
                        logger.info(f"Processing task: {task['name']}")
                        
                        result = await self._process_image_task(task_id)
                        logger.info(f"Task {task_id} result: {result['status']}")
                        
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in work loop: {e}")
                await asyncio.sleep(10)


async def demo_basic_midjourney_kg_integration():
    """Demonstrate basic Midjourney + KG integration."""
    logger.info("=== Basic Midjourney + KG Integration Demo ===")
    
    # Initialize KG
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    # Create orchestrator
    orchestrator = KGOrchestratorAgent("image_orchestrator")
    orchestrator.knowledge_graph = kg
    await orchestrator.initialize()
    
    # Create Midjourney KG agent
    mj_agent = MidjourneyKGAgent()
    mj_agent.knowledge_graph = kg
    await mj_agent.initialize()
    
    # Create a simple image generation task
    logger.info("\n1. Creating image generation task...")
    create_task_msg = AgentMessage(
        sender_id="demo",
        message_type="create_task",
        content={
            "name": "Generate Hero Image",
            "type": "image_generation",
            "description": "Generate a hero image for the website",
            "priority": "high",
            "metadata": {
                "prompt": "futuristic city skyline at sunset, cyberpunk aesthetic, neon lights",
                "version": "v7",
                "aspect_ratio": "16:9"
            },
            "required_capabilities": ["image_generation"],
            "auto_assign": True
        }
    )
    
    response = await orchestrator.process_message(create_task_msg)
    task_id = response.content['task_id']
    logger.info(f"Created task: {task_id}")
    
    # Process the task
    logger.info("\n2. Processing image generation task...")
    result = await mj_agent._process_image_task(task_id)
    logger.info(f"Task result: {json.dumps(result, indent=2)}")
    
    return kg, orchestrator, mj_agent


async def demo_image_workflow():
    """Demonstrate a complex image generation workflow."""
    logger.info("\n=== Image Generation Workflow Demo ===")
    
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    orchestrator = KGOrchestratorAgent("workflow_orchestrator")
    orchestrator.knowledge_graph = kg
    await orchestrator.initialize()
    
    # Create a multi-step image workflow
    logger.info("\n1. Creating image generation workflow...")
    workflow_msg = AgentMessage(
        sender_id="demo",
        message_type="create_workflow",
        content={
            "name": "Product Image Pipeline",
            "type": "sequential",
            "steps": [
                {
                    "name": "Generate Base Product Image",
                    "type": "image_generation",
                    "description": "Create the main product visualization",
                    "metadata": {
                        "prompt": "sleek modern smartphone, minimalist design, white background",
                        "version": "v7",
                        "aspect_ratio": "1:1"
                    }
                },
                {
                    "name": "Generate Lifestyle Shot",
                    "type": "image_generation",
                    "description": "Create lifestyle context image",
                    "metadata": {
                        "prompt": "person using smartphone in coffee shop, natural lighting",
                        "version": "v7",
                        "aspect_ratio": "16:9"
                    }
                },
                {
                    "name": "Generate Feature Highlight",
                    "type": "image_generation",
                    "description": "Highlight key product features",
                    "metadata": {
                        "prompt": "smartphone screen showing advanced features, tech visualization",
                        "version": "v7",
                        "aspect_ratio": "16:9"
                    }
                }
            ]
        }
    )
    
    response = await orchestrator.process_message(workflow_msg)
    workflow_id = response.content['workflow_id']
    logger.info(f"Created workflow: {workflow_id}")
    
    # Get workflow status
    status = await orchestrator.kg_tools.query_workflow_status(workflow_id)
    logger.info(f"Workflow has {status['total_tasks']} tasks")
    
    # Create Midjourney agent to process the workflow
    mj_agent = MidjourneyKGAgent()
    mj_agent.knowledge_graph = kg
    await mj_agent.initialize()
    
    # Process workflow tasks
    logger.info("\n2. Processing workflow tasks...")
    process_msg = AgentMessage(
        sender_id="demo",
        message_type="process_workflow",
        content={"workflow_id": workflow_id}
    )
    
    response = await mj_agent.process_message(process_msg)
    logger.info(f"Processed {response.content['processed_tasks']} tasks")
    
    # Check final workflow status
    final_status = await orchestrator.kg_tools.query_workflow_status(workflow_id)
    logger.info(f"Workflow status: {final_status['status']}")
    logger.info(f"Completed tasks: {final_status['completed_tasks']}/{final_status['total_tasks']}")
    
    return kg, orchestrator, mj_agent


async def demo_book_generation_workflow():
    """Demonstrate book generation using KG orchestration."""
    logger.info("\n=== Book Generation Workflow Demo ===")
    
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    orchestrator = KGOrchestratorAgent("book_orchestrator")
    orchestrator.knowledge_graph = kg
    await orchestrator.initialize()
    
    # Create a book generation workflow
    logger.info("\n1. Creating book illustration workflow...")
    
    book_pages = [
        {
            "title": "The Adventure Begins",
            "text": "Once upon a time, in a magical forest...",
            "prompt": "magical forest with glowing trees, fairy tale style, whimsical"
        },
        {
            "title": "Meeting the Dragon",
            "text": "A friendly dragon appeared from behind the trees...",
            "prompt": "friendly cartoon dragon in forest, children's book illustration"
        },
        {
            "title": "The Journey",
            "text": "Together they flew over mountains and valleys...",
            "prompt": "dragon and child flying over landscape, adventure, children's book style"
        }
    ]
    
    # Create workflow with tasks for each page
    steps = []
    for i, page in enumerate(book_pages):
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
                "page_text": page['text']
            }
        })
        
    workflow_msg = AgentMessage(
        sender_id="demo",
        message_type="create_workflow",
        content={
            "name": "Children's Book Illustrations",
            "type": "sequential",
            "steps": steps,
            "metadata": {
                "book_title": "The Dragon's Adventure",
                "total_pages": len(book_pages)
            }
        }
    )
    
    response = await orchestrator.process_message(workflow_msg)
    workflow_id = response.content['workflow_id']
    logger.info(f"Created book workflow: {workflow_id}")
    
    # Query workflow details using SPARQL
    logger.info("\n2. Querying workflow details via SPARQL...")
    query = f"""
    PREFIX core: <http://example.org/core#>
    SELECT ?task ?name ?metadata WHERE {{
        <{workflow_id}> core:hasTask ?task .
        ?task core:taskName ?name ;
              core:metadata ?metadata .
    }}
    ORDER BY ?task
    """
    
    results = await kg.query_graph(query)
    logger.info(f"Book workflow has {len(results)} illustration tasks")
    
    for result in results:
        metadata = json.loads(result['metadata'])
        logger.info(f"  Page {metadata['page_number']}: {metadata['page_title']}")
        
    return kg, orchestrator, workflow_id


async def demo_multi_agent_image_coordination():
    """Demonstrate multiple agents coordinating on image tasks."""
    logger.info("\n=== Multi-Agent Image Coordination Demo ===")
    
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    orchestrator = KGOrchestratorAgent("coordinator")
    orchestrator.knowledge_graph = kg
    await orchestrator.initialize()
    
    # Create multiple specialized image agents
    agents = []
    for i in range(3):
        agent = MidjourneyKGAgent(f"image_agent_{i}")
        agent.knowledge_graph = kg
        await agent.initialize()
        agents.append(agent)
        logger.info(f"Created {agent.agent_id}")
        
    # Create a batch of image tasks
    logger.info("\n1. Creating batch of image tasks...")
    
    image_prompts = [
        ("Logo Design", "minimalist tech company logo, geometric shapes"),
        ("Banner Image", "website banner, modern gradient, abstract"),
        ("Icon Set", "flat design icons for mobile app, consistent style"),
        ("Background Pattern", "subtle geometric pattern, light colors"),
        ("Hero Illustration", "isometric illustration of cloud computing")
    ]
    
    task_ids = []
    for title, prompt in image_prompts:
        create_msg = AgentMessage(
            sender_id="demo",
            message_type="create_task",
            content={
                "name": title,
                "type": "image_generation",
                "description": f"Generate {title.lower()}",
                "priority": "medium",
                "metadata": {
                    "prompt": prompt,
                    "version": "v7"
                },
                "required_capabilities": ["image_generation"]
            }
        )
        
        response = await orchestrator.process_message(create_msg)
        task_ids.append(response.content['task_id'])
        
    logger.info(f"Created {len(task_ids)} image tasks")
    
    # Agents work in parallel
    logger.info("\n2. Agents processing tasks in parallel...")
    
    async def agent_work(agent, max_tasks=2):
        processed = 0
        for _ in range(max_tasks):
            # Query for available tasks
            tasks = await agent.kg_tools.query_available_tasks(
                task_types=["image_generation"]
            )
            
            if tasks:
                task = tasks[0]
                logger.info(f"{agent.agent_id} processing: {task['name']}")
                result = await agent._process_image_task(task['task'])
                processed += 1
                
        return processed
        
    # Run agents in parallel
    work_tasks = [agent_work(agent) for agent in agents]
    results = await asyncio.gather(*work_tasks)
    
    total_processed = sum(results)
    logger.info(f"Agents processed {total_processed} tasks total")
    
    # Query completion status
    logger.info("\n3. Checking task completion status...")
    
    status_query = """
    PREFIX core: <http://example.org/core#>
    SELECT ?status (COUNT(?task) as ?count) WHERE {
        ?task a core:Task ;
              core:taskType "image_generation" ;
              core:status ?status .
    }
    GROUP BY ?status
    """
    
    status_results = await kg.query_graph(status_query)
    
    logger.info("Task status summary:")
    for result in status_results:
        logger.info(f"  {result['status']}: {result['count']} tasks")
        
    return kg, orchestrator, agents


async def demo_sparql_image_analytics():
    """Demonstrate using SPARQL to analyze image generation patterns."""
    logger.info("\n=== SPARQL Image Analytics Demo ===")
    
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    
    # Run various SPARQL queries to analyze image generation
    
    # Query 1: Find all completed image tasks with their prompts
    logger.info("\n1. Completed image generation tasks:")
    query1 = """
    PREFIX core: <http://example.org/core#>
    SELECT ?task ?name ?metadata WHERE {
        ?task a core:Task ;
              core:taskType "image_generation" ;
              core:status "completed" ;
              core:taskName ?name ;
              core:metadata ?metadata .
    }
    LIMIT 5
    """
    
    results = await kg.query_graph(query1)
    for result in results:
        metadata = json.loads(result.get('metadata', '{}'))
        logger.info(f"  {result['name']}: {metadata.get('prompt', 'N/A')[:50]}...")
        
    # Query 2: Agent performance metrics
    logger.info("\n2. Agent performance metrics:")
    query2 = """
    PREFIX core: <http://example.org/core#>
    SELECT ?agent (COUNT(?task) as ?completed_tasks) WHERE {
        ?task a core:Task ;
              core:status "completed" ;
              core:assignedTo ?agent .
        ?agent core:agentType "image_generator" .
    }
    GROUP BY ?agent
    ORDER BY DESC(?completed_tasks)
    """
    
    results = await kg.query_graph(query2)
    for result in results:
        agent_name = result['agent'].split('/')[-1]
        logger.info(f"  {agent_name}: {result['completed_tasks']} tasks completed")
        
    # Query 3: Workflow completion rates
    logger.info("\n3. Workflow completion analysis:")
    query3 = """
    PREFIX core: <http://example.org/core#>
    SELECT ?workflow ?name 
           (COUNT(?task) as ?total_tasks)
           (COUNT(?completed) as ?completed_tasks) WHERE {
        ?workflow a core:Workflow ;
                  core:workflowName ?name ;
                  core:hasTask ?task .
        OPTIONAL {
            ?task core:status "completed" .
            BIND(?task as ?completed)
        }
    }
    GROUP BY ?workflow ?name
    """
    
    results = await kg.query_graph(query3)
    for result in results:
        completion_rate = (int(result['completed_tasks']) / int(result['total_tasks']) * 100) if int(result['total_tasks']) > 0 else 0
        logger.info(f"  {result['name']}: {completion_rate:.0f}% complete ({result['completed_tasks']}/{result['total_tasks']})")
        
    # Query 4: Most common image generation parameters
    logger.info("\n4. Common image generation parameters:")
    query4 = """
    PREFIX core: <http://example.org/core#>
    SELECT ?version (COUNT(?task) as ?usage_count) WHERE {
        ?task a core:Task ;
              core:taskType "image_generation" ;
              core:metadata ?metadata .
        FILTER(CONTAINS(?metadata, '"version"'))
    }
    GROUP BY ?version
    """
    
    # Note: This is a simplified query. In practice, you'd parse the JSON metadata
    
    return kg


async def main():
    """Run all Midjourney + KG integration demonstrations."""
    kg_instances = []
    try:
        logger.info("=== Midjourney + KG Tools Integration Demo ===")
        logger.info("This demonstrates how KG tools enable orchestration of Midjourney image generation\n")
        
        # Basic integration
        kg, _, _ = await demo_basic_midjourney_kg_integration()
        kg_instances.append(kg)
        
        # Image workflow
        kg, _, _ = await demo_image_workflow()
        kg_instances.append(kg)
        
        # Book generation workflow
        kg, _, _ = await demo_book_generation_workflow()
        kg_instances.append(kg)
        
        # Multi-agent coordination
        kg, _, _ = await demo_multi_agent_image_coordination()
        kg_instances.append(kg)
        
        # Analytics
        kg = await demo_sparql_image_analytics()
        kg_instances.append(kg)
        
        logger.info("\n=== All Midjourney + KG demonstrations completed ===")
        logger.info("The KG now contains tasks, workflows, and results from all image generation activities")
        logger.info("Agents can query this data to learn patterns and improve future generations")
        
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
    # Note: Set MIDJOURNEY_API_TOKEN environment variable for real generation
    # Without it, the demo runs in simulation mode
    asyncio.run(main())
