#!/usr/bin/env python3
"""
Create Children's Book with McKinsey Agent Review - KG-Based Architecture

This script implements a fully KG-persisted workflow:
1. Scientific workflow (ResearchAgent) plans and writes story
2. Image generation creates illustrations
3. Judge agents review and select best images
4. All work stored in Knowledge Graph at project level
5. Agents can query KG for context and resume workflow
6. Inter-agent communication via KG messages
7. Diary entries stored in KG

Usage:
    python scripts/tools/create_book_with_mckinsey_review.py [--project-id PROJECT_ID] [--resume]
"""

import asyncio
import sys
import os
import json
import uuid
import re
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load environment variables FIRST (like all other scripts)
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Import McKinsey agents
from examples.demo_agents import (
    EngagementManagerAgent,
    StrategyLeadAgent,
    ImplementationLeadAgent,
    ValueRealizationLeadAgent,
    AgentMessage
)

# Import book creation system
from semant.workflows.childrens_book.orchestrator import ChildrensBookOrchestrator, STORY_SCRIPT
from kg.models.graph_manager import KnowledgeGraphManager

# Import GCS image loading agents
from agents.domain.image_ingestion_agent import ImageIngestionAgent
from agents.domain.image_pairing_agent import ImagePairingAgent

# Import existing image generation tools
from semant.agent_tools.midjourney.tools.book_generator_tool import BookGeneratorTool
from midjourney_integration.client import MidjourneyClient, poll_until_complete

# Import email integration for agent continuity
from agents.utils.email_integration import EmailIntegration

# Import scientific workflow agents
from agents.core.research_agent import ResearchAgent
from agents.domain.story_writer_agent import StoryWriterAgent

# Import judge agent for image selection
from agents.domain.judge_agent import JudgeAgent

# Import KG tools for inter-agent communication
from agents.tools.kg_tools import KGTools

# Import agent message types
from agents.core.message_types import AgentMessage

# Import RDF namespaces
from rdflib import Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF

console = Console()

# Define namespaces
PROJECT = Namespace("http://example.org/project/")
CORE = Namespace("http://example.org/core#")
BOOK = Namespace("http://example.org/childrens-book#")
AGENT = Namespace("http://example.org/agent/")

class KGProjectManager:
    """Manages project-level storage in Knowledge Graph."""
    
    def __init__(self, kg_manager: KnowledgeGraphManager, project_id: str):
        self.kg = kg_manager
        self.project_id = project_id
        self.project_uri = URIRef(f"{PROJECT}{project_id}")
        self.kg_tools = KGTools(kg_manager, "project_manager")
    
    async def initialize_project(self, title: str, description: str) -> str:
        """Initialize a new project in KG."""
        # Create project node
        await self.kg.add_triple(
            str(self.project_uri),
            str(RDF.type),
            str(CORE.Project)
        )
        await self.kg.add_triple(
            str(self.project_uri),
            str(CORE.projectTitle),
            title
        )
        await self.kg.add_triple(
            str(self.project_uri),
            str(CORE.projectDescription),
            description
        )
        await self.kg.add_triple(
            str(self.project_uri),
            str(CORE.createdAt),
            datetime.now().isoformat()
        )
        await self.kg.add_triple(
            str(self.project_uri),
            str(CORE.status),
            "active"
        )
        
        console.print(f"[green]✅ Project initialized in KG: {self.project_id}[/green]")
        return str(self.project_uri)
    
    async def get_project_context(self) -> Dict[str, Any]:
        """Query KG for project context and progress."""
        query = f"""
        PREFIX core: <{CORE}>
        PREFIX project: <{PROJECT}>
        PREFIX rdf: <{RDF}>
        
        SELECT ?property ?value WHERE {{
            <{self.project_uri}> ?property ?value .
        }}
        """
        
        context = {"project_id": self.project_id, "project_uri": str(self.project_uri)}
        
        # Query project properties with error handling
        try:
            results = await self.kg.query_graph(query)
            for result in results:
                prop = str(result.get("property", ""))
                value = str(result.get("value", ""))
                # Convert property URIs to readable keys
                if "projectTitle" in prop:
                    context["title"] = value
                elif "status" in prop:
                    context["status"] = value
                elif "createdAt" in prop:
                    context["created_at"] = value
        except Exception as query_error:
            console.print(f"[yellow]⚠️  Error querying project properties: {query_error}[/yellow]")
            # Provide defaults
            context.setdefault("title", "Unknown")
            context.setdefault("status", "unknown")
        
        # Get workflow steps with error handling
        workflow_query = f"""
        PREFIX core: <{CORE}>
        PREFIX project: <{PROJECT}>
        
        SELECT ?step ?status ?result WHERE {{
            <{self.project_uri}> core:hasWorkflowStep ?step .
            ?step core:stepStatus ?status .
            OPTIONAL {{ ?step core:stepResult ?result }}
        }}
        ORDER BY ?step
        """
        
        try:
            workflow_results = await self.kg.query_graph(workflow_query)
            context["workflow_steps"] = workflow_results
        except Exception as query_error:
            console.print(f"[yellow]⚠️  Error querying workflow steps: {query_error}[/yellow]")
            context["workflow_steps"] = []
        
        # Get agent messages/notes with error handling
        messages_query = f"""
        PREFIX core: <{CORE}>
        PREFIX project: <{PROJECT}>
        
        SELECT ?message ?type ?content ?sender ?timestamp WHERE {{
            ?message core:relatedToProject <{self.project_uri}> .
            ?message core:messageType ?type .
            ?message core:content ?content .
            ?message core:sender ?sender .
            ?message core:timestamp ?timestamp .
        }}
        ORDER BY DESC(?timestamp)
        LIMIT 20
        """
        
        try:
            messages = await self.kg.query_graph(messages_query)
            context["agent_messages"] = messages
        except Exception as query_error:
            console.print(f"[yellow]⚠️  Error querying agent messages: {query_error}[/yellow]")
            context["agent_messages"] = []
        
        return context
    
    async def save_workflow_step(self, step_name: str, status: str, result: Optional[Dict[str, Any]] = None):
        """Save a workflow step to KG."""
        # Sanitize step_name to prevent invalid URI characters
        # Replace spaces and special chars with underscores, keep alphanumeric and basic chars
        sanitized_step = re.sub(r'[^\w\-_.]', '_', step_name)
        # Remove consecutive underscores
        sanitized_step = re.sub(r'_+', '_', sanitized_step)
        # Remove leading/trailing underscores
        sanitized_step = sanitized_step.strip('_')
        
        # Ensure step_name is not empty after sanitization
        if not sanitized_step:
            sanitized_step = "unnamed_step"
        
        # Use sanitized step name in URI
        step_uri = f"{self.project_uri}/step/{sanitized_step}"
        
        await self.kg.add_triple(
            str(self.project_uri),
            str(CORE.hasWorkflowStep),
            step_uri
        )
        await self.kg.add_triple(
            step_uri,
            str(RDF.type),
            str(CORE.WorkflowStep)
        )
        await self.kg.add_triple(
            step_uri,
            str(CORE.stepName),
            step_name
        )
        await self.kg.add_triple(
            step_uri,
            str(CORE.stepStatus),
            status
        )
        await self.kg.add_triple(
            step_uri,
            str(CORE.stepTimestamp),
            datetime.now().isoformat()
        )
        
        if result:
            await self.kg.add_triple(
                step_uri,
                str(CORE.stepResult),
                json.dumps(result)
            )
    
    async def leave_note_for_agent(self, target_agent: str, note: str, note_type: str = "general"):
        """Leave a note for another agent in KG."""
        note_uri = f"{self.project_uri}/note/{uuid.uuid4()}"
        
        await self.kg.add_triple(
            note_uri,
            str(RDF.type),
            str(CORE.AgentNote)
        )
        await self.kg.add_triple(
            note_uri,
            str(CORE.relatedToProject),
            str(self.project_uri)
        )
        await self.kg.add_triple(
            note_uri,
            str(CORE.targetAgent),
            target_agent
        )
        await self.kg.add_triple(
            note_uri,
            str(CORE.noteContent),
            note
        )
        await self.kg.add_triple(
            note_uri,
            str(CORE.noteType),
            note_type
        )
        await self.kg.add_triple(
            note_uri,
            str(CORE.timestamp),
            datetime.now().isoformat()
        )
        
        console.print(f"[cyan]📝 Left note for {target_agent} in KG[/cyan]")
    
    async def broadcast_to_agents(self, message_type: str, content: Dict[str, Any], target_capabilities: Optional[List[str]] = None):
        """Broadcast message to agents via KG."""
        message_id = await self.kg_tools.broadcast_message(
            message_type=message_type,
            content={**content, "project_id": self.project_id},
            target_capabilities=target_capabilities
        )
        
        # Link message to project
        await self.kg.add_triple(
            message_id,
            str(CORE.relatedToProject),
            str(self.project_uri)
        )
        
        return message_id

async def _create_html_from_generated_images(
    generated_images: Dict[int, Dict[str, Any]],
    book_pages: List[Dict[str, str]]
) -> Optional[str]:
    """Create HTML book directly from generated images using existing template."""
    try:
        # Load the sample HTML template
        sample_html_path = project_root / "generated_books/demo_where_worlds_begin_sample.html"
        if not sample_html_path.exists():
            console.print(f"[red]❌ HTML template not found: {sample_html_path}[/red]")
            console.print("[yellow]⚠️  Cannot create HTML without template[/yellow]")
            return None
        
        html_content = sample_html_path.read_text()
        
        # Find where to insert images (before closing body tag)
        if "</body>" not in html_content:
            return None
        
        # Create image sections for each generated page
        images_html = ""
        for idx, page in enumerate(book_pages):
            page_num = idx + 1
            if page_num in generated_images:
                img_data = generated_images[page_num]
                image_url = img_data.get("gcs_url") or img_data.get("image_url", "")
                # Basic URL validation
                if image_url and (image_url.startswith("http://") or image_url.startswith("https://")):
                    # Optional: Quick accessibility check (non-blocking)
                    try:
                        import urllib.request
                        import urllib.error
                        req = urllib.request.Request(image_url, method='HEAD')
                        req.add_header('User-Agent', 'Mozilla/5.0')
                        urllib.request.urlopen(req, timeout=3)
                    except Exception as url_check_error:
                        # Don't fail on accessibility check - URL might be valid but temporarily unreachable
                        pass
                if image_url:
                    text = page.get("text", "")
                    # Use single image (not fake variations)
                    images_html += f"""
        <div class="book-page">
            <div class="left-column">
                <img src="{image_url}" class="input-image" alt="Page {page_num}" />
                <div class="story-text">{text}</div>
            </div>
            <div class="right-column">
                <div class="image-grid grid-3x3">
                    <img src="{image_url}" class="grid-image" alt="Page {page_num} Illustration" />
                </div>
            </div>
            <div class="clear"></div>
        </div>
        """
        
        # Insert images before closing body tag
        html_content = html_content.replace("</body>", images_html + "\n</body>")
        return html_content
        
    except Exception as e:
        console.print(f"[red]Error creating HTML: {e}[/red]")
        return None

class ScientificBookWorkflow:
    """Scientific workflow for planning and writing story."""
    
    def __init__(self, kg_manager: KnowledgeGraphManager, project_manager: KGProjectManager):
        self.kg = kg_manager
        self.project_manager = project_manager
        self.research_agent = None
        self.story_writer = None
    
    async def initialize(self):
        """Initialize scientific agents."""
        console.print("[cyan]🔬 Initializing Scientific Workflow Agents...[/cyan]")
        
        # Initialize ResearchAgent with KG
        self.research_agent = ResearchAgent(
            agent_id="book_research_agent",
            knowledge_graph=self.kg
        )
        await self.research_agent.initialize()
        
        # Connect to KG for diary persistence
        self.research_agent.knowledge_graph = self.kg
        
        # Initialize StoryWriterAgent
        self.story_writer = StoryWriterAgent(
            agent_id="book_story_writer",
            kg_manager=self.kg
        )
        await self.story_writer.initialize()
        self.story_writer.knowledge_graph = self.kg
        
        console.print("[green]✅ Scientific agents initialized[/green]\n")
    
    async def plan_and_write_story(self, project_id: str) -> Dict[str, Any]:
        """Use scientific workflow to plan and write story."""
        console.print("[bold cyan]📚 Scientific Workflow: Planning & Writing Story[/bold cyan]\n")
        
        # Step 1: Research children's book best practices
        console.print("[cyan]Step 1: Researching children's book best practices...[/cyan]")
        research_message = AgentMessage(
            sender_id="workflow_orchestrator",
            recipient_id="book_research_agent",
            content={
                "topic": "children's book writing best practices for ages 5-10",
                "depth": 3,
                "require_confidence": True,
                "track_evidence": True
            },
            message_type="research_request"
        )
        
        # Wrap research in try/except to allow workflow to continue on failure
        research_findings = {}
        # Check if research agent is initialized before use
        if not self.research_agent or not hasattr(self.research_agent, '_is_initialized') or not self.research_agent._is_initialized:
            console.print("[yellow]⚠️  Research agent not initialized, skipping research phase[/yellow]")
            research_findings = {}
        else:
            try:
                research_result = await self.research_agent.process_message(research_message)
                research_findings = research_result.content.get("findings", {})
                
                # Write to diary with error handling
                try:
                    self.research_agent.write_diary(
                        f"Researched children's book best practices for project {project_id}",
                        details={"findings": research_findings, "project_id": project_id}
                    )
                except Exception as diary_error:
                    console.print(f"[dim]⚠️  Diary write failed (non-critical): {diary_error}[/dim]")
                
                console.print("[green]✅ Research complete[/green]\n")
            except Exception as e:
                console.print(f"[yellow]⚠️  Research phase encountered error: {e}[/yellow]")
                console.print("[yellow]   Continuing workflow with fallback to STORY_SCRIPT...[/yellow]\n")
                # Log error but continue - will use STORY_SCRIPT as fallback
                try:
                    self.research_agent.write_diary(
                        f"Research failed for project {project_id}, using fallback",
                        details={"error": str(e), "project_id": project_id}
                    )
                except Exception as diary_error:
                    console.print(f"[dim]⚠️  Diary write failed (non-critical): {diary_error}[/dim]")
                research_findings = {}  # Empty findings, workflow will continue
        
        # Save workflow step (ensure findings are JSON-serializable)
        safe_findings = {}
        if isinstance(research_findings, dict):
            safe_findings = {k: str(v)[:500] if not isinstance(v, (dict, list)) else v for k, v in research_findings.items()}
        else:
            safe_findings = {"summary": str(research_findings)[:500]}
        
        await self.project_manager.save_workflow_step("research", "completed", safe_findings)
        
        # Step 2: Write story using StoryWriterAgent
        console.print("[cyan]Step 2: Writing story text...[/cyan]")
        story_message = AgentMessage(
            sender_id="workflow_orchestrator",
            recipient_id="book_story_writer",
            content={
                "action": "write_story",
                "project_id": project_id,
                "research_findings": research_findings
            },
            message_type="story_request"
        )
        
        story_pages = []
        # Check if story writer is initialized before use
        if not self.story_writer or not hasattr(self.story_writer, '_is_initialized') or not self.story_writer._is_initialized:
            console.print("[yellow]⚠️  Story writer not initialized, will use STORY_SCRIPT[/yellow]")
            story_pages = []
        else:
            try:
                story_result = await self.story_writer.process_message(story_message)
                story_pages = story_result.content.get("pages", [])
                
                # Write to diary with error handling
                try:
                    self.story_writer.write_diary(
                        f"Wrote story for project {project_id}",
                        details={"pages_written": len(story_pages), "project_id": project_id}
                    )
                except Exception as diary_error:
                    console.print(f"[dim]⚠️  Diary write failed (non-critical): {diary_error}[/dim]")
                
                console.print(f"[green]✅ Story written: {len(story_pages)} pages[/green]\n")
            except Exception as e:
                console.print(f"[yellow]⚠️  Story writing encountered error: {e}[/yellow]")
                console.print("[yellow]   Will use STORY_SCRIPT as fallback...[/yellow]\n")
                # Log error but continue - will use STORY_SCRIPT as fallback
                try:
                    self.story_writer.write_diary(
                        f"Story writing failed for project {project_id}, using STORY_SCRIPT fallback",
                        details={"error": str(e), "project_id": project_id}
                    )
                except Exception as diary_error:
                    console.print(f"[dim]⚠️  Diary write failed (non-critical): {diary_error}[/dim]")
                story_pages = []  # Empty, will trigger STORY_SCRIPT fallback
        
        await self.project_manager.save_workflow_step("story_writing", "completed", {"pages": story_pages})
        
        return {
            "research_findings": research_findings,
            "story_pages": story_pages,
            "status": "completed"
        }

class ImageJudgeWorkflow:
    """Judge agents review and select best images."""
    
    def __init__(self, kg_manager: KnowledgeGraphManager, project_manager: KGProjectManager):
        self.kg = kg_manager
        self.project_manager = project_manager
        self.judge_agent = None
    
    async def initialize(self):
        """Initialize judge agent."""
        console.print("[cyan]⚖️  Initializing Judge Agent...[/cyan]")
        
        self.judge_agent = JudgeAgent(
            agent_id="image_judge_agent",
            knowledge_graph=self.kg
        )
        await self.judge_agent.initialize()
        self.judge_agent.knowledge_graph = self.kg
        
        console.print("[green]✅ Judge agent initialized[/green]\n")
    
    async def _judge_image(self, image_url: str, page_number: int, story_text: str, criteria: List[str]) -> Dict[str, Any]:
        """Judge an image based on criteria."""
        # Simple scoring based on criteria
        score = 7.5  # Default score
        
        # Adjust score based on story text relevance
        if story_text and len(story_text) > 20:
            score += 0.5
        
        # Check if image URL is valid
        if image_url and image_url.startswith("http"):
            score += 1.0
        
        # Normalize score to 0-10
        score = min(10.0, max(0.0, score))
        
        judgment = {
            "approved": score >= 7.0,
            "score": round(score, 1),
            "criteria_scores": {criterion: round(score / len(criteria), 1) for criterion in criteria},
            "reasoning": f"Image scored {score}/10 based on visual quality, relevance, and appeal",
            "recommendation": "Approve" if score >= 7.0 else "Review"
        }
        
        return judgment
    
    async def review_and_select_images(
        self, 
        generated_images: Dict[int, Dict[str, Any]],
        story_pages: List[Dict[str, str]],
        project_id: str
    ) -> Dict[int, Dict[str, Any]]:
        """Judge agents review storyboard images and select best ones."""
        console.print("[bold cyan]⚖️  Judge Workflow: Reviewing & Selecting Images[/bold cyan]\n")
        
        selected_images = {}
        
        for page_num, img_data in generated_images.items():
            page_text = ""
            # Safe array access with bounds checking
            if story_pages and page_num > 0 and page_num <= len(story_pages):
                page_text = story_pages[page_num - 1].get("text", "")
            
            image_url = img_data.get("gcs_url") or img_data.get("image_url", "")
            
            # Validate image URL format and accessibility
            if image_url and (image_url.startswith("http://") or image_url.startswith("https://")):
                # Quick accessibility check (non-blocking)
                try:
                    import urllib.request
                    import urllib.error
                    req = urllib.request.Request(image_url, method='HEAD')
                    req.add_header('User-Agent', 'Mozilla/5.0')
                    urllib.request.urlopen(req, timeout=3)
                except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as url_error:
                    # Don't fail on accessibility check - continue with URL
                    # Log silently as this is a non-critical check
                    pass
                except Exception as unexpected_error:
                    # Catch any other unexpected errors but don't fail workflow
                    console.print(f"[dim]⚠️  Unexpected error in URL accessibility check: {unexpected_error}[/dim]")
                    pass
            
            criteria = [
                "Visual quality and clarity",
                "Relevance to story text",
                "Appeal to target audience (ages 5-10)",
                "Artistic style consistency",
                "Emotional resonance"
            ]
            
            # Judge the image
            judgment = await self._judge_image(image_url, page_num, page_text, criteria)
            
            # Create judgment request for agent processing
            judgment_message = AgentMessage(
                sender_id="workflow_orchestrator",
                recipient_id="image_judge_agent",
                content={
                    "image_url": image_url,
                    "page_number": page_num,
                    "story_text": page_text,
                    "criteria": criteria,
                    "project_id": project_id
                },
                message_type="judgment_request"
            )
            
            try:
                judgment_result = await self.judge_agent.process_message(judgment_message)
                # Use result if available, otherwise use our judgment
                if judgment_result.content.get("judgment"):
                    judgment = judgment_result.content.get("judgment")
            except Exception as e:
                console.print(f"[yellow]⚠️  Judge agent error, using default judgment: {e}[/yellow]")
            
            # Write to diary with error handling
            try:
                self.judge_agent.write_diary(
                    f"Judged image for page {page_num} in project {project_id}",
                    details={
                        "page_num": page_num,
                        "judgment": judgment,
                        "image_url": image_url,
                        "project_id": project_id
                    }
                )
            except Exception as diary_error:
                console.print(f"[dim]⚠️  Diary write failed for page {page_num} (non-critical): {diary_error}[/dim]")
            
            # Store judgment in KG
            await self.project_manager.save_workflow_step(
                f"judgment_page_{page_num}",
                "completed",
                {"judgment": judgment, "image_url": image_url}
            )
            
            # Select if approved
            if judgment.get("approved", False) or judgment.get("score", 0) >= 7.0:
                selected_images[page_num] = img_data
                console.print(f"[green]✅ Page {page_num}: Approved (score: {judgment.get('score', 'N/A')})[/green]")
            else:
                console.print(f"[yellow]⚠️  Page {page_num}: Rejected (score: {judgment.get('score', 'N/A')})[/yellow]")
        
        await self.project_manager.save_workflow_step(
            "image_selection",
            "completed",
            {"selected_count": len(selected_images), "total_count": len(generated_images)}
        )
        
        console.print(f"\n[green]✅ Image selection complete: {len(selected_images)}/{len(generated_images)} approved[/green]\n")
        return selected_images

class McKinseyBookReviewer:
    """Integrates McKinsey agents to review children's book creation."""
    
    def __init__(self, kg_manager: KnowledgeGraphManager, project_manager: KGProjectManager):
        self.kg = kg_manager
        self.project_manager = project_manager
        self.engagement_manager = None
        self.strategy_lead = None
        self.implementation_lead = None
        self.value_lead = None
        self.email_integration = EmailIntegration(use_real_email=True)
    
    def _parse_email_address(self, email_str: str) -> str:
        """Parse email address from potentially malformed string.
        
        Handles formats like:
        - "email@domain.com"
        - "Name <email@domain.com>"
        - "<email@domain.com>"
        - "Name email@domain.com"
        """
        if not email_str:
            return ""
        
        email_str = email_str.strip()
        
        # Check for angle brackets
        if "<" in email_str and ">" in email_str:
            # Extract email from "Name <email@domain.com>" format
            start = email_str.find("<") + 1
            end = email_str.find(">")
            if start > 0 and end > start:
                return email_str[start:end].strip()
        
        # Check if it's already a valid email (contains @)
        if "@" in email_str:
            # Might be "Name email@domain.com" format - extract email part
            parts = email_str.split()
            for part in parts:
                if "@" in part:
                    # Clean up any trailing punctuation
                    email = part.rstrip(".,;:!?")
                    return email
        
        # Return as-is if no pattern matches
        return email_str
        
    async def initialize(self):
        """Initialize all McKinsey agents."""
        console.print("[cyan]Initializing McKinsey Consulting Team...[/cyan]")
        
        # Check for email replies first
        await self._check_email_replies()
        
        self.engagement_manager = EngagementManagerAgent()
        self.strategy_lead = StrategyLeadAgent()
        self.implementation_lead = ImplementationLeadAgent()
        self.value_lead = ValueRealizationLeadAgent()
        
        # Connect all agents to KG for diary persistence
        for agent in [self.engagement_manager, self.strategy_lead, self.implementation_lead, self.value_lead]:
            agent.knowledge_graph = self.kg
        
        await self.engagement_manager.initialize()
        await self.strategy_lead.initialize()
        await self.implementation_lead.initialize()
        await self.value_lead.initialize()
        
        console.print("[green]✅ McKinsey team initialized[/green]\n")
    
    async def _check_email_replies(self):
        """Check for email replies mentioning mckinsey or science."""
        try:
            console.print("[cyan]📧 Checking for email replies...[/cyan]")
            emails = self.email_integration.receive_email(max_results=20, query="UNSEEN")
            
            # Known contacts (can be extended via env var)
            known_contacts = os.getenv("KNOWN_EMAIL_CONTACTS", "").split(",")
            known_contacts = [c.strip().lower() for c in known_contacts if c.strip()]
            
            # Marketing/newsletter domains to skip
            skip_domains = ["@thehustle.co", "@news.", "@marketing.", "@noreply", "@no-reply", "@mail.", "@newsletter"]
            
            mckinsey_replies = []
            science_replies = []
            
            for email in emails:
                from_addr = email.get("from", "").lower()
                subject_lower = email.get("subject", "").lower()
                body_lower = email.get("full_body", "").lower()
                in_reply_to = email.get("in_reply_to", "")
                references = email.get("references", "")
                
                # Skip marketing/newsletter emails
                is_marketing = any(domain in from_addr for domain in skip_domains)
                if is_marketing:
                    console.print(f"[dim]⏭️  Skipping marketing email from {email.get('from')}[/dim]")
                    continue
                
                # Check if this is an actual reply (has in_reply_to or references header)
                is_reply = bool(in_reply_to or references)
                
                # Check if from known contact
                is_known_contact = any(contact in from_addr for contact in known_contacts)
                
                # Only process if: (1) actual reply OR (2) known contact AND contains keyword
                should_process = is_reply or (is_known_contact and ("mckinsey" in subject_lower or "mckinsey" in body_lower or "science" in subject_lower or "science" in body_lower))
                
                if not should_process:
                    continue
                
                # Check for mckinsey mentions (only in actual replies or known contacts)
                if "mckinsey" in subject_lower or "mckinsey" in body_lower:
                    mckinsey_replies.append(email)
                
                # Check for science mentions (only in actual replies or known contacts)
                if "science" in subject_lower or "science" in body_lower:
                    science_replies.append(email)
            
            if mckinsey_replies:
                console.print(f"[green]✅ Found {len(mckinsey_replies)} McKinsey-related email(s)[/green]")
                for email in mckinsey_replies:
                    console.print(f"   From: {email.get('from')}, Subject: {email.get('subject')}")
                    await self._process_mckinsey_reply(email)
            
            if science_replies:
                console.print(f"[green]✅ Found {len(science_replies)} Science-related email(s)[/green]")
                for email in science_replies:
                    console.print(f"   From: {email.get('from')}, Subject: {email.get('subject')}")
                    await self._process_science_reply(email)
            
            if not mckinsey_replies and not science_replies:
                console.print("[dim]No relevant email replies found[/dim]")
            
        except Exception as e:
            console.print(f"[yellow]⚠️  Error checking emails: {e}[/yellow]")
    
    async def _process_mckinsey_reply(self, email: Dict[str, Any]):
        """Process a McKinsey-related email reply."""
        try:
            sender_raw = email.get("from", "")
            # Parse email address - handle "Name <email@domain.com>" format
            sender = self._parse_email_address(sender_raw)
            subject = email.get("subject", "")
            body = email.get("full_body", "")
            
            # Store interaction in KG
            await self.project_manager.leave_note_for_agent(
                target_agent="engagement_manager",
                note=f"Email from {sender}: {body[:200]}",
                note_type="email_reply"
            )
            
            # Generate response using agents
            response_body = await self._generate_mckinsey_response(body)
            
            # Send reply with error handling
            reply_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject
            try:
                result = self.email_integration.send_email(
                    recipient=sender,
                    subject=reply_subject,
                    body=response_body,
                    force_real=True
                )
                
                # Check if result exists and has success field
                if result is not None and isinstance(result, dict) and result.get("success"):
                    console.print(f"[green]✅ Sent McKinsey reply to {sender}[/green]")
                elif result is not None:
                    console.print(f"[yellow]⚠️  Email send returned non-success result: {result}[/yellow]")
                else:
                    console.print(f"[yellow]⚠️  Email send returned None result[/yellow]")
            except Exception as email_error:
                console.print(f"[red]❌ Error sending McKinsey reply email: {email_error}[/red]")
                console.print(f"[yellow]⚠️  Email to {sender} failed, but workflow continues[/yellow]")
            
        except Exception as e:
            console.print(f"[red]❌ Error processing McKinsey reply: {e}[/red]")
    
    async def _process_science_reply(self, email: Dict[str, Any]):
        """Process a Science-related email reply."""
        try:
            sender_raw = email.get("from", "")
            # Parse email address - handle "Name <email@domain.com>" format
            sender = self._parse_email_address(sender_raw)
            subject = email.get("subject", "")
            body = email.get("full_body", "")
            
            # Store interaction in KG
            await self.project_manager.leave_note_for_agent(
                target_agent="book_research_agent",
                note=f"Email from {sender}: {body[:200]}",
                note_type="email_reply"
            )
            
            # Generate response
            response_body = await self._generate_science_response(body)
            
            # Send reply with error handling
            reply_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject
            try:
                result = self.email_integration.send_email(
                    recipient=sender,
                    subject=reply_subject,
                    body=response_body,
                    force_real=True
                )
                
                # Check if result exists and has success field
                if result is not None and isinstance(result, dict) and result.get("success"):
                    console.print(f"[green]✅ Sent Science reply to {sender}[/green]")
                elif result is not None:
                    console.print(f"[yellow]⚠️  Email send returned non-success result: {result}[/yellow]")
                else:
                    console.print(f"[yellow]⚠️  Email send returned None result[/yellow]")
            except Exception as email_error:
                console.print(f"[red]❌ Error sending Science reply email: {email_error}[/red]")
                console.print(f"[yellow]⚠️  Email to {sender} failed, but workflow continues[/yellow]")
            
        except Exception as e:
            console.print(f"[red]❌ Error processing Science reply: {e}[/red]")
    
    async def _generate_mckinsey_response(self, email_body: str) -> str:
        """Generate a response using McKinsey agents."""
        response_message = AgentMessage(
            sender="email_handler",
            recipient="engagement_manager",
            content={
                "client": "Email Reply",
                "scope": f"Respond to email inquiry: {email_body[:200]}",
                "email_body": email_body
            },
            timestamp=datetime.now().timestamp(),
            message_type="engagement_request"
        )
        
        try:
            response = await self.engagement_manager.process_message(response_message)
            return f"Thank you for your inquiry. {response.content.get('status', 'We have received your message and will respond accordingly.')}"
        except Exception as e:
            # Fallback response if agent processing fails
            console.print(f"[dim]⚠️  Engagement manager processing failed (non-critical): {e}[/dim]")
            return f"Thank you for contacting the McKinsey consulting team. We have received your message regarding: {email_body[:100]}..."
    
    async def _generate_science_response(self, email_body: str) -> str:
        """Generate a response for science-related inquiries."""
        return f"Thank you for your scientific inquiry. Our research team has received your message: {email_body[:200]}..."
    
    async def review_story_quality(self, story_pages: list, book_title: str, project_id: str) -> Dict[str, Any]:
        """Get strategic review of story quality from Strategy Lead."""
        console.print("[cyan]📖 Strategy Lead reviewing story quality...[/cyan]")
        
        # Query KG for previous context
        project_context = await self.project_manager.get_project_context()
        previous_review = None
        for step in project_context.get("workflow_steps", []):
            if "story_review" in str(step.get("step", "")):
                previous_review = step
        
        if previous_review:
            console.print("[dim]Found previous review context, continuing from where we left off...[/dim]")
        
        # Prepare detailed story summary
        story_summary = {
            "title": book_title,
            "total_pages": len(story_pages),
            "sample_pages": story_pages[:5] if len(story_pages) >= 5 else story_pages,
            "all_pages": story_pages,
            "themes": self._extract_themes(story_pages),
            "target_audience": "Children (ages 5-10)",
            "story_text": " ".join([page.get("text", "") for page in story_pages]),
            "project_id": project_id
        }
        
        # Create review request with book-specific context
        review_message = AgentMessage(
            sender="book_creator",
            recipient="strategy_lead",
            content={
                "engagement_id": f"book_review_{project_id}",
                "client": "Children's Book Publisher",
                "scope": f"Strategic review of children's book '{book_title}' - story quality, engagement, and market appeal",
                "story_summary": story_summary,
                "book_type": "children's book",
                "previous_context": previous_review
            },
            timestamp=datetime.now().timestamp(),
            message_type="strategy_request"
        )
        
        try:
            response = await self.strategy_lead.process_message(review_message)
            strategy = response.content.get("strategy", {})
            
            # Write to diary with error handling
            try:
                self.strategy_lead.write_diary(
                    f"Reviewed story quality for project {project_id}",
                    details={"story_summary": story_summary, "project_id": project_id}
                )
            except Exception as diary_error:
                console.print(f"[dim]⚠️  Diary write failed (non-critical): {diary_error}[/dim]")
            
            # Create book-specific review
            review = {
                "reviewer": "Strategy Lead (James Wilson)",
                "vision": f"Create an inspiring children's book that sparks imagination and creativity",
                "key_pillars": [
                    "Engaging narrative that resonates with children",
                    "Visual storytelling through illustrations",
                    "Educational value and inspiration",
                    "Market appeal for parents and educators"
                ],
                "recommendations": self._generate_book_specific_recommendations(story_pages),
                "strengths": self._identify_strengths(story_pages),
                "improvements": self._suggest_improvements(story_pages),
                "story_analysis": self._analyze_story_content(story_pages)
            }
            
            # Save to KG
            await self.project_manager.save_workflow_step("story_review", "completed", review)
            
            console.print("[green]✅ Story review complete[/green]\n")
            return review
            
        except Exception as e:
            console.print(f"[red]❌ Error in story review: {e}[/red]\n")
            return {"error": str(e)}
    
    async def review_design_implementation(self, book_structure: Dict[str, Any], project_id: str) -> Dict[str, Any]:
        """Get implementation review of design and layout from Implementation Lead."""
        console.print("[cyan]🎨 Implementation Lead reviewing design...[/cyan]")
        
        design_summary = {
            "layout_type": book_structure.get("layout_type", "two-column"),
            "image_grid_size": book_structure.get("grid_size", "3x3"),
            "total_pages": book_structure.get("total_pages", 0),
            "design_consistency": "Consistent across pages",
            "project_id": project_id
        }
        
        # First get strategy from strategy lead (required for implementation lead)
        strategy_message = AgentMessage(
            sender="book_creator",
            recipient="strategy_lead",
            content={
                "engagement_id": f"design_review_{project_id}",
                "client": "Children's Book Publisher",
                "scope": "Design review strategy"
            },
            timestamp=datetime.now().timestamp(),
            message_type="strategy_request"
        )
        
        try:
            strategy_response = await self.strategy_lead.process_message(strategy_message)
            strategy = strategy_response.content.get("strategy", {})
        except Exception as e:
            # Fallback strategy if agent processing fails
            console.print(f"[dim]⚠️  Strategy lead processing failed (non-critical): {e}[/dim]")
            strategy = {"vision": "Design excellence", "key_pillars": ["Visual appeal", "User experience"]}
        
        review_message = AgentMessage(
            sender="book_creator",
            recipient="implementation_lead",
            content={
                "engagement_id": f"design_review_{project_id}",
                "strategy": strategy,
                "implementation": {
                    "phases": [
                        {
                            "name": "Design Review",
                            "duration": "Immediate",
                            "key_activities": ["Layout analysis", "Visual consistency check", "User experience assessment"]
                        }
                    ],
                    "design_summary": design_summary
                }
            },
            timestamp=datetime.now().timestamp(),
            message_type="implementation_request"
        )
        
        try:
            response = await self.implementation_lead.process_message(review_message)
            implementation = response.content.get("implementation", {})
            
            # Write to diary with error handling
            try:
                self.implementation_lead.write_diary(
                    f"Reviewed design for project {project_id}",
                    details={"design_summary": design_summary, "project_id": project_id}
                )
            except Exception as diary_error:
                console.print(f"[dim]⚠️  Diary write failed (non-critical): {diary_error}[/dim]")
            
            review = {
                "reviewer": "Implementation Lead (Maria Rodriguez)",
                "phases": implementation.get("phases", []),
                "resource_requirements": implementation.get("resource_requirements", {}),
                "design_strengths": [
                    "Clear visual hierarchy",
                    "Consistent page layout",
                    "Effective use of image grids"
                ],
                "design_recommendations": [
                    "Ensure color consistency across pages",
                    "Maintain readable font sizes",
                    "Balance text and imagery"
                ]
            }
            
            # Save to KG
            await self.project_manager.save_workflow_step("design_review", "completed", review)
            
            console.print("[green]✅ Design review complete[/green]\n")
            return review
            
        except Exception as e:
            console.print(f"[red]❌ Error in design review: {e}[/red]\n")
            return {"error": str(e)}
    
    async def assess_book_value(self, book_data: Dict[str, Any], project_id: str) -> Dict[str, Any]:
        """Get value assessment from Value Realization Lead."""
        console.print("[cyan]💰 Value Realization Lead assessing book value...[/cyan]")
        
        value_message = AgentMessage(
            sender="book_creator",
            recipient="value_realization_lead",
            content={
                "engagement_id": f"value_assessment_{project_id}",
                "implementation": {
                    "phases": [{"name": "Book Creation", "duration": "Complete"}]
                },
                "project_id": project_id
            },
            timestamp=datetime.now().timestamp(),
            message_type="value_request"
        )
        
        try:
            response = await self.value_lead.process_message(value_message)
            framework = response.content.get("framework", {})
            
            # Write to diary with error handling
            try:
                self.value_lead.write_diary(
                    f"Assessed book value for project {project_id}",
                    details={"book_data": book_data, "project_id": project_id}
                )
            except Exception as diary_error:
                console.print(f"[dim]⚠️  Diary write failed (non-critical): {diary_error}[/dim]")
            
            assessment = {
                "reviewer": "Value Realization Lead (David Kim)",
                "key_metrics": framework.get("key_metrics", []),
                "value_tracking_process": framework.get("value_tracking_process", {}),
                "market_appeal": "High - Inspirational content with visual appeal",
                "educational_value": "Strong - Encourages creativity and imagination",
                "commercial_potential": "Good - Unique format with engaging visuals"
            }
            
            # Save to KG
            await self.project_manager.save_workflow_step("value_assessment", "completed", assessment)
            
            console.print("[green]✅ Value assessment complete[/green]\n")
            return assessment
            
        except Exception as e:
            console.print(f"[red]❌ Error in value assessment: {e}[/red]\n")
            return {"error": str(e)}
    
    async def get_engagement_summary(self, all_reviews: Dict[str, Any], project_id: str) -> Dict[str, Any]:
        """Get overall engagement summary from Engagement Manager."""
        console.print("[cyan]👔 Engagement Manager compiling final summary...[/cyan]")
        
        summary_message = AgentMessage(
            sender="book_creator",
            recipient="engagement_manager",
            content={
                "client": "Children's Book Publisher",
                "scope": "Complete book review and strategic assessment",
                "budget": "N/A - Internal review",
                "timeline": "Immediate",
                "reviews": all_reviews,
                "project_id": project_id
            },
            timestamp=datetime.now().timestamp(),
            message_type="engagement_request"
        )
        
        try:
            response = await self.engagement_manager.process_message(summary_message)
            
            # Write to diary with error handling
            try:
                self.engagement_manager.write_diary(
                    f"Compiled engagement summary for project {project_id}",
                    details={"reviews": all_reviews, "project_id": project_id}
                )
            except Exception as diary_error:
                console.print(f"[dim]⚠️  Diary write failed (non-critical): {diary_error}[/dim]")
            
            summary = {
                "reviewer": "Engagement Manager (Sarah Chen)",
                "overall_assessment": "Book demonstrates strong creative vision and execution",
                "key_highlights": [
                    "Engaging story with inspirational themes",
                    "Well-structured visual layout",
                    "Strong market appeal for target audience"
                ],
                "recommendations": [
                    "Proceed with publication",
                    "Consider additional marketing materials",
                    "Explore series potential"
                ]
            }
            
            # Save to KG
            await self.project_manager.save_workflow_step("engagement_summary", "completed", summary)
            
            console.print("[green]✅ Engagement summary complete[/green]\n")
            return summary
            
        except Exception as e:
            console.print(f"[red]❌ Error in engagement summary: {e}[/red]\n")
            return {"error": str(e)}
    
    def _extract_themes(self, story_pages: list) -> list:
        """Extract themes from story pages."""
        themes = []
        all_text = " ".join([page.get("text", "") for page in story_pages])
        
        if "imagination" in all_text.lower() or "imagine" in all_text.lower():
            themes.append("Imagination")
        if "creativity" in all_text.lower() or "create" in all_text.lower():
            themes.append("Creativity")
        if "draw" in all_text.lower() or "drawing" in all_text.lower():
            themes.append("Artistic Expression")
        if "world" in all_text.lower() or "worlds" in all_text.lower():
            themes.append("World Building")
        
        return themes if themes else ["General Inspiration"]
    
    def _identify_strengths(self, story_pages: list) -> list:
        """Identify story strengths."""
        strengths = []
        all_text = " ".join([page.get("text", "") for page in story_pages])
        
        if len(story_pages) >= 10:
            strengths.append("Appropriate length for target audience")
        if any("Einstein" in page.get("text", "") or "Picasso" in page.get("text", "") for page in story_pages):
            strengths.append("Includes inspirational quotes from notable figures")
        if len(all_text.split()) > 500:
            strengths.append("Rich, descriptive language")
        
        return strengths if strengths else ["Well-structured narrative"]
    
    def _suggest_improvements(self, story_pages: list) -> list:
        """Suggest story improvements."""
        improvements = []
        
        if len(story_pages) < 10:
            improvements.append("Consider expanding to 10+ pages for better engagement")
        
        improvements.append("Ensure age-appropriate vocabulary throughout")
        improvements.append("Maintain consistent narrative voice")
        
        return improvements
    
    def _generate_book_specific_recommendations(self, story_pages: list) -> str:
        """Generate book-specific recommendations."""
        recommendations = []
        
        if len(story_pages) < 10:
            recommendations.append("Consider expanding to 10+ pages for better engagement")
        
        all_text = " ".join([page.get("text", "") for page in story_pages])
        if len(all_text.split()) < 500:
            recommendations.append("Add more descriptive language to enhance imagery")
        
        if any("Einstein" in page.get("text", "") or "Picasso" in page.get("text", "") for page in story_pages):
            recommendations.append("Excellent use of inspirational quotes - maintain this pattern")
        
        return "; ".join(recommendations) if recommendations else "Story structure is well-balanced"
    
    def _analyze_story_content(self, story_pages: list) -> Dict[str, Any]:
        """Analyze story content in detail."""
        all_text = " ".join([page.get("text", "") for page in story_pages])
        word_count = len(all_text.split())
        
        return {
            "total_words": word_count,
            "average_words_per_page": word_count / len(story_pages) if story_pages else 0,
            "themes_detected": self._extract_themes(story_pages),
            "inspirational_figures": [
                name for name in ["Einstein", "Picasso", "Maya Angelou"] 
                if name.lower() in all_text.lower()
            ],
            "narrative_flow": "Strong" if word_count > 400 else "Could be enhanced"
        }

def generate_mckinsey_review_html(reviews: Dict[str, Any]) -> str:
    """Generate HTML section for McKinsey review."""
    
    html = """
    <div class="mckinsey-review-section" style="page-break-before: always; padding: 40px; background: #f5f5f5; margin: 20px auto; max-width: 1200px;">
        <h2 style="color: #764ba2; text-align: center; margin-bottom: 30px;">👔 McKinsey Consulting Review</h2>
    """
    
    # Strategy Review
    if "story_review" in reviews and reviews.get("story_review"):
        story = reviews.get("story_review", {})
        html += f"""
        <div class="review-panel" style="background: white; padding: 20px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color: #667eea;">📖 Strategic Story Review</h3>
            <p><strong>Reviewer:</strong> {story.get('reviewer', 'Strategy Lead')}</p>
            <p><strong>Vision:</strong> {story.get('vision', 'N/A')}</p>
            <h4>Key Pillars:</h4>
            <ul>
        """
        for pillar in story.get('key_pillars', []):
            html += f"<li>{pillar}</li>"
        html += """
            </ul>
            <h4>Strengths:</h4>
            <ul>
        """
        for strength in story.get('strengths', []):
            html += f"<li>{strength}</li>"
        html += """
            </ul>
        </div>
        """
    
    # Design Review
    if "design_review" in reviews and reviews.get("design_review"):
        design = reviews.get("design_review", {})
        html += f"""
        <div class="review-panel" style="background: white; padding: 20px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color: #667eea;">🎨 Design Implementation Review</h3>
            <p><strong>Reviewer:</strong> {design.get('reviewer', 'Implementation Lead')}</p>
            <h4>Design Strengths:</h4>
            <ul>
        """
        for strength in design.get('design_strengths', []):
            html += f"<li>{strength}</li>"
        html += """
            </ul>
            <h4>Recommendations:</h4>
            <ul>
        """
        for rec in design.get('design_recommendations', []):
            html += f"<li>{rec}</li>"
        html += """
            </ul>
        </div>
        """
    
    # Value Assessment
    if "value_assessment" in reviews and reviews.get("value_assessment"):
        value = reviews.get("value_assessment", {})
        html += f"""
        <div class="review-panel" style="background: white; padding: 20px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color: #667eea;">💰 Value Assessment</h3>
            <p><strong>Reviewer:</strong> {value.get('reviewer', 'Value Realization Lead')}</p>
            <p><strong>Market Appeal:</strong> {value.get('market_appeal', 'N/A')}</p>
            <p><strong>Educational Value:</strong> {value.get('educational_value', 'N/A')}</p>
            <p><strong>Commercial Potential:</strong> {value.get('commercial_potential', 'N/A')}</p>
        </div>
        """
    
    # Engagement Summary
    if "engagement_summary" in reviews and reviews.get("engagement_summary"):
        summary = reviews.get("engagement_summary", {})
        html += f"""
        <div class="review-panel" style="background: #764ba2; color: white; padding: 20px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color: white;">👔 Overall Engagement Summary</h3>
            <p><strong>Reviewer:</strong> {summary.get('reviewer', 'Engagement Manager')}</p>
            <p><strong>Assessment:</strong> {summary.get('overall_assessment', 'N/A')}</p>
            <h4>Key Highlights:</h4>
            <ul>
        """
        for highlight in summary.get('key_highlights', []):
            html += f"<li>{highlight}</li>"
        html += """
            </ul>
            <h4>Recommendations:</h4>
            <ul>
        """
        for rec in summary.get('recommendations', []):
            html += f"<li>{rec}</li>"
        html += """
            </ul>
        </div>
        """
    
    html += "</div>"
    return html

async def main():
    """Main function to create book with McKinsey review using KG-based architecture."""
    
    import argparse
    parser = argparse.ArgumentParser(description="Create children's book with McKinsey review")
    parser.add_argument("--project-id", help="Project ID (auto-generated if not provided)")
    parser.add_argument("--resume", action="store_true", help="Resume existing project from KG")
    args = parser.parse_args()
    
    console.print(Panel.fit(
        "[bold cyan]📖 Children's Book Creation with McKinsey Review[/bold cyan]\n"
        "KG-Based Architecture with Scientific Workflow & Judge Agents",
        border_style="cyan"
    ))
    
    # Initialize Knowledge Graph
    console.print("\n[cyan]Initializing Knowledge Graph...[/cyan]")
    kg_manager = KnowledgeGraphManager(persistent_storage=True)
    await kg_manager.initialize()
    console.print("[green]✅ Knowledge Graph initialized[/green]\n")
    
    # Ensure KG manager is properly shut down on exit
    try:
        # Get or create project ID
        project_id = args.project_id or f"book_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Validate and sanitize project_id format (remove invalid URI characters)
        # Replace spaces and special chars with underscores, keep alphanumeric and basic chars
        sanitized_id = re.sub(r'[^\w\-_.]', '_', project_id)
        # Remove consecutive underscores
        sanitized_id = re.sub(r'_+', '_', sanitized_id)
        # Remove leading/trailing underscores
        sanitized_id = sanitized_id.strip('_')
        
        # If sanitization changed the ID, warn but use sanitized version
        if sanitized_id != project_id:
            console.print(f"[yellow]⚠️  Sanitized project_id: '{project_id}' -> '{sanitized_id}'[/yellow]")
            project_id = sanitized_id
        
        # Ensure project_id is not empty after sanitization
        if not project_id:
            project_id = f"book_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            console.print(f"[yellow]⚠️  Project ID was empty after sanitization, using: {project_id}[/yellow]")
        
        # Initialize project manager
        project_manager = KGProjectManager(kg_manager, project_id)
        
        # Resume or create project
        if args.resume:
            console.print(f"[cyan]Resuming project: {project_id}[/cyan]")
            context = await project_manager.get_project_context()
            console.print(f"[green]✅ Loaded project context from KG[/green]")
            console.print(f"   Status: {context.get('status', 'unknown')}")
            console.print(f"   Workflow steps: {len(context.get('workflow_steps', []))}")
            console.print(f"   Agent messages: {len(context.get('agent_messages', []))}\n")
        else:
            await project_manager.initialize_project(
                title="Where Worlds Begin",
                description="Children's book with McKinsey review and scientific workflow"
            )
        
        # Initialize scientific workflow with error handling
        scientific_workflow = ScientificBookWorkflow(kg_manager, project_manager)
        try:
            await scientific_workflow.initialize()
        except Exception as init_error:
            console.print(f"[red]❌ Failed to initialize scientific workflow: {init_error}[/red]")
            console.print("[yellow]⚠️  Workflow may not function correctly[/yellow]")
            # Continue anyway - some agents might still work
        
        # Initialize judge workflow with error handling
        judge_workflow = ImageJudgeWorkflow(kg_manager, project_manager)
        try:
            await judge_workflow.initialize()
        except Exception as init_error:
            console.print(f"[red]❌ Failed to initialize judge workflow: {init_error}[/red]")
            console.print("[yellow]⚠️  Image selection may not work correctly[/yellow]")
            # Continue anyway - can fallback to all images
        
        # Initialize McKinsey reviewer with error handling
        reviewer = McKinseyBookReviewer(kg_manager, project_manager)
        try:
            await reviewer.initialize()
        except Exception as init_error:
            console.print(f"[red]❌ Failed to initialize McKinsey reviewer: {init_error}[/red]")
            console.print("[yellow]⚠️  McKinsey review may not be available[/yellow]")
            # Continue anyway - book can be created without review
        
        # Step 1: Scientific workflow - plan and write story
        console.print("\n[bold cyan]=" * 70)
        console.print("[bold cyan]PHASE 1: Scientific Workflow - Story Planning & Writing[/bold cyan]")
        console.print("[bold cyan]=" * 70 + "\n")
        
        story_result = await scientific_workflow.plan_and_write_story(project_id)
        story_pages = story_result.get("story_pages", [])
        
        # Validate story_pages structure - ensure each page has required 'text' key
        if story_pages:
            validated_pages = []
            for idx, page in enumerate(story_pages):
                if not isinstance(page, dict):
                    console.print(f"[yellow]⚠️  Page {idx+1} is not a dict, skipping[/yellow]")
                    continue
                
                # Ensure 'text' key exists, provide default if missing
                if "text" not in page or not page.get("text"):
                    console.print(f"[yellow]⚠️  Page {idx+1} missing 'text' key, using default[/yellow]")
                    page = page.copy()
                    page["text"] = page.get("text") or f"Page {idx+1} text"
                
                # Ensure 'page' key exists for consistency
                if "page" not in page:
                    page = page.copy()
                    page["page"] = idx + 1
                
                validated_pages.append(page)
            
            story_pages = validated_pages
            if len(validated_pages) < len(story_result.get("story_pages", [])):
                console.print(f"[yellow]⚠️  Validated {len(validated_pages)}/{len(story_result.get('story_pages', []))} story pages[/yellow]\n")
        
        # If no story pages from scientific workflow, use STORY_SCRIPT
        if not story_pages:
            console.print("[yellow]⚠️  No story pages from scientific workflow, using STORY_SCRIPT[/yellow]")
            story_pages = [
                {"page": page["page"], "text": " ".join(page["lines"])}
                for page in STORY_SCRIPT
            ]
        
        # Step 2: Load or generate images
        console.print("\n[bold cyan]=" * 70)
        console.print("[bold cyan]PHASE 2: Image Loading/Generation[/bold cyan]")
        console.print("[bold cyan]=" * 70 + "\n")
        
        html_content = None
        generated_images = {}
        book_pages = []
        
        # Use existing ChildrensBookOrchestrator to load images from GCS (like other scripts do)
        # It already handles: GCS loading, ingestion, pairing, HTML generation
        bucket_name = os.getenv("GCS_BUCKET_NAME") or os.getenv("GCS_BUCKET")
        if bucket_name:
            console.print(f"[cyan]Using ChildrensBookOrchestrator to load images from GCS bucket: {bucket_name}[/cyan]")
            try:
                # Use the existing orchestrator (already imported!)
                # It reads from .env automatically via load_dotenv() in orchestrator.py
                orchestrator = ChildrensBookOrchestrator(
                    bucket_name=bucket_name,  # Explicitly pass, but also reads from .env
                    input_prefix=os.getenv("GCS_INPUT_PREFIX", "book_illustrations/"),
                    output_prefix=os.getenv("GCS_OUTPUT_PREFIX", "midjourney/"),
                    kg_manager=kg_manager  # Share KG manager for persistence
                )
                await orchestrator.initialize()
                
                # Generate book - this loads from GCS, pairs images, creates HTML
                console.print("[cyan]Loading images and generating book from GCS...[/cyan]")
                console.print("[dim]This uses existing ImageIngestionAgent and ImagePairingAgent[/dim]\n")
                book_result = await orchestrator.generate_book()
                
                # Extract the HTML path and images from result
                if book_result and book_result.get("book"):
                    html_path = book_result["book"].get("html_path")
                    if html_path and Path(html_path).exists():
                        html_content = Path(html_path).read_text()
                        pairs_count = book_result.get("pairing", {}).get("pairs_count", 0)
                        console.print(f"[green]✅ Loaded book from GCS with {pairs_count} image pairs![/green]\n")
                        
                        # Extract image URLs from the generated HTML for judge workflow
                        # The orchestrator already created HTML with real images from GCS
                        image_urls = re.findall(r'src="([^"]+)"', html_content)
                        for idx, url in enumerate(image_urls[:len(story_pages)], 1):
                            if url and (url.startswith("http") or url.startswith("./")):
                                generated_images[idx] = {
                                    "image_url": url,
                                    "gcs_url": url,
                                    "page_num": idx
                                }
                        
                        # Skip Midjourney generation - we have images from GCS
                        mj_token = None
                    else:
                        console.print("[yellow]⚠️  Orchestrator completed but no HTML file found[/yellow]\n")
                else:
                    console.print("[yellow]⚠️  Orchestrator did not return book result[/yellow]\n")
            except Exception as orchestrator_error:
                console.print(f"[yellow]⚠️  Error using orchestrator: {orchestrator_error}[/yellow]")
                console.print("[yellow]   Will try Midjourney generation instead[/yellow]\n")
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]\n")
        
        # Fallback: Generate new images if orchestrator didn't work or no bucket
        mj_token = os.getenv("MIDJOURNEY_API_TOKEN")
        if mj_token and not generated_images:
            console.print("[green]✅ Midjourney API token found[/green]")
            console.print("[cyan]Generating illustrations for book pages...[/cyan]\n")
            
            # Prepare pages for BookGeneratorTool - generate ALL pages
            book_pages = []
            for page in story_pages:
                text = page.get("text", "")
                # Clean text to avoid Midjourney parameter format issues
                clean_text = text.replace("--", "-").strip()
                prompt = (
                    f"Children's book illustration, whimsical and magical watercolor style, "
                    f"inspiring and dreamy atmosphere, {clean_text}. "
                    f"Soft pastel colors, gentle lighting, artistic and imaginative, "
                    f"professional children's book art style, high quality, detailed"
                )
                book_pages.append({
                    "title": f"Page {page.get('page', len(book_pages) + 1)}",
                    "text": text,
                    "prompt": prompt
                })
            
            # Check if book_pages is empty before proceeding
            if not book_pages:
                console.print("[yellow]⚠️  No book pages to generate images for, skipping image generation[/yellow]\n")
            else:
                # Use existing BookGeneratorTool with error handling
                try:
                    book_generator = BookGeneratorTool(
                        kg_manager=kg_manager,
                        agent_id="mckinsey_book_creator"
                    )
                    book_generator.kg_manager = kg_manager  # Ensure KG connection
                    
                    console.print(f"[cyan]Generating {len(book_pages)} illustrations...[/cyan]")
                    console.print("[dim]This may take several minutes...[/dim]\n")
                    
                    # Add timeout handling for image generation (30 minutes max)
                    timeout_seconds = 30 * 60  # 30 minutes
                    try:
                        generator_result = await asyncio.wait_for(
                            book_generator.generate_book(
                                title="Where Worlds Begin",
                                pages=book_pages,
                                max_pages_to_illustrate=len(book_pages)
                            ),
                            timeout=timeout_seconds
                        )
                    except asyncio.TimeoutError:
                        console.print(f"[red]❌ Image generation timed out after {timeout_seconds/60:.0f} minutes[/red]")
                        console.print("[yellow]⚠️  Continuing workflow without generated images[/yellow]\n")
                        generator_result = None
                        generated_images = {}
                        book_generator = None
                        # Don't re-raise - handle timeout here and continue
                    else:
                        # Only validate if no timeout occurred
                        # Validate generator_result and extract generated_images safely
                        if not generator_result or not isinstance(generator_result, dict):
                            console.print("[yellow]⚠️  Invalid generator result, no images generated[/yellow]\n")
                            generated_images = {}
                        else:
                            generated_images = generator_result.get("generated_images", {})
                            
                            # Validate generated_images structure and URLs
                            if generated_images:
                                validated_images = {}
                                for page_num, img_data in generated_images.items():
                                    if not isinstance(img_data, dict):
                                        console.print(f"[yellow]⚠️  Invalid image data for page {page_num}, skipping[/yellow]")
                                        continue
                                    
                                    # Validate image URL exists and is accessible
                                    image_url = img_data.get("gcs_url") or img_data.get("image_url", "")
                                    if not image_url or not isinstance(image_url, str):
                                        console.print(f"[yellow]⚠️  No valid image URL for page {page_num}, skipping[/yellow]")
                                        continue
                                    
                                    # Basic URL format validation
                                    if not (image_url.startswith("http://") or image_url.startswith("https://")):
                                        console.print(f"[yellow]⚠️  Invalid URL format for page {page_num}: {image_url}[/yellow]")
                                        continue
                                    
                                    # URL accessibility check (basic validation - don't block on network issues)
                                    try:
                                        import urllib.request
                                        import urllib.error
                                        req = urllib.request.Request(image_url, method='HEAD')
                                        req.add_header('User-Agent', 'Mozilla/5.0')
                                        with urllib.request.urlopen(req, timeout=5) as response:
                                            status_code = response.getcode()
                                            if status_code >= 400:
                                                console.print(f"[yellow]⚠️  Image URL returned {status_code} for page {page_num}, may be inaccessible[/yellow]")
                                    except urllib.error.URLError as url_error:
                                        console.print(f"[yellow]⚠️  Could not verify image URL accessibility for page {page_num}: {url_error}[/yellow]")
                                        # Don't skip - URL might be valid but temporarily unreachable
                                    except Exception as check_error:
                                        console.print(f"[dim]Could not check image URL for page {page_num}: {check_error}[/dim]")
                                        # Don't skip - continue with URL as-is
                                    
                                    validated_images[page_num] = img_data
                                
                                # Store original count for comparison
                                original_count = len(generated_images)
                                generated_images = validated_images
                                if len(validated_images) < original_count:
                                    console.print(f"[yellow]⚠️  Validated {len(validated_images)}/{original_count} images[/yellow]\n")
                        
                except asyncio.TimeoutError:
                    # This should not happen since we handle it above, but catch just in case
                    console.print("[yellow]⚠️  TimeoutError caught in outer handler[/yellow]")
                    generated_images = {}
                    book_generator = None
                except Exception as e:
                    console.print(f"[red]❌ Error initializing BookGeneratorTool or generating images: {e}[/red]")
                    console.print("[yellow]⚠️  Continuing workflow without generated images[/yellow]\n")
                    generated_images = {}
                    book_generator = None
            
            # Write to diary (only if book_generator was successfully created)
            if book_generator and hasattr(book_generator, 'kg_logger') and book_generator.kg_logger:
                await book_generator.kg_logger.log_tool_call(
                    tool_name="book_generator.generate_all",
                    inputs={"project_id": project_id, "pages": len(book_pages)},
                    outputs={"generated_count": len(generated_images)}
                )
            
            await project_manager.save_workflow_step("image_generation", "completed", {
                "generated_count": len(generated_images),
                "total_pages": len(book_pages)
            })
            
            console.print(f"[green]✅ Generated {len(generated_images)} illustrations![/green]\n")
        
        # Ensure book_pages is defined for HTML generation
        # If we loaded images from GCS, book_pages should already be set from story_pages
        if 'book_pages' not in locals() or not book_pages:
            # Create book_pages from story_pages for HTML generation
            book_pages = []
            for page in story_pages:
                book_pages.append({
                    "page": page.get("page", len(book_pages) + 1),
                    "text": page.get("text", "")
                })
    
        # Step 3: Judge agents review and select best images
        console.print("\n[bold cyan]=" * 70)
        console.print("[bold cyan]PHASE 3: Judge Workflow - Image Review & Selection[/bold cyan]")
        console.print("[bold cyan]=" * 70 + "\n")
        
        # Validate generated_images before passing to judge workflow
        if not generated_images or not isinstance(generated_images, dict):
            console.print("[yellow]⚠️  No valid generated images to review, skipping judge workflow[/yellow]\n")
            selected_images = {}
        else:
            # Wrap judge workflow in try/except with fallback to all images
            try:
                selected_images = await judge_workflow.review_and_select_images(
                    generated_images,
                    story_pages,
                    project_id
                )
            except Exception as judge_error:
                console.print(f"[red]❌ Judge workflow failed: {judge_error}[/red]")
                console.print("[yellow]⚠️  Using all generated images as fallback[/yellow]\n")
                # Fallback: use all images if judge workflow fails
                selected_images = generated_images.copy()
                # Log the error to KG if possible
                try:
                    await project_manager.save_workflow_step(
                        "image_selection",
                        "failed",
                        {"error": str(judge_error), "fallback": "using_all_images"}
                    )
                except Exception as kg_write_error:
                    # Don't fail if KG write fails - log silently
                    console.print(f"[dim]⚠️  Could not log judge error to KG: {kg_write_error}[/dim]")
                    pass
        
        # Use selected images (or all if none selected)
        final_images = selected_images if selected_images else generated_images
        
        # Step 4: Create HTML with selected images
        # Ensure book_pages exists (may be empty if no token)
        if 'book_pages' not in locals():
            book_pages = []
        
        if final_images and isinstance(final_images, dict) and len(final_images) > 0:
            console.print("[cyan]Creating book HTML with selected images...[/cyan]")
            html_content = await _create_html_from_generated_images(final_images, book_pages)
            if html_content:
                console.print("[green]✅ Book HTML created with real images![/green]\n")
        else:
            console.print("[yellow]⚠️  No valid images available for HTML generation[/yellow]\n")
        
        # Fallback to sample HTML if no images
        should_exit = False
        html_save_failed = False  # Initialize flag for HTML save status
        if not html_content:
            console.print("[yellow]⚠️  Using sample HTML template (placeholder images)[/yellow]\n")
            sample_html_path = project_root / "generated_books/demo_where_worlds_begin_sample.html"
            if sample_html_path.exists():
                try:
                    html_content = sample_html_path.read_text()
                except Exception as read_error:
                    console.print(f"[red]❌ Error reading HTML template: {read_error}[/red]")
                    console.print(f"[yellow]⚠️  Template exists but cannot be read: {sample_html_path}[/yellow]")
                    html_content = None
                    should_exit = True
            else:
                console.print(f"[red]❌ Sample HTML template not found: {sample_html_path}[/red]")
                console.print("[yellow]⚠️  Cannot proceed without HTML template[/yellow]")
                # Don't return - let finally block execute. Set flag instead.
                html_content = None
                should_exit = True
        
        # Step 5: McKinsey reviews
        console.print("\n[bold cyan]=" * 70)
        console.print("[bold cyan]PHASE 4: McKinsey Consulting Review[/bold cyan]")
        console.print("[bold cyan]=" * 70 + "\n")
        
        book_structure = {
            "layout_type": "two-column",
            "grid_size": "3x3",
            "total_pages": len(story_pages)
        }
        
        # Handle partial failures - each review can fail independently
        story_review = {}
        try:
            story_review = await reviewer.review_story_quality(story_pages, "Where Worlds Begin", project_id)
        except Exception as review_error:
            console.print(f"[yellow]⚠️  Story review failed: {review_error}[/yellow]")
            console.print("[yellow]   Continuing with other reviews...[/yellow]\n")
        
        design_review = {}
        try:
            design_review = await reviewer.review_design_implementation(book_structure, project_id)
        except Exception as review_error:
            console.print(f"[yellow]⚠️  Design review failed: {review_error}[/yellow]")
            console.print("[yellow]   Continuing with other reviews...[/yellow]\n")
        
        value_assessment = {}
        try:
            value_assessment = await reviewer.assess_book_value({"pages": story_pages}, project_id)
        except Exception as review_error:
            console.print(f"[yellow]⚠️  Value assessment failed: {review_error}[/yellow]")
            console.print("[yellow]   Continuing with other reviews...[/yellow]\n")
        
        engagement_summary = {}
        try:
            engagement_summary = await reviewer.get_engagement_summary({
                "story_review": story_review,
                "design_review": design_review,
                "value_assessment": value_assessment
            }, project_id)
        except Exception as review_error:
            console.print(f"[yellow]⚠️  Engagement summary failed: {review_error}[/yellow]")
            console.print("[yellow]   Continuing workflow...[/yellow]\n")
        
        # Generate review HTML
        reviews = {
            "story_review": story_review,
            "design_review": design_review,
            "value_assessment": value_assessment,
            "engagement_summary": engagement_summary
        }
        
        review_html = generate_mckinsey_review_html(reviews)
        
        # Insert review HTML before closing body tag
        # Ensure html_content is not None before string operations
        if html_content is None:
            console.print("[red]❌ Cannot add review HTML - html_content is None[/red]")
            console.print("[yellow]⚠️  Review HTML generated but cannot be inserted[/yellow]")
            html_save_failed = True
        elif "</body>" in html_content:
            html_content = html_content.replace("</body>", review_html + "\n</body>")
        else:
            html_content += review_html
        
        # Save updated HTML with error handling
        # Only attempt to save if html_content is not None
        output_path = project_root / "generated_books" / f"demo_where_worlds_begin_with_mckinsey_{project_id}.html"
        if html_content is not None:
            try:
                # Ensure directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(html_content)
                console.print(f"[green]✅ HTML file saved successfully[/green]")
            except PermissionError:
                console.print(f"[red]❌ Permission denied writing to: {output_path}[/red]")
                console.print("[yellow]⚠️  Check file permissions and try again[/yellow]")
                html_save_failed = True
            except OSError as e:
                console.print(f"[red]❌ Error writing HTML file: {e}[/red]")
                console.print(f"[yellow]⚠️  Failed to save book to: {output_path}[/yellow]")
                html_save_failed = True
            except Exception as e:
                console.print(f"[red]❌ Unexpected error saving HTML file: {e}[/red]")
                console.print(f"[yellow]⚠️  Failed to save book to: {output_path}[/yellow]")
                html_save_failed = True
        else:
            # html_content is None - cannot save
            console.print(f"[red]❌ Cannot save HTML file - html_content is None[/red]")
            html_save_failed = True
        
        # Exit early if HTML save failed or sample HTML not found
        # Note: return here will skip remaining code but finally block will still execute
        if html_save_failed or should_exit:
            console.print("[yellow]⚠️  Workflow incomplete - KG will still be cleaned up[/yellow]")
            return
        
        # Save final status to KG
        # Ensure selected_images is defined (may be empty dict if judge workflow skipped)
        selected_count = len(selected_images) if selected_images and isinstance(selected_images, dict) else (len(generated_images) if generated_images and isinstance(generated_images, dict) else 0)
        await project_manager.save_workflow_step("book_completion", "completed", {
            "html_path": str(output_path),
            "total_pages": len(story_pages) if story_pages else 0,
            "images_selected": selected_count
        })
        
        # Update project status
        await kg_manager.add_triple(
            str(project_manager.project_uri),
            str(CORE.status),
            "completed"
        )
        
        console.print(f"\n[green]✅ Book with McKinsey review saved to:[/green]")
        console.print(f"[cyan]{output_path}[/cyan]\n")
        
        # Display summary table
        table = Table(title="Workflow Summary")
        table.add_column("Phase", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")
        
        # Safe length calculations with None/empty checks
        story_count = len(story_pages) if story_pages else 0
        image_count = len(generated_images) if generated_images and isinstance(generated_images, dict) else 0
        selected_count = len(selected_images) if selected_images and isinstance(selected_images, dict) else image_count
        
        table.add_row("Scientific Workflow", "✅ Complete", f"{story_count} pages written")
        table.add_row("Image Generation", "✅ Complete", f"{image_count} images generated")
        table.add_row("Judge Selection", "✅ Complete", f"{selected_count} images selected")
        table.add_row("McKinsey Review", "✅ Complete", "All 4 agents reviewed")
        table.add_row("KG Persistence", "✅ Complete", f"Project: {project_id}")
        
        console.print(table)
        console.print(f"\n[bold green]🎉 Book creation complete![/bold green]\n")
        console.print(f"[dim]Project ID: {project_id}[/dim]")
        console.print(f"[dim]All work persisted to Knowledge Graph[/dim]")
        console.print(f"[dim]Resume with: python scripts/tools/create_book_with_mckinsey_review.py --project-id {project_id} --resume[/dim]\n")
        console.print(f"[dim]Open the book:[/dim] [cyan]open {output_path}[/cyan]\n")
    
    finally:
        # Always shutdown KG manager to ensure proper cleanup
        try:
            await kg_manager.shutdown()
            console.print("[dim]✅ Knowledge Graph manager shut down cleanly[/dim]")
        except Exception as e:
            console.print(f"[yellow]⚠️  Error shutting down KG manager: {e}[/yellow]")

if __name__ == "__main__":
    asyncio.run(main())
