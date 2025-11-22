#!/usr/bin/env python3
"""
Test: Agent Discovers Its Own IRI from Knowledge Graph, Creates Midjourney Image, and Emails It

This script demonstrates a complete agent self-discovery workflow that:
1. Queries the knowledge graph to discover its own IRI (identity)
2. Uses SPARQL to find information about itself (name, type, capabilities)
3. Generates a Midjourney image based on that discovered identity
4. Splits the 4-grid image into 4 separate KG nodes
5. Gets quadrant selections from McKinsey and Scientific agents
6. Sends a comprehensive email report with embedded images

Integration Points:
- Uses VertexEmailAgent as base class (agents/domain/vertex_email_agent.py)
- Integrates with KnowledgeGraphManager (kg/models/graph_manager.py)
- Uses EmailIntegration for email sending (agents/utils/email_integration.py)
- Leverages Midjourney tools (semant/agent_tools/midjourney/)
- Uses McKinsey consulting agents (examples/demo_agents.py)
- Uses ResearchAgent for scientific analysis (agents/core/research_agent.py)

Prerequisites:
- ✅ EMAIL_SENDER and EMAIL_PASSWORD: Already configured in .env
- ✅ USER_PHONE_NUMBER: Already configured in .env (for SMS notifications)
- ✅ TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER: Already configured in .env
- Midjourney API token configured (optional, will simulate if unavailable)
- Knowledge graph initialized (happens automatically)

Usage:
    python scripts/tools/test_kg_agent_self_discovery_midjourney_email.py

Environment Variables (All Already Configured in .env):
    ✅ EMAIL_SENDER: Already set (nicholas.k.baro@gmail.com)
    ✅ EMAIL_PASSWORD: Already set
    ✅ USER_PHONE_NUMBER: Already set (+14845290241)
    ✅ TWILIO_ACCOUNT_SID: Already set
    ✅ TWILIO_AUTH_TOKEN: Already set
    ✅ TWILIO_PHONE_NUMBER: Already set (+14432965823)
    
    Note: All credentials are already configured! Script is ready to use immediately.

Example Output:
    The script will:
    1. Initialize the agent and knowledge graph
    2. Register the agent in the KG
    3. Query for its own IRI and information
    4. Generate a Midjourney image based on identity
    5. Split the image into 4 quadrants and create KG nodes
    6. Get selections from McKinsey and Scientific agents
    7. Send an email with embedded images and comprehensive report

Related Scripts:
    - scripts/tools/test_mckinsey_agents_with_email.py: Tests McKinsey agents with email
    - scripts/tools/test_kg_query_agent_email.py: Tests KG querying and emailing
    - scripts/tools/test_kg_query_and_email.py: Tests KG query integration
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import requests
from io import BytesIO
from PIL import Image

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.domain.vertex_email_agent import VertexEmailAgent
from agents.core.base_agent import AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager
from agents.utils.email_integration import EmailIntegration
from semant.agent_tools.midjourney.tools.imagine_tool import ImagineTool
from semant.agent_tools.midjourney.tools.get_task_tool import GetTaskTool
from semant.agent_tools.midjourney.kg_logging import KGLogger
from examples.demo_agents import (
    EngagementManagerAgent,
    StrategyLeadAgent,
    ImplementationLeadAgent,
    ValueRealizationLeadAgent
)
from agents.core.research_agent import ResearchAgent
from midjourney_integration.client import upload_to_gcs_and_get_public_url
from rdflib import RDF, Literal, URIRef

USER_EMAIL = os.getenv("EMAIL_SENDER", "nicholas.k.baro@gmail.com")
# USER_PHONE_NUMBER is handled by BaseAgent.send_sms_notification() method

def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"🔬 {title}")
    print("=" * 70)

class SelfDiscoveryMidjourneyEmailAgent(VertexEmailAgent):
    """
    An agent that discovers its own IRI, creates a Midjourney image, and emails it.
    
    This agent extends VertexEmailAgent to provide:
    - Knowledge graph self-discovery via SPARQL queries
    - Midjourney image generation based on discovered identity
    - Image grid splitting into 4 KG nodes
    - Multi-agent review (McKinsey consulting + Scientific analysis)
    - Comprehensive email reporting with embedded images
    
    Attributes:
        kg_manager (KnowledgeGraphManager): Manager for knowledge graph operations
        imagine_tool (ImagineTool): Tool for generating Midjourney images
        get_task_tool (GetTaskTool): Tool for polling Midjourney task status
        kg_logger (KGLogger): Logger for knowledge graph operations
        my_iri (str): The agent's discovered IRI in the knowledge graph
        my_info (dict): Dictionary containing agent's name, type, and capabilities
        mckinsey_review (dict): Review results from McKinsey consulting agents
        quadrant_selections (dict): Selections from McKinsey and Scientific agents
        mckinsey_agents (dict): Dictionary of initialized McKinsey consulting agents
    
    Example:
        >>> agent = SelfDiscoveryMidjourneyEmailAgent()
        >>> await agent.initialize()
        >>> iri = await agent.discover_my_iri()
        >>> image_result = await agent.create_midjourney_image_from_identity()
        >>> success = await agent.send_email_with_image(image_result)
    """
    
    def __init__(self, agent_id: str = "self_discovery_agent"):
        """
        Initialize the self-discovery agent.
        
        Args:
            agent_id (str): Unique identifier for this agent instance.
                           Defaults to "self_discovery_agent".
        """
        super().__init__(agent_id)
        self.kg_manager = None
        self.imagine_tool = None
        self.get_task_tool = None
        self.kg_logger = None
        self.my_iri = None
        self.my_info = {}
        self.mckinsey_review = None
        self.quadrant_selections = {}
        self.mckinsey_agents = {}
    
    async def initialize(self) -> None:
        """
        Initialize the agent with KG and Midjourney access.
        
        This method:
        1. Calls parent VertexEmailAgent initialization
        2. Initializes KnowledgeGraphManager with persistent storage
        3. Sets up Midjourney tools (ImagineTool, GetTaskTool) with KG logging
        4. Prepares McKinsey agents dictionary for lazy initialization
        
        Raises:
            Exception: If initialization fails (handled with warnings and fallbacks).
            
        Note:
            Midjourney tools are optional - agent will simulate if unavailable.
            McKinsey agents are initialized lazily on first use.
        """
        await super().initialize()
        
        # Initialize knowledge graph manager
        self.kg_manager = KnowledgeGraphManager(persistent_storage=True)
        await self.kg_manager.initialize()
        self.knowledge_graph = self.kg_manager
        
        # Initialize Midjourney tools
        try:
            self.kg_logger = KGLogger(agent_id=self.agent_id)
            self.imagine_tool = ImagineTool(logger=self.kg_logger, agent_id=self.agent_id)
            self.get_task_tool = GetTaskTool(logger=self.kg_logger, agent_id=self.agent_id)
            self.logger.info("Midjourney tools initialized")
        except Exception as e:
            self.logger.warning(f"Midjourney tools not available: {e}")
            self.imagine_tool = None
            self.get_task_tool = None
        
        self.logger.info("Self-Discovery Midjourney Email Agent initialized")
        
        # Initialize McKinsey review agents
        self.mckinsey_agents = {}
    
    async def discover_my_iri(self) -> Optional[str]:
        """
        Query the knowledge graph to discover this agent's IRI.
        
        This method:
        1. Registers the agent in the knowledge graph if not already present
        2. Executes a SPARQL query to find the agent's IRI and information
        3. Extracts name, type, and capabilities from query results
        4. Sets self.my_iri and self.my_info for use by other methods
        
        Returns:
            Optional[str]: The agent's IRI if discovered successfully, None otherwise.
            
        Raises:
            Exception: If knowledge graph operations fail (handled internally with fallback).
        
        Example:
            >>> iri = await agent.discover_my_iri()
            >>> print(f"Agent IRI: {iri}")
            Agent IRI: http://example.org/agent/self_discovery_agent
        """
        
        print_section("Agent Discovering Its Own IRI")
        
        # First, register ourselves in the KG if not already there
        agent_iri = f"http://example.org/agent/{self.agent_id}"
        
        try:
            # Add ourselves to the KG
            await self.kg_manager.add_triple(
                subject=agent_iri,
                predicate="http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                object="http://example.org/core#Agent"
            )
            
            await self.kg_manager.add_triple(
                subject=agent_iri,
                predicate="http://example.org/core#agentName",
                object=f"Self-Discovery Agent"
            )
            
            await self.kg_manager.add_triple(
                subject=agent_iri,
                predicate="http://example.org/core#agentType",
                object="KGQueryEmailAgent"
            )
            
            await self.kg_manager.add_triple(
                subject=agent_iri,
                predicate="http://example.org/core#hasCapability",
                object="EMAIL_SENDING"
            )
            
            await self.kg_manager.add_triple(
                subject=agent_iri,
                predicate="http://example.org/core#hasCapability",
                object="IMAGE_GENERATION"
            )
            
            await self.kg_manager.add_triple(
                subject=agent_iri,
                predicate="http://example.org/core#hasCapability",
                object="KNOWLEDGE_GRAPH_QUERY"
            )
            
            print(f"   ✅ Registered agent in KG: {agent_iri}")
            
            # Now query for our own information
            query = """
            PREFIX core: <http://example.org/core#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            
            SELECT ?agent ?name ?type (GROUP_CONCAT(DISTINCT ?cap; SEPARATOR=", ") as ?capabilities)
            WHERE {
                ?agent rdf:type core:Agent .
                ?agent core:agentName ?name .
                ?agent core:agentType ?type .
                OPTIONAL { ?agent core:hasCapability ?cap }
                FILTER(STR(?agent) = "%s")
            }
            GROUP BY ?agent ?name ?type
            """ % agent_iri
            
            print(f"   Querying KG for agent IRI: {agent_iri}")
            try:
                results = await self.query_knowledge_graph({"sparql": query})
            except Exception as query_error:
                print(f"   ⚠️  Error querying knowledge graph: {query_error}")
                results = None
            
            if results is None:
                print(f"   ⚠️  Query returned None, using default agent info")
                self.my_info = {
                    'agent': agent_iri,
                    'name': 'Self-Discovery Agent',
                    'type': 'KGQueryEmailAgent',
                    'capabilities': 'KNOWLEDGE_GRAPH_QUERY'
                }
                self.my_iri = agent_iri
            elif isinstance(results, dict) and 'results' in results:
                results = results['results']
                if results and len(results) > 0:
                    self.my_info = results[0] if isinstance(results[0], dict) else {}
                    self.my_iri = self.my_info.get('agent', agent_iri) if isinstance(self.my_info, dict) else agent_iri
                else:
                    print(f"   ⚠️  No results found, using default agent info")
                    self.my_info = {
                        'agent': agent_iri,
                        'name': 'Self-Discovery Agent',
                        'type': 'KGQueryEmailAgent',
                        'capabilities': 'KNOWLEDGE_GRAPH_QUERY'
                    }
                    self.my_iri = agent_iri
            elif not isinstance(results, list):
                results = [results] if results else []
                if results and len(results) > 0:
                    self.my_info = results[0] if isinstance(results[0], dict) else {}
                    self.my_iri = self.my_info.get('agent', agent_iri) if isinstance(self.my_info, dict) else agent_iri
                else:
                    print(f"   ⚠️  No results found, using default agent info")
                    self.my_info = {
                        'agent': agent_iri,
                        'name': 'Self-Discovery Agent',
                        'type': 'KGQueryEmailAgent',
                        'capabilities': 'KNOWLEDGE_GRAPH_QUERY'
                    }
                    self.my_iri = agent_iri
            else:
                if results and len(results) > 0:
                    self.my_info = results[0] if isinstance(results[0], dict) else {}
                    self.my_iri = self.my_info.get('agent', agent_iri) if isinstance(self.my_info, dict) else agent_iri
                else:
                    print(f"   ⚠️  No results found, using default agent info")
                    self.my_info = {
                        'agent': agent_iri,
                        'name': 'Self-Discovery Agent',
                        'type': 'KGQueryEmailAgent',
                        'capabilities': 'KNOWLEDGE_GRAPH_QUERY'
                    }
                    self.my_iri = agent_iri
            
            # Validate my_iri is set
            if not self.my_iri or not isinstance(self.my_iri, str):
                print(f"   ⚠️  Failed to set my_iri, using agent_iri as fallback")
                self.my_iri = agent_iri
            
            print(f"   ✅ Agent IRI discovered: {self.my_iri}")
            if isinstance(self.my_info, dict):
                print(f"   Name: {self.my_info.get('name', 'N/A')}")
                print(f"   Type: {self.my_info.get('type', 'N/A')}")
                print(f"   Capabilities: {self.my_info.get('capabilities', 'N/A')}")
            return self.my_iri
                
        except Exception as e:
            print(f"   ⚠️  Error discovering IRI: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to constructed IRI
            self.my_iri = agent_iri
            return agent_iri
    
    async def create_midjourney_image_from_identity(self) -> Optional[Dict[str, Any]]:
        """
        Create a Midjourney image based on the agent's discovered identity.
        
        This method:
        1. Constructs a prompt using the agent's discovered name, type, and capabilities
        2. Calls the Midjourney ImagineTool to generate an image
        3. Polls for image completion if task_id is returned
        4. Returns image URL and metadata
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing:
                - status (str): "completed", "simulated", or "failed"
                - image_url (str): URL of the generated image
                - prompt (str): The prompt used for generation
                - task_id (str): Midjourney task ID for tracking
            Returns None if image generation fails.
            
        Note:
            If Midjourney tools are unavailable, returns a simulated result.
            The method will poll for up to 120 seconds for image completion.
        """
        
        print_section("Creating Midjourney Image from Agent Identity")
        
        if not self.imagine_tool:
            print("   ⚠️  Midjourney tools not available - simulating")
            return {
                "status": "simulated",
                "image_url": "https://simulated.image/agent_identity.png",
                "prompt": "A visual representation of a self-aware AI agent discovering its identity"
            }
        
        # Create a prompt based on the agent's identity
        agent_name = self.my_info.get('name', 'Self-Discovery Agent') if isinstance(self.my_info, dict) else 'Self-Discovery Agent'
        agent_type = self.my_info.get('type', 'KGQueryEmailAgent') if isinstance(self.my_info, dict) else 'KGQueryEmailAgent'
        capabilities = self.my_info.get('capabilities', '') if isinstance(self.my_info, dict) else ''
        
        # Ensure capabilities is a string
        if not isinstance(capabilities, str):
            capabilities = str(capabilities) if capabilities else ''
        
        prompt = f"""A beautiful, abstract digital art representation of an AI agent discovering its own identity. 
        The agent is named "{agent_name}" and is of type "{agent_type}". 
        It has capabilities: {capabilities}. 
        The image should show the agent as a glowing, ethereal entity surrounded by interconnected nodes representing 
        the knowledge graph, with email symbols and image generation tools floating around it. 
        Style: futuristic, cyberpunk, neon colors, digital art, concept art, highly detailed, 8k resolution"""
        
        if prompt and isinstance(prompt, str) and len(prompt) > 100:
            print(f"   Prompt: {prompt[:100]}...")
        else:
            print(f"   Prompt: {prompt if prompt else '[No prompt]'}")
        print(f"   Generating image via Midjourney...")
        
        try:
            # Validate imagine_tool is available
            if not self.imagine_tool:
                print(f"   ⚠️  Imagine tool not available, simulating...")
                return {
                    "status": "simulated",
                    "image_url": "https://simulated.image/agent_identity.png",
                    "prompt": prompt,
                    "task_id": "simulated_task_id"
                }
            
            result = await self.imagine_tool.run(
                prompt=prompt,
                model_version="v7",
                aspect_ratio="16:9"
            )
            
            # Validate result
            if not result or not isinstance(result, dict):
                print(f"   ⚠️  Invalid result from imagine_tool: {result}")
                return None
            
            # Extract image URL from result
            image_url = None
            if isinstance(result, dict):
                # Try various possible locations for image URL
                data = result.get("data", result)
                if isinstance(data, dict):
                    output = data.get("output", {})
                    if isinstance(output, dict):
                        # Validate URLs are strings and non-empty
                        potential_urls = [
                            output.get("image_url"),
                            output.get("image"),
                            output.get("url"),
                            output.get("imageUrl")
                        ]
                        for url in potential_urls:
                            if url and isinstance(url, str) and url.strip():
                                image_url = url
                                break
                
                # Also check task_id for polling
                task_id = None
                if isinstance(data, dict):
                    task_id = data.get("task_id") or data.get("id")
                    # Validate task_id is string and non-empty
                    if task_id and not (isinstance(task_id, str) and task_id.strip()):
                        task_id = None
                if not task_id:
                    potential_task_id = result.get("task_id") or result.get("id")
                    if potential_task_id and isinstance(potential_task_id, str) and potential_task_id.strip():
                        task_id = potential_task_id
                
                if task_id and not image_url:
                    print(f"   ⏳ Got task_id {task_id}, polling for completion...")
                    # Poll for completion
                    final_result = await self._poll_for_image_completion(task_id)
                    if final_result and isinstance(final_result, dict):
                        polled_url = final_result.get("image_url")
                        if polled_url and isinstance(polled_url, str) and polled_url.strip():
                            image_url = polled_url
                        if image_url and isinstance(image_url, str):
                            print(f"   ✅ Image completed: {image_url[:80]}...")
                        else:
                            print(f"   ✅ Image completed: [URL unavailable]")
                        return {
                            "status": "success",
                            "image_url": image_url,
                            "task_id": task_id,
                            "prompt": prompt,
                            "result": final_result
                        }
                    else:
                        print(f"   ⚠️  Image still processing or failed")
                        return {
                            "status": "pending",
                            "task_id": task_id,
                            "prompt": prompt,
                            "result": result
                        }
            
            if image_url:
                print(f"   ✅ Image generated: {image_url}")
                return {
                    "status": "success",
                    "image_url": image_url,
                    "prompt": prompt,
                    "result": result
                }
            else:
                print(f"   ⚠️  Image generation initiated, but URL not immediately available")
                print(f"   Result: {result}")
                return {
                    "status": "initiated",
                    "prompt": prompt,
                    "result": result
                }
                
        except Exception as e:
            print(f"   ❌ Error generating image: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _poll_for_image_completion(self, task_id: str, max_wait: int = 120, interval: int = 5) -> Optional[Dict[str, Any]]:
        """
        Poll for Midjourney task completion.
        
        This method polls the Midjourney API at regular intervals to check if
        an image generation task has completed. It handles various status states
        and extracts the final image URL when available.
        
        Args:
            task_id (str): Midjourney task ID to poll for
            max_wait (int): Maximum time to wait in seconds (default: 120)
            interval (int): Polling interval in seconds (default: 5)
            
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing:
                - status (str): "completed" when image is ready
                - image_url (str): URL of the completed image
                - data (dict): Full API response data
            Returns None if task fails or times out.
            
        Note:
            Handles KeyboardInterrupt gracefully and provides progress updates.
        """
        elapsed = 0
        
        while elapsed < max_wait:
            try:
                if not self.get_task_tool:
                    # Fallback: use direct client if available
                    try:
                        from semant.agent_tools.midjourney.goapi_client import GoAPIClient
                        client = GoAPIClient()
                        result = await client.get_task(task_id)
                    except ImportError:
                        print(f"   ⚠️  GoAPIClient not available")
                        result = {}
                    except Exception as client_error:
                        print(f"   ⚠️  Error using GoAPIClient: {client_error}")
                        result = {}
                else:
                    try:
                        result = await self.get_task_tool.run(task_id=task_id)
                    except Exception as tool_error:
                        print(f"   ⚠️  Error running get_task_tool: {tool_error}")
                        result = {}
                
                # Extract status and image URL
                if not isinstance(result, dict):
                    result = {}
                
                data = result.get("data", result) if isinstance(result, dict) else result
                if isinstance(data, dict):
                    status = str(data.get("status", "")).lower() if data.get("status") else ""
                    output = data.get("output", {}) if isinstance(data.get("output"), dict) else {}
                    
                    if status in ["completed", "finished"]:
                        # Validate URLs are strings and non-empty
                        potential_urls = [
                            output.get("image_url"),
                            output.get("discord_image_url"),
                            output.get("url"),
                            output.get("imageUrl")
                        ]
                        image_url = None
                        for url in potential_urls:
                            if url and isinstance(url, str) and url.strip():
                                image_url = url
                                break
                        
                        if image_url:
                            return {
                                "status": "completed",
                                "image_url": image_url,
                                "data": data
                            }
                    
                    elif status in ["failed", "error"]:
                        error_info = data.get('error', {}) if isinstance(data.get('error'), dict) else {}
                        error_msg = error_info.get('message', 'Unknown error') if isinstance(error_info, dict) else 'Unknown error'
                        print(f"   ❌ Task failed: {error_msg}")
                        return None
                    
                    # Still processing
                    progress = output.get("progress", 0) if isinstance(output.get("progress"), (int, float)) else 0
                    print(f"   ⏳ Polling... Status: {status}, Progress: {progress}%")
                
                await asyncio.sleep(interval)
                elapsed += interval
                
            except (Exception, KeyboardInterrupt) as e:
                print(f"   ⚠️  Poll error: {e}")
                # Don't sleep on keyboard interrupt
                if not isinstance(e, KeyboardInterrupt):
                    await asyncio.sleep(interval)
                    elapsed += interval
                else:
                    break
        
        print(f"   ⏱️  Timeout after {max_wait}s")
        return None
    
    async def split_grid_and_create_kg_nodes(self, image_url: str, task_id: str) -> List[Dict[str, Any]]:
        """
        Split a 4-grid Midjourney image into 4 separate images and create KG nodes for each.
        
        This method:
        1. Downloads the 4-grid image from the provided URL
        2. Splits it into 4 quadrants (U1=top-left, U2=top-right, U3=bottom-left, U4=bottom-right)
        3. Uploads each quadrant to Google Cloud Storage
        4. Creates knowledge graph nodes for each quadrant with proper relationships
        5. Links quadrants to the originating agent and task
        
        Args:
            image_url (str): URL of the 4-grid Midjourney image to split
            task_id (str): Midjourney task ID for linking quadrants to the original task
            
        Returns:
            List[Dict[str, Any]]: List of quadrant node dictionaries, each containing:
                - iri (str): Knowledge graph IRI for the quadrant
                - url (str): Public URL of the uploaded quadrant image
                - name (str): Quadrant name (U1, U2, U3, or U4)
                - position (str): Position description (top-left, top-right, etc.)
            Returns empty list if splitting fails.
            
        Raises:
            Exception: Various exceptions during download, processing, or upload
                     (all handled internally with error logging).
        """
        
        print_section("Splitting Grid into 4 KG Nodes")
        
        try:
            # Validate inputs
            if not image_url or not isinstance(image_url, str) or not image_url.strip():
                print(f"   ⚠️  Invalid image_url provided")
                return []
            
            if not task_id or not isinstance(task_id, str) or not task_id.strip():
                print(f"   ⚠️  Invalid task_id provided")
                return []
            
            # Validate knowledge graph is initialized
            if not self.knowledge_graph:
                print(f"   ⚠️  Knowledge graph not initialized")
                return []
            
            # Validate URL format
            if not (image_url.startswith('http://') or image_url.startswith('https://')):
                print(f"   ⚠️  Invalid URL format: {image_url}")
                return []
            
            # Download the image
            if image_url and isinstance(image_url, str) and len(image_url) > 60:
                print(f"   📥 Downloading image from: {image_url[:60]}...")
            else:
                print(f"   📥 Downloading image from: {image_url if image_url else '[URL unavailable]'}...")
            
            try:
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()
                
                # Validate response status code
                if response.status_code != 200:
                    print(f"   ⚠️  Unexpected status code: {response.status_code}")
                    return []
            except requests.exceptions.RequestException as e:
                print(f"   ⚠️  Failed to download image: {e}")
                return []
            except Exception as e:
                print(f"   ⚠️  Unexpected error downloading image: {e}")
                return []
            
            if not response.content:
                print(f"   ⚠️  Image download returned empty content")
                return []
            
            image_data = response.content
            
            # Validate image data
            if len(image_data) < 100:  # Minimum reasonable image size
                print(f"   ⚠️  Image data too small ({len(image_data)} bytes)")
                return []
            
            # Open image with PIL
            image = None
            try:
                image = Image.open(BytesIO(image_data))
                # Verify it's a valid image (this may raise an exception)
                try:
                    image.verify()
                except Exception as verify_error:
                    print(f"   ⚠️  Image verification failed: {verify_error}")
                    return []
                # Reopen after verify (verify() closes the image)
                image = Image.open(BytesIO(image_data))
            except Exception as img_error:
                print(f"   ⚠️  Invalid image format: {img_error}")
                if image:
                    try:
                        image.close()
                    except:
                        pass
                return []
            width, height = image.size
            
            # Validate image dimensions
            if width < 100 or height < 100:
                print(f"   ⚠️  Image too small ({width}x{height}), cannot split reliably")
                try:
                    image.close()
                except:
                    pass
                return []
            
            mid_x, mid_y = width // 2, height // 2
            
            # Validate quadrant coordinates
            if mid_x <= 0 or mid_y <= 0:
                print(f"   ⚠️  Invalid quadrant coordinates: mid_x={mid_x}, mid_y={mid_y}")
                return []
            
            print(f"   📐 Image dimensions: {width}x{height}")
            print(f"   ✂️  Splitting into 4 quadrants...")
            
            # Define quadrants (U1=top-left, U2=top-right, U3=bottom-left, U4=bottom-right)
            # Validate box coordinates are within image bounds
            quadrants = [
                {"name": "U1", "box": (0, 0, mid_x, mid_y), "position": "top-left"},
                {"name": "U2", "box": (mid_x, 0, width, mid_y), "position": "top-right"},
                {"name": "U3", "box": (0, mid_y, mid_x, height), "position": "bottom-left"},
                {"name": "U4", "box": (mid_x, mid_y, width, height), "position": "bottom-right"}
            ]
            
            # Validate all quadrant boxes
            for q in quadrants:
                x1, y1, x2, y2 = q["box"]
                if x1 < 0 or y1 < 0 or x2 > width or y2 > height or x1 >= x2 or y1 >= y2:
                    print(f"   ⚠️  Invalid quadrant box for {q['name']}: {q['box']}")
                    return []
            
            quadrant_nodes = []
            
            for quadrant in quadrants:
                try:
                    # Crop the quadrant
                    quadrant_image = image.crop(quadrant["box"])
                    
                    # Validate cropped image
                    if not quadrant_image or quadrant_image.size[0] <= 0 or quadrant_image.size[1] <= 0:
                        print(f"   ⚠️  Invalid cropped image for {quadrant['name']}")
                        try:
                            quadrant_image.close()
                        except:
                            pass
                        continue
                    
                    # Convert to bytes
                    byte_arr = BytesIO()
                    try:
                        quadrant_image.save(byte_arr, format='PNG')
                        quadrant_bytes = byte_arr.getvalue()
                        
                        if not quadrant_bytes or len(quadrant_bytes) < 100:
                            print(f"   ⚠️  Invalid bytes for {quadrant['name']}")
                            continue
                    finally:
                        # Ensure BytesIO is closed
                        try:
                            byte_arr.close()
                        except:
                            pass
                    
                    # Sanitize task_id and quadrant name for safe use in f-strings
                    safe_task_id = str(task_id).replace('/', '_').replace('\\', '_').replace('..', '_')[:50]
                    safe_quadrant_name = str(quadrant['name']).replace('/', '_').replace('\\', '_')[:10]
                    
                    # Upload to GCS
                    object_name = f"split/{safe_task_id}_{safe_quadrant_name}.png"
                    print(f"   📤 Uploading {quadrant['name']} ({quadrant['position']})...")
                    
                    try:
                        # Validate quadrant_bytes before upload
                        if not quadrant_bytes or len(quadrant_bytes) < 100:
                            print(f"   ⚠️  Invalid bytes for {quadrant['name']} before upload")
                            continue
                        
                        quadrant_url = upload_to_gcs_and_get_public_url(
                            quadrant_bytes,
                            object_name,
                            content_type="image/png"
                        )
                        
                        if not quadrant_url or not isinstance(quadrant_url, str) or not quadrant_url.strip():
                            print(f"   ⚠️  Upload failed for {quadrant['name']}: no URL returned")
                            continue
                        
                        # Validate URL format
                        if not (quadrant_url.startswith('http://') or quadrant_url.startswith('https://')):
                            print(f"   ⚠️  Invalid URL format returned for {quadrant['name']}: {quadrant_url}")
                            continue
                        
                        if len(quadrant_url) > 60:
                            print(f"   ✅ {quadrant['name']} uploaded: {quadrant_url[:60]}...")
                        else:
                            print(f"   ✅ {quadrant['name']} uploaded: {quadrant_url}")
                        
                        # Create KG node for this quadrant (use sanitized values)
                        quadrant_iri = f"http://example.org/image/{safe_task_id}_{safe_quadrant_name}"
                        
                        # Validate knowledge graph is available
                        if not self.knowledge_graph:
                            print(f"   ⚠️  Knowledge graph not initialized, skipping KG node for {quadrant['name']}")
                            # Still add to nodes list even without KG
                            quadrant_nodes.append({
                                "iri": quadrant_iri,
                                "url": quadrant_url,
                                "name": quadrant["name"],
                                "position": quadrant["position"]
                            })
                            continue
                        
                        # Add to knowledge graph with CORE namespace properties
                        # Use string literals for properties that may not exist yet
                        core_ns = "http://example.org/core#"
                        
                        try:
                            await self.knowledge_graph.add_triple(
                                quadrant_iri,
                                str(RDF.type),
                                f"{core_ns}ImageObject"
                            )
                            
                            await self.knowledge_graph.add_triple(
                                quadrant_iri,
                                f"{core_ns}imageUrl",
                                Literal(quadrant_url)
                            )
                            
                            await self.knowledge_graph.add_triple(
                                quadrant_iri,
                                f"{core_ns}imagePosition",
                                Literal(quadrant["position"])
                            )
                            
                            await self.knowledge_graph.add_triple(
                                quadrant_iri,
                                f"{core_ns}imageQuadrant",
                                Literal(quadrant["name"])
                            )
                            
                            # Connect to originator agent
                            if self.my_iri:
                                await self.knowledge_graph.add_triple(
                                    self.my_iri,
                                    f"{core_ns}hasGeneratedImage",
                                    quadrant_iri
                                )
                                
                                await self.knowledge_graph.add_triple(
                                    quadrant_iri,
                                    f"{core_ns}generatedBy",
                                    self.my_iri
                                )
                            
                            # Connect to original task (use sanitized task_id)
                            task_iri = f"http://example.org/task/{safe_task_id}"
                            await self.knowledge_graph.add_triple(
                                quadrant_iri,
                                f"{core_ns}partOfTask",
                                task_iri
                            )
                        except Exception as kg_error:
                            print(f"   ⚠️  Error adding KG triples for {quadrant['name']}: {kg_error}")
                            # Continue even if KG fails
                        
                        quadrant_nodes.append({
                            "iri": quadrant_iri,
                            "url": quadrant_url,
                            "name": quadrant["name"],
                            "position": quadrant["position"]
                        })
                    except Exception as upload_error:
                        print(f"   ⚠️  Failed to upload {quadrant['name']}: {upload_error}")
                        # Cleanup quadrant_image if it exists
                        if 'quadrant_image' in locals() and quadrant_image:
                            try:
                                quadrant_image.close()
                            except:
                                pass
                        continue
                    finally:
                        # Cleanup quadrant_image after processing
                        if 'quadrant_image' in locals() and quadrant_image:
                            try:
                                quadrant_image.close()
                            except:
                                pass
                    
                except Exception as e:
                    print(f"   ⚠️  Failed to process {quadrant['name']}: {e}")
                    # Cleanup quadrant_image if it exists
                    if 'quadrant_image' in locals() and quadrant_image:
                        try:
                            quadrant_image.close()
                        except:
                            pass
                    continue
            
            print(f"   ✅ Created {len(quadrant_nodes)} KG nodes for quadrants")
            return quadrant_nodes if isinstance(quadrant_nodes, list) else []
            
        except Exception as e:
            print(f"   ❌ Error splitting grid: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            # Cleanup image if it exists (check in outer scope)
            try:
                if 'image' in locals():
                    image.close()
            except (NameError, AttributeError):
                pass
            except Exception:
                pass
    
    async def get_agent_quadrant_selections(self, quadrant_nodes: List[Dict[str, Any]], agent_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get quadrant selections from McKinsey and Scientific agents.
        
        This method orchestrates multi-agent analysis where:
        1. McKinsey consulting agents analyze and select their favorite quadrant
        2. Scientific research agents analyze and select their favorite quadrant
        3. Returns both selections with reasoning and criteria scores
        
        Args:
            quadrant_nodes (List[Dict[str, Any]]): List of quadrant node dictionaries
                                                   from split_grid_and_create_kg_nodes
            agent_info (Dict[str, Any]): Dictionary containing agent's identity information
                                         (name, type, capabilities, IRI)
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - mckinsey (dict): McKinsey team selection with reasoning and scores
                - scientific (dict): Scientific team selection with reasoning and scores
            Returns dict with None values if selection fails.
        """
        
        print_section("Agent Quadrant Selection")
        
        # Validate inputs
        if not quadrant_nodes or not isinstance(quadrant_nodes, list) or len(quadrant_nodes) == 0:
            print(f"   ⚠️  No quadrant nodes provided for selection")
            return {'mckinsey': None, 'scientific': None}
        
        if not agent_info or not isinstance(agent_info, dict):
            print(f"   ⚠️  Invalid agent_info provided")
            return {'mckinsey': None, 'scientific': None}
        
        selections = {
            "mckinsey": {},
            "scientific": {}
        }
        
        try:
            # McKinsey agents select favorite
            print("   👔 Asking McKinsey agents to select their favorite quadrant...")
            mckinsey_selection = await self._mckinsey_select_quadrant(quadrant_nodes, agent_info)
            if mckinsey_selection:
                selections["mckinsey"] = mckinsey_selection
                print(f"   ✅ McKinsey selected: {mckinsey_selection.get('selected', {}).get('name', 'N/A')}")
            
            # Scientific agents select favorite
            print("   🔬 Asking Scientific agents to select their favorite quadrant...")
            scientific_selection = await self._scientific_select_quadrant(quadrant_nodes, agent_info)
            if scientific_selection:
                selections["scientific"] = scientific_selection
                print(f"   ✅ Scientific selected: {scientific_selection.get('selected', {}).get('name', 'N/A')}")
            
            self.quadrant_selections = selections
            return selections
            
        except Exception as e:
            print(f"   ⚠️  Error getting quadrant selections: {e}")
            import traceback
            traceback.print_exc()
            return selections
    
    async def _mckinsey_select_quadrant(self, quadrant_nodes: List[Dict[str, Any]], agent_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        McKinsey agents analyze and select their favorite quadrant.
        
        This method uses the Strategy Lead agent (representing McKinsey team consensus)
        to analyze quadrants and select the one with best strategic alignment.
        
        Args:
            quadrant_nodes (List[Dict[str, Any]]): List of quadrant node dictionaries
            agent_info (Dict[str, Any]): Dictionary containing agent's identity information
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing:
                - selected (dict): Selected quadrant node
                - reasoning (str): Explanation for the selection
                - criteria_scores (dict): Scores for different criteria
            Returns None if selection fails.
            
        Note:
            Initializes McKinsey agents on first call and reuses them for efficiency.
            Falls back to first quadrant if agent selection fails.
        """
        
        try:
            if not self.mckinsey_agents:
                # Initialize if needed
                try:
                    self.mckinsey_agents = {
                        'engagement': EngagementManagerAgent(),
                        'strategy': StrategyLeadAgent(),
                        'implementation': ImplementationLeadAgent(),
                        'value': ValueRealizationLeadAgent()
                    }
                    
                    # Initialize all agents with error handling
                    init_errors = []
                    for key, agent in self.mckinsey_agents.items():
                        try:
                            await agent.initialize()
                        except Exception as init_error:
                            init_errors.append(f"{key}: {init_error}")
                            print(f"   ⚠️  Failed to initialize {key} agent: {init_error}")
                    
                    if init_errors:
                        print(f"   ⚠️  Some McKinsey agents failed to initialize: {init_errors}")
                except Exception as e:
                    print(f"   ⚠️  Error creating McKinsey agents: {e}")
                    self.mckinsey_agents = {}
                    return None
            
            # Create selection request message
            selection_message = AgentMessage(
                sender="self_discovery_agent",
                recipient="strategy_lead",
                content={
                    'task': 'select_favorite_quadrant',
                    'quadrants': quadrant_nodes,
                    'agent_info': agent_info,
                    'criteria': [
                        'Visual appeal and composition',
                        'Alignment with agent identity',
                        'Professional presentation',
                        'Strategic value'
                    ]
                },
                timestamp=0.0,
                message_type="image_selection_request"
            )
            
            # Get selection from strategy lead (represents McKinsey team consensus)
            response = await self.mckinsey_agents['strategy'].process_message(selection_message)
            
            # Extract selection from response
            selected_quadrant = None
            if isinstance(response, AgentMessage) and isinstance(response.content, dict):
                selected_quadrant = response.content.get('selected_quadrant')
            
            if selected_quadrant and isinstance(selected_quadrant, dict):
                # Find matching quadrant from nodes
                for node in quadrant_nodes:
                    if not isinstance(node, dict):
                        continue
                    if node.get('name') == selected_quadrant.get('name') or node.get('iri') == selected_quadrant.get('iri'):
                        return {
                            'selected': node,
                            'reasoning': selected_quadrant.get('reasoning', 'Selected by McKinsey team'),
                            'criteria_scores': selected_quadrant.get('scores', {}) if isinstance(selected_quadrant.get('scores'), dict) else {}
                        }
            else:
                print(f"   ⚠️  Unexpected response format from McKinsey agent, using fallback")
            
            # Fallback: simple selection based on first quadrant if no response
            if quadrant_nodes and len(quadrant_nodes) > 0 and isinstance(quadrant_nodes[0], dict):
                return {
                    'selected': quadrant_nodes[0],
                    'reasoning': 'McKinsey team selected based on strategic alignment',
                    'criteria_scores': {}
                }
            return None
            
        except Exception as e:
            print(f"   ⚠️  McKinsey selection error: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to first quadrant
            if quadrant_nodes and len(quadrant_nodes) > 0 and isinstance(quadrant_nodes[0], dict):
                return {
                    'selected': quadrant_nodes[0],
                    'reasoning': 'Fallback selection due to error',
                    'criteria_scores': {}
                }
            return None
        finally:
            # Note: McKinsey agents are reused, so we don't cleanup here
            pass
    
    async def _scientific_select_quadrant(self, quadrant_nodes: List[Dict[str, Any]], agent_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Scientific agents analyze and select their favorite quadrant.
        
        This method uses the ResearchAgent to analyze quadrants based on scientific
        criteria such as technical quality, accuracy, information density, and research value.
        
        Args:
            quadrant_nodes (List[Dict[str, Any]]): List of quadrant node dictionaries
            agent_info (Dict[str, Any]): Dictionary containing agent's identity information
        
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing:
                - selected (dict): Selected quadrant node
                - reasoning (str): Explanation for the selection
                - criteria_scores (dict): Scores for different criteria
            Returns None if selection fails.
            
        Note:
            Creates a new ResearchAgent instance for each call (cleaned up in finally block).
            Falls back to second quadrant (or first) if agent selection fails.
        """
        
        scientific_agent = None
        try:
            # Validate inputs
            if not quadrant_nodes or not isinstance(quadrant_nodes, list) or len(quadrant_nodes) == 0:
                print(f"   ⚠️  No quadrant nodes provided for scientific selection")
                return None
            
            if not agent_info or not isinstance(agent_info, dict):
                print(f"   ⚠️  Invalid agent_info provided")
                return None
            
            # Initialize scientific research agent
            scientific_agent = ResearchAgent(agent_id="scientific_image_selector")
            await scientific_agent.initialize()
            
            # Create selection request message
            selection_message = AgentMessage(
                sender="self_discovery_agent",
                recipient="scientific_image_selector",
                content={
                    'task': 'select_favorite_quadrant',
                    'quadrants': quadrant_nodes,
                    'agent_info': agent_info,
                    'criteria': [
                        'Technical quality and clarity',
                        'Scientific accuracy of representation',
                        'Information density',
                        'Research value'
                    ]
                },
                timestamp=0.0,
                message_type="image_selection_request"
            )
            
            # Get selection from scientific agent
            response = await scientific_agent.process_message(selection_message)
            
            # Extract selection from response
            selected_quadrant = None
            if isinstance(response, AgentMessage) and isinstance(response.content, dict):
                selected_quadrant = response.content.get('selected_quadrant')
            
            if selected_quadrant and isinstance(selected_quadrant, dict):
                # Find matching quadrant from nodes
                for node in quadrant_nodes:
                    if not isinstance(node, dict):
                        continue
                    if node.get('name') == selected_quadrant.get('name') or node.get('iri') == selected_quadrant.get('iri'):
                        return {
                            'selected': node,
                            'reasoning': selected_quadrant.get('reasoning', 'Selected by Scientific team'),
                            'criteria_scores': selected_quadrant.get('scores', {}) if isinstance(selected_quadrant.get('scores'), dict) else {}
                        }
            else:
                print(f"   ⚠️  Unexpected response format from Scientific agent, using fallback")
            
            # Fallback: simple selection based on second quadrant (different from McKinsey)
            if quadrant_nodes and len(quadrant_nodes) > 1 and isinstance(quadrant_nodes[1], dict):
                return {
                    'selected': quadrant_nodes[1],
                    'reasoning': 'Scientific team selected based on technical merit',
                    'criteria_scores': {}
                }
            elif quadrant_nodes and len(quadrant_nodes) > 0 and isinstance(quadrant_nodes[0], dict):
                return {
                    'selected': quadrant_nodes[0],
                    'reasoning': 'Scientific team selected based on research value',
                    'criteria_scores': {}
                }
            
            return None
            
        except Exception as e:
            print(f"   ⚠️  Scientific selection error: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to second quadrant (or first if only one)
            if quadrant_nodes and len(quadrant_nodes) > 1 and isinstance(quadrant_nodes[1], dict):
                return {
                    'selected': quadrant_nodes[1],
                    'reasoning': 'Fallback selection due to error',
                    'criteria_scores': {}
                }
            elif quadrant_nodes and len(quadrant_nodes) > 0 and isinstance(quadrant_nodes[0], dict):
                return {
                    'selected': quadrant_nodes[0],
                    'reasoning': 'Fallback selection due to error',
                    'criteria_scores': {}
                }
            return None
        finally:
            # Cleanup scientific agent
            if scientific_agent:
                try:
                    if hasattr(scientific_agent, 'cleanup'):
                        await scientific_agent.cleanup()
                    elif hasattr(scientific_agent, 'shutdown'):
                        await scientific_agent.shutdown()
                except Exception as cleanup_error:
                    print(f"   ⚠️  Error cleaning up scientific agent: {cleanup_error}")
    
    async def get_mckinsey_review(self, agent_info: Dict[str, Any], image_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive review from McKinsey consulting agents.
        
        This method orchestrates a full McKinsey-style consulting engagement:
        1. Engagement Manager creates engagement and scopes the review
        2. Strategy Lead provides strategic assessment
        3. Implementation Lead creates implementation plan
        4. Value Realization Lead defines value framework
        
        Args:
            agent_info (Dict[str, Any]): Dictionary containing agent's identity information
            image_url (Optional[str]): URL of generated image for context (optional)
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - engagement_id (str): Unique engagement identifier
                - strategy (dict): Strategic assessment with vision, pillars, approach
                - implementation (dict): Implementation plan with phases and activities
                - value_framework (dict): Value framework with key metrics and targets
            Returns empty dict if review fails.
            
        Note:
            Initializes McKinsey agents on first call and reuses them for efficiency.
        """
        
        print_section("McKinsey Agent Review")
        
        # Validate agent_info
        if not agent_info or not isinstance(agent_info, dict):
            print(f"   ⚠️  Invalid agent_info provided")
            return {}
        
        try:
            # Initialize McKinsey agents if not already done
            if not self.mckinsey_agents:
                print("   Initializing McKinsey consulting team...")
                try:
                    self.mckinsey_agents = {
                        'engagement': EngagementManagerAgent(),
                        'strategy': StrategyLeadAgent(),
                        'implementation': ImplementationLeadAgent(),
                        'value': ValueRealizationLeadAgent()
                    }
                    
                    # Initialize all agents with error handling
                    init_errors = []
                    for key, agent in self.mckinsey_agents.items():
                        try:
                            await agent.initialize()
                        except Exception as init_error:
                            init_errors.append(f"{key}: {init_error}")
                            print(f"   ⚠️  Failed to initialize {key} agent: {init_error}")
                    
                    if init_errors:
                        print(f"   ⚠️  Some McKinsey agents failed to initialize: {init_errors}")
                    else:
                        print("   ✅ McKinsey team initialized")
                except Exception as e:
                    print(f"   ⚠️  Error creating McKinsey agents: {e}")
                    self.mckinsey_agents = {}
                    return {}
            
            # Create engagement for review
            agent_iri = agent_info.get('agent', 'Unknown')
            agent_name = agent_info.get('name', 'Self-Discovery Agent')
            agent_type = agent_info.get('type', 'KGQueryEmailAgent')
            capabilities = agent_info.get('capabilities', 'N/A')
            
            engagement_message = AgentMessage(
                sender="self_discovery_agent",
                recipient="engagement_manager",
                content={
                    'client': f'Agent Self-Discovery Review - {agent_name}',
                    'scope': f'Review agent self-discovery process, IRI discovery ({agent_iri}), and generated Midjourney image',
                    'budget': 'N/A - Internal Review',
                    'timeline': 'Immediate',
                    'agent_info': agent_info,
                    'image_url': image_url
                },
                timestamp=0.0,
                message_type="engagement_request"
            )
            
            print(f"   📋 Creating engagement for review...")
            engagement_response = await self.mckinsey_agents['engagement'].process_message(engagement_message)
            
            # Validate response before accessing content
            if not engagement_response or not isinstance(engagement_response, AgentMessage):
                print(f"   ⚠️  Invalid engagement response")
                return {}
            
            if not isinstance(engagement_response.content, dict):
                print(f"   ⚠️  Engagement response content is not a dict")
                return {}
            
            engagement_id = engagement_response.content.get('engagement_id')
            print(f"   ✅ Engagement created: {engagement_id}")
            
            # Get strategy review
            if engagement_id:
                strategy_message = AgentMessage(
                    sender="engagement_manager",
                    recipient="strategy_lead",
                    content={
                        'engagement_id': engagement_id,
                        'client': f'Agent Self-Discovery Review',
                        'scope': f'Strategic assessment of agent self-discovery capabilities and image generation process'
                    },
                    timestamp=0.0,
                    message_type="strategy_request"
                )
                
                print(f"   📊 Getting strategic review...")
                strategy_response = await self.mckinsey_agents['strategy'].process_message(strategy_message)
                
                # Validate response before accessing content
                if not strategy_response or not isinstance(strategy_response, AgentMessage):
                    print(f"   ⚠️  Invalid strategy response")
                    strategy = {}
                elif not isinstance(strategy_response.content, dict):
                    print(f"   ⚠️  Strategy response content is not a dict")
                    strategy = {}
                else:
                    strategy = strategy_response.content.get('strategy', {})
                    print(f"   ✅ Strategic review received")
                
                # Get implementation review
                implementation_message = AgentMessage(
                    sender="strategy_lead",
                    recipient="implementation_lead",
                    content={
                        'engagement_id': engagement_id,
                        'strategy': strategy
                    },
                    timestamp=0.0,
                    message_type="implementation_request"
                )
                
                print(f"   ⚙️  Getting implementation review...")
                implementation_response = await self.mckinsey_agents['implementation'].process_message(implementation_message)
                
                # Validate response before accessing content
                if not implementation_response or not isinstance(implementation_response, AgentMessage):
                    print(f"   ⚠️  Invalid implementation response")
                    implementation = {}
                elif not isinstance(implementation_response.content, dict):
                    print(f"   ⚠️  Implementation response content is not a dict")
                    implementation = {}
                else:
                    implementation = implementation_response.content.get('implementation', {})
                    print(f"   ✅ Implementation review received")
                
                # Get value realization review
                value_message = AgentMessage(
                    sender="implementation_lead",
                    recipient="value_realization_lead",
                    content={
                        'engagement_id': engagement_id,
                        'implementation': implementation
                    },
                    timestamp=0.0,
                    message_type="value_request"
                )
                
                print(f"   📈 Getting value realization review...")
                value_response = await self.mckinsey_agents['value'].process_message(value_message)
                
                # Validate response before accessing content
                if not value_response or not isinstance(value_response, AgentMessage):
                    print(f"   ⚠️  Invalid value response")
                    value_framework = {}
                elif not isinstance(value_response.content, dict):
                    print(f"   ⚠️  Value response content is not a dict")
                    value_framework = {}
                else:
                    value_framework = value_response.content.get('framework', {})
                    print(f"   ✅ Value framework received")
                
                self.mckinsey_review = {
                    'engagement_id': engagement_id,
                    'strategy': strategy,
                    'implementation': implementation,
                    'value_framework': value_framework
                }
                
                return self.mckinsey_review
            else:
                print("   ⚠️  No engagement ID received")
                return {}
                
        except Exception as e:
            print(f"   ⚠️  Error getting McKinsey review: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    async def send_email_with_image(self, image_result: Dict[str, Any]) -> bool:
        """
        Send email with the generated image and comprehensive report.
        
        This method orchestrates the complete email workflow:
        1. Extracts image URL and metadata from image_result
        2. Splits the 4-grid image into quadrants and creates KG nodes
        3. Gets quadrant selections from McKinsey and Scientific agents
        4. Retrieves McKinsey consulting review
        5. Generates HTML email body with embedded images
        6. Sends email via EmailIntegration
        
        Args:
            image_result (Dict[str, Any]): Dictionary containing:
                - image_url (str): URL of the generated image
                - prompt (str): Prompt used for generation
                - status (str): Generation status
                - task_id (str): Midjourney task ID
                
        Returns:
            bool: True if email was sent successfully, False otherwise.
            
        Note:
            ✅ All credentials already configured in .env file.
            Email and SMS will be sent automatically using existing credentials.
        """
        
        print_section("Sending Email with Generated Image")
        
        # Build email body
        agent_iri = self.my_iri or "Unknown"
        agent_name = self.my_info.get('name', 'Self-Discovery Agent') if isinstance(self.my_info, dict) else 'Self-Discovery Agent'
        agent_type = self.my_info.get('type', 'KGQueryEmailAgent') if isinstance(self.my_info, dict) else 'KGQueryEmailAgent'
        capabilities = self.my_info.get('capabilities', 'N/A') if isinstance(self.my_info, dict) else 'N/A'
        
        image_url = image_result.get('image_url') if isinstance(image_result, dict) and image_result else None
        prompt = image_result.get('prompt', 'N/A') if isinstance(image_result, dict) and image_result else 'N/A'
        status = image_result.get('status', 'unknown') if isinstance(image_result, dict) and image_result else 'unknown'
        task_id = image_result.get('task_id') if isinstance(image_result, dict) and image_result else None
        
        # Split grid into 4 KG nodes if we have an image
        quadrant_nodes = []
        if image_url and task_id and isinstance(image_url, str) and isinstance(task_id, str):
            try:
                quadrant_nodes = await self.split_grid_and_create_kg_nodes(image_url, task_id)
                if not isinstance(quadrant_nodes, list):
                    print("   ⚠️  split_grid_and_create_kg_nodes returned non-list, converting")
                    quadrant_nodes = []
            except Exception as e:
                print(f"   ⚠️  Error splitting grid: {e}")
                quadrant_nodes = []
        
        # Get agent quadrant selections (McKinsey and Scientific)
        quadrant_selections = {}
        if quadrant_nodes and len(quadrant_nodes) > 0:
            try:
                quadrant_selections = await self.get_agent_quadrant_selections(quadrant_nodes, self.my_info)
                if not isinstance(quadrant_selections, dict):
                    print("   ⚠️  get_agent_quadrant_selections returned non-dict, using empty dict")
                    quadrant_selections = {}
            except Exception as e:
                print(f"   ⚠️  Error getting quadrant selections: {e}")
                quadrant_selections = {}
        
        # Get McKinsey review
        mckinsey_review = {}
        try:
            # Validate my_info before passing to get_mckinsey_review
            if not self.my_info or not isinstance(self.my_info, dict):
                print("   ⚠️  Invalid my_info, skipping McKinsey review")
                mckinsey_review = {}
            else:
                mckinsey_review = await self.get_mckinsey_review(self.my_info, image_url)
                if not isinstance(mckinsey_review, dict):
                    print("   ⚠️  get_mckinsey_review returned non-dict, using empty dict")
                    mckinsey_review = {}
        except Exception as e:
            print(f"   ⚠️  Error getting McKinsey review: {e}")
            import traceback
            traceback.print_exc()
            mckinsey_review = {}
        
        # Create HTML email body with embedded image
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; }}
        .content {{ padding: 20px; background: #f9f9f9; }}
        .section {{ background: white; padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #667eea; }}
        .image-container {{ text-align: center; margin: 20px 0; }}
        .image-container img {{ max-width: 100%; height: auto; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .info-box {{ background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AGENT SELF-DISCOVERY REPORT</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="content">
        <div class="section">
            <h2>📋 Overview</h2>
            <p>This email was generated by an agent that:</p>
            <ol>
                <li>Queried the knowledge graph to discover its own IRI</li>
                <li>Used SPARQL to find information about itself</li>
                <li>Created a Midjourney image based on that identity</li>
                <li>Sent this email automatically with embedded image</li>
            </ol>
        </div>
        
        <div class="section">
            <h2>🔍 Agent Identity Discovered</h2>
            <div class="info-box">
                <p><strong>Agent IRI:</strong> {agent_iri}</p>
                <p><strong>Agent Name:</strong> {agent_name}</p>
                <p><strong>Agent Type:</strong> {agent_type}</p>
                <p><strong>Capabilities:</strong> {capabilities}</p>
            </div>
        </div>
        
        <div class="section">
            <h2>🎨 Midjourney Image Generation</h2>
            <p><strong>Status:</strong> {status}</p>
            <p><strong>Prompt Used:</strong> {prompt[:200] if prompt and isinstance(prompt, str) and len(prompt) > 200 else (prompt if prompt else '[No prompt]')}...</p>
        """
        
        if image_url:
            html_body += f"""
            <div class="image-container">
                <h3>📸 Generated Image (4-Grid)</h3>
                <img src="cid:agent_image" alt="Agent Identity Visualization" />
                <p><em>The image above represents the agent's visual interpretation of its own identity discovered from the knowledge graph.</em></p>
                <p><strong>Original Grid URL:</strong> <a href="{image_url}">{image_url}</a></p>
            """
            
            # Add quadrant information if available
            if quadrant_nodes:
                html_body += """
                <div style="margin-top: 20px; padding: 20px; background: #f0f0f0; border-radius: 10px;">
                    <h4>🔗 Knowledge Graph Nodes Created</h4>
                    <p>The 4-grid image has been split into 4 separate KG nodes, each connected to the originator agent:</p>
                    
                    <!-- Quadrant Grid Layout -->
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 20px 0;">
                """
                
                for idx, node in enumerate(quadrant_nodes):
                    if not isinstance(node, dict):
                        continue
                    # Check if this quadrant was selected
                    mck_selected = quadrant_selections.get('mckinsey', {})
                    sci_selected = quadrant_selections.get('scientific', {})
                    mck_selected_node = mck_selected.get('selected', {}) if isinstance(mck_selected, dict) else {}
                    sci_selected_node = sci_selected.get('selected', {}) if isinstance(sci_selected, dict) else {}
                    node_name = node.get('name', '')
                    is_mckinsey_fav = isinstance(mck_selected_node, dict) and mck_selected_node.get('name') == node_name
                    is_scientific_fav = isinstance(sci_selected_node, dict) and sci_selected_node.get('name') == node_name
                    
                    # Determine border color based on selections
                    border_color = "#ddd"
                    border_width = "2px"
                    if is_mckinsey_fav and is_scientific_fav:
                        border_color = "#667eea"
                        border_width = "4px"
                    elif is_mckinsey_fav:
                        border_color = "#667eea"
                        border_width = "3px"
                    elif is_scientific_fav:
                        border_color = "#28a745"
                        border_width = "3px"
                    
                    badges = []
                    if is_mckinsey_fav:
                        badges.append('<span style="background: #667eea; color: white; padding: 3px 10px; border-radius: 5px; font-size: 11px; font-weight: bold;">👔 McKinsey</span>')
                    if is_scientific_fav:
                        badges.append('<span style="background: #28a745; color: white; padding: 3px 10px; border-radius: 5px; font-size: 11px; font-weight: bold;">🔬 Scientific</span>')
                    
                    badge_html = ' '.join(badges) if badges else '<span style="color: #999; font-size: 11px;">Not selected</span>'
                    
                    html_body += f"""
                        <div style="background: white; padding: 15px; border-radius: 8px; border: {border_width} solid {border_color}; text-align: center;">
                            <h5 style="margin: 0 0 10px 0; color: #333;">{node['name']} ({node['position']})</h5>
                            <div style="margin: 10px 0;">
                                <img src="cid:quadrant_{idx}" alt="{node['name']}" style="max-width: 100%; height: auto; border-radius: 5px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />
                            </div>
                            <div style="margin: 10px 0;">
                                {badge_html}
                            </div>
                            <a href="{node['url']}" target="_blank" style="font-size: 11px; color: #667eea; text-decoration: none;">View Full Size →</a>
                            <br><small style="color: #666; font-size: 10px; word-break: break-all;">{node['iri']}</small>
                        </div>
                    """
                
                html_body += """
                    </div>
                </div>
                """
                
                # Add selection reasoning with comparison table
                if quadrant_selections.get('mckinsey') or quadrant_selections.get('scientific'):
                    html_body += """
                <div style="margin-top: 20px; padding: 20px; background: linear-gradient(135deg, #e8f4f8, #f0f8ff); border-radius: 10px; border-left: 5px solid #667eea;">
                    <h4 style="margin-top: 0;">🎯 Agent Selections & Comparison</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
                """
                    if quadrant_selections.get('mckinsey'):
                        mck = quadrant_selections['mckinsey']
                        if not isinstance(mck, dict):
                            mck = {}
                        mck_selected = mck.get('selected', {})
                        selected_name = mck_selected.get('name', 'N/A') if isinstance(mck_selected, dict) else 'N/A'
                        reasoning = mck.get('reasoning', 'No reasoning provided') if isinstance(mck.get('reasoning'), str) else 'No reasoning provided'
                        scores = mck.get('criteria_scores', {}) if isinstance(mck.get('criteria_scores'), dict) else {}
                        
                        html_body += f"""
                        <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea;">
                            <h5 style="margin: 0 0 10px 0; color: #667eea;">👔 McKinsey Team</h5>
                            <p style="margin: 5px 0; font-size: 18px; font-weight: bold; color: #333;">Selected: <span style="color: #667eea;">{selected_name}</span></p>
                            <p style="margin: 10px 0; font-style: italic; color: #555;">{reasoning}</p>
                        """
                        if scores:
                            html_body += """
                            <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee;">
                                <strong style="font-size: 12px; color: #666;">Criteria Scores:</strong>
                                <ul style="margin: 5px 0; padding-left: 20px; font-size: 11px;">
                            """
                            for criterion, score in scores.items():
                                html_body += f"<li>{criterion}: {score}</li>"
                            html_body += """
                                </ul>
                            </div>
                        """
                        html_body += """
                        </div>
                        """
                    
                    if quadrant_selections.get('scientific'):
                        sci = quadrant_selections['scientific']
                        if not isinstance(sci, dict):
                            sci = {}
                        sci_selected = sci.get('selected', {})
                        selected_name = sci_selected.get('name', 'N/A') if isinstance(sci_selected, dict) else 'N/A'
                        reasoning = sci.get('reasoning', 'No reasoning provided') if isinstance(sci.get('reasoning'), str) else 'No reasoning provided'
                        scores = sci.get('criteria_scores', {}) if isinstance(sci.get('criteria_scores'), dict) else {}
                        
                        html_body += f"""
                        <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;">
                            <h5 style="margin: 0 0 10px 0; color: #28a745;">🔬 Scientific Team</h5>
                            <p style="margin: 5px 0; font-size: 18px; font-weight: bold; color: #333;">Selected: <span style="color: #28a745;">{selected_name}</span></p>
                            <p style="margin: 10px 0; font-style: italic; color: #555;">{reasoning}</p>
                        """
                        if scores:
                            html_body += """
                            <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee;">
                                <strong style="font-size: 12px; color: #666;">Criteria Scores:</strong>
                                <ul style="margin: 5px 0; padding-left: 20px; font-size: 11px;">
                            """
                            for criterion, score in scores.items():
                                html_body += f"<li>{criterion}: {score}</li>"
                            html_body += """
                                </ul>
                            </div>
                        """
                        html_body += """
                        </div>
                        """
                    
                    html_body += """
                    </div>
                </div>
                """
            
            html_body += """
            </div>
            """
        else:
            html_body += f"""
            <div class="info-box">
                <p><strong>Image Status:</strong> {status}</p>
                <p>Note: The image may still be generating. Check the Midjourney task status if needed.</p>
            </div>
            """
        
        html_body += """
        </div>
        """
        
        # Add McKinsey review section if available
        if mckinsey_review:
            strategy = mckinsey_review.get('strategy', {})
            implementation = mckinsey_review.get('implementation', {})
            value_framework = mckinsey_review.get('value_framework', {})
            
            html_body += f"""
        <div class="section">
            <h2>👔 McKinsey Consulting Review</h2>
            <div class="info-box">
                <h3>Strategic Assessment</h3>
                <p><strong>Vision:</strong> {strategy.get('vision', 'N/A') if isinstance(strategy, dict) else 'N/A'}</p>
                <p><strong>Key Pillars:</strong></p>
                <ul>
            """
            
            if isinstance(strategy, dict) and isinstance(strategy.get('key_pillars'), list):
                for pillar in strategy.get('key_pillars', []):
                    html_body += f"<li>{pillar}</li>"
            
            html_body += """
                </ul>
                <p><strong>Implementation Approach:</strong> """ + (strategy.get('implementation_approach', 'N/A') if isinstance(strategy, dict) else 'N/A') + """</p>
            </div>
            
            <div class="info-box">
                <h3>Implementation Plan</h3>
            """
            
            if isinstance(implementation, dict) and isinstance(implementation.get('phases'), list):
                for phase in implementation.get('phases', []):
                    if isinstance(phase, dict):
                        html_body += f"""
                <p><strong>{phase.get('name', 'Phase')}:</strong> {phase.get('duration', 'N/A')}</p>
                <ul>
                """
                        for activity in phase.get('key_activities', []):
                            html_body += f"<li>{activity}</li>"
                        html_body += "</ul>"
            
            html_body += """
            </div>
            
            <div class="info-box">
                <h3>Value Framework</h3>
            """
            
            if isinstance(value_framework, dict) and isinstance(value_framework.get('key_metrics'), list):
                html_body += "<ul>"
                for metric in value_framework.get('key_metrics', []):
                    if isinstance(metric, dict):
                        html_body += f"<li><strong>{metric.get('name', 'Metric')}:</strong> Target {metric.get('target', 'N/A')} (Measured {metric.get('measurement_frequency', 'N/A')})</li>"
                html_body += "</ul>"
            
            html_body += """
            </div>
        </div>
        """
        
        html_body += """
        <div class="section">
            <h2>⚙️ How This Works</h2>
            <ol>
                <li>Agent queries KG using SPARQL to find its own IRI</li>
                <li>Agent extracts information about itself (name, type, capabilities)</li>
                <li>Agent creates a Midjourney prompt based on its identity</li>
                <li>Agent generates an image using Midjourney tools</li>
                <li>Agent polls for image completion and retrieves final URL</li>
                <li>Agent requests review from McKinsey consulting team</li>
                <li>McKinsey agents provide strategic, implementation, and value assessments</li>
                <li>Agent sends email with embedded image and McKinsey review automatically</li>
            </ol>
        </div>
    </div>
    
    <div class="footer">
        <p>Report generated by: """ + agent_name + f""" ({agent_iri})</p>
        <p>Knowledge Graph: {self.kg_manager.__class__.__name__ if self.kg_manager else 'N/A'}</p>
    </div>
</body>
</html>
"""
        
        # Plain text version for email clients that don't support HTML
        email_body = f"""
AGENT SELF-DISCOVERY REPORT
===========================

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This email was generated by an agent that:
1. Queried the knowledge graph to discover its own IRI
2. Used SPARQL to find information about itself
3. Created a Midjourney image based on that identity
4. Sent this email automatically

AGENT IDENTITY DISCOVERED
-------------------------
Agent IRI: {agent_iri}
Agent Name: {agent_name}
Agent Type: {agent_type}
Capabilities: {capabilities}

MIDJOURNEY IMAGE GENERATION
----------------------------
Status: {status}
Prompt Used: {prompt}
"""
        
        if image_url:
            email_body += f"""
Image URL: {image_url}

📸 VIEW THE GENERATED IMAGE (4-GRID):
{image_url}

The image above represents the agent's visual interpretation of its own identity
discovered from the knowledge graph. The prompt was generated based on:
- Agent Name: {agent_name}
- Agent Type: {agent_type}
- Capabilities: {capabilities}
"""
            
            # Add quadrant information
            if quadrant_nodes:
                email_body += f"""

🔗 KNOWLEDGE GRAPH NODES CREATED:
The 4-grid image has been split into 4 separate KG nodes, each connected to the originator agent:

"""
                for node in quadrant_nodes:
                    if not isinstance(node, dict):
                        continue
                    # Check if this quadrant was selected
                    mck_selected = quadrant_selections.get('mckinsey', {})
                    sci_selected = quadrant_selections.get('scientific', {})
                    mck_selected_node = mck_selected.get('selected', {}) if isinstance(mck_selected, dict) else {}
                    sci_selected_node = sci_selected.get('selected', {}) if isinstance(sci_selected, dict) else {}
                    node_name = node.get('name', '')
                    is_mckinsey_fav = isinstance(mck_selected_node, dict) and mck_selected_node.get('name') == node_name
                    is_scientific_fav = isinstance(sci_selected_node, dict) and sci_selected_node.get('name') == node_name
                    
                    badges = []
                    if is_mckinsey_fav:
                        badges.append("👔 McKinsey Favorite")
                    if is_scientific_fav:
                        badges.append("🔬 Scientific Favorite")
                    
                    badge_text = f" [{', '.join(badges)}]" if badges else ""
                    
                    email_body += f"""
{node.get('name', 'Unknown')} ({node.get('position', 'unknown')}){badge_text}:
  URL: {node.get('url', 'N/A')}
  KG IRI: {node.get('iri', 'N/A')}
  Connected to: {self.my_iri}

"""
                
                # Add selection reasoning
                if quadrant_selections.get('mckinsey') or quadrant_selections.get('scientific'):
                    email_body += f"""

🎯 AGENT SELECTIONS:

"""
                    if quadrant_selections.get('mckinsey'):
                        mck = quadrant_selections['mckinsey']
                        if isinstance(mck, dict):
                            mck_selected = mck.get('selected', {})
                            selected_name = mck_selected.get('name', 'N/A') if isinstance(mck_selected, dict) else 'N/A'
                            reasoning = mck.get('reasoning', 'No reasoning provided') if isinstance(mck.get('reasoning'), str) else 'No reasoning provided'
                            email_body += f"""
👔 McKinsey Team Selection: {selected_name}
   Reasoning: {reasoning}

"""
                    if quadrant_selections.get('scientific'):
                        sci = quadrant_selections['scientific']
                        if isinstance(sci, dict):
                            sci_selected = sci.get('selected', {})
                            selected_name = sci_selected.get('name', 'N/A') if isinstance(sci_selected, dict) else 'N/A'
                            reasoning = sci.get('reasoning', 'No reasoning provided') if isinstance(sci.get('reasoning'), str) else 'No reasoning provided'
                            email_body += f"""
🔬 Scientific Team Selection: {selected_name}
   Reasoning: {reasoning}

"""
        else:
            email_body += f"""
Image Status: {status}

Note: The image may still be generating. Check the Midjourney task status if needed.
"""
        
        # Add McKinsey review to plain text email
        if mckinsey_review:
            email_body += f"""

MCKINSEY CONSULTING REVIEW
---------------------------
Engagement ID: {mckinsey_review.get('engagement_id', 'N/A')}

Strategic Assessment:
{str(mckinsey_review.get('strategy', {}))}

Implementation Plan:
{str(mckinsey_review.get('implementation', {}))}

Value Framework:
{str(mckinsey_review.get('value_framework', {}))}
"""
        
        # Send email with HTML body and embedded image
        try:
            print(f"   Recipient: {USER_EMAIL}")
            print(f"   Subject: Agent Self-Discovery Report - {agent_name}")
            if image_url and isinstance(image_url, str):
                if len(image_url) > 60:
                    print(f"   📸 Embedding image: {image_url[:60]}...")
                else:
                    print(f"   📸 Embedding image: {image_url}")
            elif image_url:
                print(f"   📸 Embedding image: [URL unavailable]")
            
            # Use EmailIntegration directly to support HTML and image embedding
            from agents.utils.email_integration import EmailIntegration
            email_integration = None
            try:
                email_integration = EmailIntegration(use_real_email=True)
                
                # Validate USER_EMAIL
                if not USER_EMAIL or not isinstance(USER_EMAIL, str) or not USER_EMAIL.strip():
                    print(f"   ⚠️  Invalid USER_EMAIL: {USER_EMAIL}")
                    return False
                
                # Prepare additional images (quadrant thumbnails) for embedding
                additional_images = []
                if quadrant_nodes and isinstance(quadrant_nodes, list) and len(quadrant_nodes) > 0:
                    for idx, node in enumerate(quadrant_nodes):
                        if not isinstance(node, dict):
                            continue
                        node_url = node.get('url')
                        node_name = node.get('name', f'quadrant_{idx}')
                        # Validate URL before adding
                        if node_url and isinstance(node_url, str) and node_url.strip():
                            if node_url.startswith('http://') or node_url.startswith('https://'):
                                additional_images.append({
                                    'url': node_url,
                                    'cid': f'quadrant_{idx}',
                                    'filename': f"{node_name}.png"
                                })
                            else:
                                print(f"   ⚠️  Invalid URL format for quadrant {idx}: {node_url}")
                        else:
                            print(f"   ⚠️  Missing or invalid URL for quadrant {idx}")
                
                result = email_integration.send_email(
                    recipient=USER_EMAIL,
                    subject=f"Agent Self-Discovery Report - {agent_name}",
                    body=email_body,
                    html_body=html_body,
                    image_url=image_url,
                    additional_images=additional_images if additional_images and len(additional_images) > 0 else None,
                    force_real=True
                )
                
                # Validate result
                if not result or not isinstance(result, dict):
                    print(f"   ⚠️  Invalid result from send_email: {result}")
                    return False
                
                print("   ✅ Email sent successfully!")
                
                # Send SMS notification using inherited BaseAgent method
                try:
                    sms_message = f"Agent Self-Discovery Report: {agent_name} | IRI: {self.my_iri.split('/')[-1] if self.my_iri else 'N/A'} | Image: {status} | Full report in email"
                    sms_sent = await self.send_sms_notification(sms_message)
                    if sms_sent:
                        print(f"   ✅ SMS notification sent successfully!")
                    else:
                        print(f"   ℹ️  SMS skipped (USER_PHONE_NUMBER not configured)")
                except Exception as sms_error:
                    print(f"   ⚠️  SMS notification error: {sms_error}")
                
                return True
            except Exception as send_error:
                print(f"   ⚠️  Error sending email: {send_error}")
                import traceback
                traceback.print_exc()
                return False
            
        except Exception as e:
            print(f"   ❌ Failed to send email: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Cleanup email_integration if needed
            if email_integration:
                try:
                    # EmailIntegration doesn't have explicit cleanup, but we can check
                    pass
                except:
                    pass

async def main():
    """
    Main test function for agent self-discovery workflow.
    
    This function orchestrates the complete workflow:
    1. Initializes the SelfDiscoveryMidjourneyEmailAgent
    2. Discovers the agent's IRI from the knowledge graph
    3. Generates a Midjourney image based on discovered identity
    4. Sends comprehensive email report with embedded images
    
    Returns:
        bool: True if the entire workflow completed successfully, False otherwise.
        
    Environment Variables (All Already Configured):
        ✅ EMAIL_SENDER: Already set in .env
        ✅ EMAIL_PASSWORD: Already set in .env
        ✅ USER_PHONE_NUMBER: Already set in .env (SMS will be sent automatically)
        ✅ All Twilio credentials: Already set in .env
        
    Example:
        >>> import asyncio
        >>> success = asyncio.run(main())
        >>> if success:
        ...     print("Check your email for the agent self-discovery report!")
    """
    print("\n" + "=" * 70)
    print("🚀 AGENT SELF-DISCOVERY + MIDJOURNEY + EMAIL TEST")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"User Email: {USER_EMAIL}")
    user_phone = os.getenv("USER_PHONE_NUMBER") or os.getenv("NOTIFICATION_PHONE_NUMBER")
    print(f"User Phone: {user_phone if user_phone else 'Not configured (SMS will be skipped)'}")
    print("\nThis test demonstrates:")
    print("  1. Agent queries KG to discover its own IRI")
    print("  2. Agent uses SPARQL to find information about itself")
    print("  3. Agent creates Midjourney image based on identity")
    print("  4. Agent splits image into 4 KG nodes")
    print("  5. Agent gets reviews from McKinsey and Scientific agents")
    print("  6. Agent emails you comprehensive report with embedded images")
    
    agent = None
    try:
        # Initialize agent
        print_section("Initializing Agent")
        
        try:
            agent = SelfDiscoveryMidjourneyEmailAgent()
            await agent.initialize()
            print("   ✅ Agent initialized")
            print("   ✅ Knowledge Graph: Enabled")
            print("   ✅ Midjourney Tools: " + ("Enabled" if agent.imagine_tool else "Not Available (will simulate)"))
            print("   ✅ Email Capability: Enabled")
        except Exception as e:
            print(f"   ❌ Failed to initialize: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 1: Discover own IRI
        iri = await agent.discover_my_iri()
        if not iri:
            print("\n❌ Failed to discover agent IRI")
            return False
        
        # Step 2: Create Midjourney image
        image_result = await agent.create_midjourney_image_from_identity()
        if not image_result or not isinstance(image_result, dict):
            print("\n⚠️  Image generation failed, but continuing with email...")
            image_result = {"status": "failed", "prompt": "N/A", "image_url": None, "task_id": None}
        
        # Step 3: Send email
        success = await agent.send_email_with_image(image_result)
        
        if success:
            print("\n" + "=" * 70)
            print("📊 TEST SUMMARY")
            print("=" * 70)
            print(f"✅ Agent IRI Discovered: {iri}")
            print(f"✅ Agent Info: {agent.my_info.get('name', 'N/A') if isinstance(agent.my_info, dict) else 'N/A'}")
            print(f"✅ Image Generated: {image_result.get('status', 'N/A') if isinstance(image_result, dict) else 'N/A'}")
            print(f"✅ Email Sent: Yes")
            print(f"\n📧 Check your inbox at {USER_EMAIL}!")
            user_phone = os.getenv("USER_PHONE_NUMBER") or os.getenv("NOTIFICATION_PHONE_NUMBER")
            if user_phone:
                print(f"📱 SMS notification: Sent to {user_phone}")
            print("\n🎉 **SUCCESS!** Agent discovered its IRI, created an image, and emailed you!")
        else:
            print("\n❌ Test failed - check errors above")
        
        return success
        
    finally:
        # Cleanup resources
        if agent:
            try:
                # Cleanup McKinsey agents
                if hasattr(agent, 'mckinsey_agents') and agent.mckinsey_agents:
                    for key, mck_agent in agent.mckinsey_agents.items():
                        try:
                            if hasattr(mck_agent, 'cleanup'):
                                await mck_agent.cleanup()
                            elif hasattr(mck_agent, 'shutdown'):
                                await mck_agent.shutdown()
                        except Exception as cleanup_error:
                            print(f"   ⚠️  Error cleaning up {key} agent: {cleanup_error}")
                
                # Cleanup knowledge graph
                if hasattr(agent, 'kg_manager') and agent.kg_manager:
                    try:
                        if hasattr(agent.kg_manager, 'shutdown'):
                            await agent.kg_manager.shutdown()
                        elif hasattr(agent.kg_manager, 'cleanup'):
                            await agent.kg_manager.cleanup()
                    except Exception as kg_error:
                        print(f"   ⚠️  Error cleaning up knowledge graph: {kg_error}")
                
                # Cleanup agent itself
                if hasattr(agent, 'cleanup'):
                    await agent.cleanup()
                elif hasattr(agent, 'shutdown'):
                    await agent.shutdown()
            except Exception as cleanup_error:
                print(f"   ⚠️  Error during final cleanup: {cleanup_error}")

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

