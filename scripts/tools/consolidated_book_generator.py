#!/usr/bin/env python3
"""
CONSOLIDATED BOOK GENERATOR - UNIFIED SYSTEM
🎯 Single entry point for ALL book generation capabilities
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum
from dotenv import load_dotenv

# Import all existing systems
from universal_book_generator import UniversalBookGenerator
from one_click_book_system import OneClickBookSystem
from generate_complete_book_now import CompleteBookGenerator
from semant.agent_tools.midjourney.tools.book_generator_tool import BookGeneratorTool
from semant.agent_tools.midjourney import REGISTRY

load_dotenv()

class BookGenerationMode(Enum):
    """Available book generation modes."""
    QUICK = "quick"           # Simple template editing
    UNIVERSAL = "universal"   # Any story with AI prompts
    ONE_CLICK = "one_click"   # Pre-built Quacky story
    COMPLETE = "complete"     # Full 12-page Quacky with KG
    AGENT_TOOL = "agent_tool" # Programmatic agent use

class ConsolidatedBookGenerator:
    """
    🎯 UNIFIED BOOK GENERATION SYSTEM

    This consolidates ALL book generation capabilities into one system:

    1. QUICK Mode: Edit template and run (easiest)
    2. UNIVERSAL Mode: Any story with AI-generated prompts
    3. ONE_CLICK Mode: Pre-built Quacky story with fallbacks
    4. COMPLETE Mode: Full 12-page story with Knowledge Graph
    5. AGENT_TOOL Mode: For programmatic use by AI agents

    All modes support:
    - Midjourney illustration generation
    - Knowledge Graph storage
    - Multiple output formats (HTML, Markdown)
    - Fallback systems for reliability
    - State persistence and resumability
    """

    def __init__(self, mode: str = "quick"):
        self.mode = BookGenerationMode(mode)
        self.output_dir = Path(f"consolidated_books/{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print("🎯 CONSOLIDATED BOOK GENERATOR INITIALIZED")
        print(f"📋 Mode: {self.mode.value.upper()}")
        print(f"📁 Output: {self.output_dir}")

        # Initialize tools based on mode
        self._initialize_tools()

    def _initialize_tools(self):
        """Initialize the appropriate tools for the selected mode."""
        try:
            if self.mode in [BookGenerationMode.AGENT_TOOL]:
                # Initialize agent tool
                self.agent_tool = BookGeneratorTool()
                print("✅ Agent tool initialized")
            else:
                # Import basic generators
                self.universal_generator = UniversalBookGenerator()
                print("✅ Universal generator available")

        except Exception as e:
            print(f"⚠️ Some tools may not be available: {e}")

    async def generate_book(self, **kwargs) -> Dict[str, Any]:
        """
        Generate a book using the selected mode.

        Args:
            **kwargs: Mode-specific parameters

        Returns:
            Dict with results and metadata
        """

        print(f"\n🚀 STARTING BOOK GENERATION ({self.mode.value})")
        print("=" * 60)

        try:
            if self.mode == BookGenerationMode.QUICK:
                return await self._quick_mode(**kwargs)
            elif self.mode == BookGenerationMode.UNIVERSAL:
                return await self._universal_mode(**kwargs)
            elif self.mode == BookGenerationMode.ONE_CLICK:
                return await self._one_click_mode(**kwargs)
            elif self.mode == BookGenerationMode.COMPLETE:
                return await self._complete_mode(**kwargs)
            elif self.mode == BookGenerationMode.AGENT_TOOL:
                return await self._agent_tool_mode(**kwargs)
            else:
                raise ValueError(f"Unknown mode: {self.mode}")

        except Exception as e:
            print(f"❌ Generation failed: {e}")
            return self._create_error_result(e)

    async def _quick_mode(self, title: str = None, pages: List[Dict] = None) -> Dict[str, Any]:
        """Quick mode - edit template and run."""
        if not title or not pages:
            # Use default example
            title = "The Magic Pizza Adventure"
            pages = [
                {
                    "text": "Tommy found a glowing pizza slice under his bed!",
                    "art_direction": "surprised boy finding magical glowing pizza"
                },
                {
                    "text": "When he took a bite, he could fly like a superhero!",
                    "art_direction": "boy flying through clouds with pizza slice"
                },
                {
                    "text": "He shared the magic pizza with all his friends at school.",
                    "art_direction": "kids sharing pizza and floating in playground"
                },
                {
                    "text": "Together they flew around the world helping people!",
                    "art_direction": "group of flying children over world map"
                },
                {
                    "text": "Best lunch ever! said Tommy as they landed back home.",
                    "art_direction": "happy kids landing at school with pizza"
                }
            ]

        # Create the book using the universal generator
        # For the consolidated system, we'll use a simpler approach
        try:
            generator = UniversalBookGenerator()
            # Set the book content
            generator.book_title = title
            generator.pages = generator._process_pages(pages)
            # Call the sync version of the method (avoiding the wrapper)
            result_path = generator._create_html_book()
            print("✅ Book created successfully!")
            print(f"📁 Output: {result_path}")
            return self._create_success_result("quick", title, len(pages))
        except Exception as e:
            print(f"⚠️ Error creating book: {e}")
            return self._create_error_result(e)

    async def _universal_mode(self, **kwargs) -> Dict[str, Any]:
        """Universal mode - any story with AI prompts."""
        # This would require interactive input or file input
        print("🔧 Universal mode requires interactive input")
        print("💡 Run: python3 universal_book_generator.py")
        return self._create_info_result("universal", "Interactive mode required")

    async def _one_click_mode(self, **kwargs) -> Dict[str, Any]:
        """One-click mode - pre-built Quacky story."""
        try:
            system = OneClickBookSystem()
            result = await system.generate_complete_book()
            return self._create_success_result("one_click", system.book_title, len(system.pages))
        except Exception as e:
            print(f"⚠️ One-click mode failed: {e}")
            return self._create_error_result(e)

    async def _complete_mode(self, **kwargs) -> Dict[str, Any]:
        """Complete mode - full Quacky story with KG."""
        try:
            generator = CompleteBookGenerator()
            await generator.run()
            return self._create_success_result("complete", generator.book_title, 12)
        except Exception as e:
            print(f"⚠️ Complete mode failed: {e}")
            return self._create_error_result(e)

    async def _agent_tool_mode(self, title: str, pages: List[Dict], **kwargs) -> Dict[str, Any]:
        """Agent tool mode - for programmatic use."""
        try:
            if not hasattr(self, 'agent_tool'):
                raise ValueError("Agent tool not available")

            result = await self.agent_tool.run(
                title=title,
                pages=pages,
                max_pages_to_illustrate=kwargs.get('max_pages', 6)
            )
            return self._create_success_result("agent_tool", title, len(pages))

        except Exception as e:
            print(f"⚠️ Agent tool mode failed: {e}")
            return self._create_error_result(e)

    def _create_success_result(self, mode: str, title: str, pages: int) -> Dict[str, Any]:
        """Create a successful result structure."""
        return {
            "status": "success",
            "mode": mode,
            "title": title,
            "pages": pages,
            "output_directory": str(self.output_dir),
            "timestamp": datetime.now().isoformat(),
            "message": f"✅ Book generated successfully using {mode} mode!"
        }

    def _create_error_result(self, error: Exception) -> Dict[str, Any]:
        """Create an error result structure."""
        return {
            "status": "error",
            "mode": self.mode.value,
            "error": str(error),
            "output_directory": str(self.output_dir),
            "timestamp": datetime.now().isoformat(),
            "message": "❌ Book generation failed"
        }

    def _create_info_result(self, mode: str, message: str) -> Dict[str, Any]:
        """Create an informational result structure."""
        return {
            "status": "info",
            "mode": mode,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

    def get_available_modes(self) -> Dict[str, str]:
        """Get description of all available modes."""
        return {
            "quick": "Edit template and run - simplest approach",
            "universal": "Any story with AI-generated prompts",
            "one_click": "Pre-built Quacky McWaddles story",
            "complete": "Full 12-page Quacky with Knowledge Graph",
            "agent_tool": "Programmatic use by AI agents"
        }

    def create_example_stories(self) -> Dict[str, Dict]:
        """Create example stories for different themes."""
        return {
            "space": {
                "title": "Luna's Space Adventure",
                "pages": [
                    {
                        "text": "Luna the astronaut bunny dreamed of visiting the stars!",
                        "art_direction": "cute bunny in a space suit"
                    },
                    {
                        "text": "She built a rocket ship from cardboard boxes and imagination.",
                        "art_direction": "bunny building colorful cardboard rocket"
                    },
                    {
                        "text": "3... 2... 1... BLAST OFF! Luna zoomed past the clouds!",
                        "art_direction": "rocket launching with bunny inside"
                    },
                    {
                        "text": "She danced on the moon and made friends with alien butterflies.",
                        "art_direction": "bunny on moon surface with glowing butterflies"
                    },
                    {
                        "text": "Luna returned home with stardust in her fur and stories to share!",
                        "art_direction": "happy bunny landing back on Earth"
                    }
                ]
            },
            "dinosaur": {
                "title": "Rex the Detective",
                "pages": [
                    {
                        "text": "Rex the dinosaur detective found mysterious footprints!",
                        "art_direction": "detective dinosaur examining footprints"
                    },
                    {
                        "text": "He followed the trail through the prehistoric jungle.",
                        "art_direction": "dinosaur walking through jungle"
                    },
                    {
                        "text": "The footprints led to a surprise birthday party!",
                        "art_direction": "dinosaur at birthday party with friends"
                    }
                ]
            },
            "robot": {
                "title": "Robbie the Robot Chef",
                "pages": [
                    {
                        "text": "Robbie the robot loved to cook but only knew how to make toast!",
                        "art_direction": "robot making toast"
                    },
                    {
                        "text": "He went to cooking school and learned to make rainbow soup!",
                        "art_direction": "robot cooking colorful soup"
                    },
                    {
                        "text": "The kids loved his bouncing spaghetti!",
                        "art_direction": "robot serving bouncing spaghetti"
                    }
                ]
            }
        }


# 🎯 MAIN INTERFACE FUNCTIONS

async def generate_book(mode: str = "quick", **kwargs) -> Dict[str, Any]:
    """
    🎯 MAIN BOOK GENERATION FUNCTION

    Args:
        mode: Generation mode (quick, universal, one_click, complete, agent_tool)
        **kwargs: Mode-specific parameters

    Examples:
        # Quick mode with custom story
        await generate_book("quick", title="My Story", pages=[{"text": "Once upon a time..."}])

        # Use pre-built example
        await generate_book("quick")  # Uses default pizza story
    """
    generator = ConsolidatedBookGenerator(mode)
    return await generator.generate_book(**kwargs)


def show_available_modes():
    """Show all available generation modes."""
    generator = ConsolidatedBookGenerator()
    modes = generator.get_available_modes()

    print("\n🎯 CONSOLIDATED BOOK GENERATOR - Available Modes")
    print("=" * 60)

    for mode, description in modes.items():
        print(f"📋 {mode.upper()}: {description}")

    print("\n💡 Examples:")
    print("  Quick mode: python3 consolidated_book_generator.py quick")
    print("  Custom story: python3 consolidated_book_generator.py quick --title 'My Book' --pages 'page1,page2'")
    print("  Space theme: python3 consolidated_book_generator.py quick --theme space")


def create_example_book(theme: str = None):
    """Create an example book with a specific theme."""
    generator = ConsolidatedBookGenerator()

    if not theme:
        print("\n🎨 Available example themes:")
        examples = generator.create_example_stories()
        for theme_name in examples.keys():
            print(f"  • {theme_name}")
        print("\n💡 Usage: python3 consolidated_book_generator.py example --theme space")
        return

    examples = generator.create_example_stories()
    if theme not in examples:
        print(f"❌ Unknown theme: {theme}")
        print("Available themes: space, dinosaur, robot")
        return

    story = examples[theme]
    print(f"\n🚀 Creating example book: {story['title']}")
    # Note: This will be called from main() which already has an event loop
    # We'll handle this in the main function
    print("⚠️ Example mode requires running from main() - use: python3 consolidated_book_generator.py example --theme space")


# 🎯 COMMAND LINE INTERFACE

def create_workflow_from_text(text_file: str, user_email: str, workflow_name: str = "Book Generation Workflow") -> Dict[str, Any]:
    """Create a comprehensive workflow for book generation."""
    try:
        from agents.domain.orchestration_workflow import OrchestrationWorkflow
        from agents.domain.planner_agent import PlannerAgent
        from agents.domain.code_review_agent import CodeReviewAgent
        from agents.core.agent_registry import AgentRegistry

        # Initialize registry and get planner
        registry = AgentRegistry(disable_auto_discovery=False)
        planner = PlannerAgent("planner", registry)

        # Initialize review agents
        review_agents = []
        try:
            review_agent = CodeReviewAgent("code_reviewer")
            review_agents.append(review_agent)
        except Exception as e:
            print(f"⚠️ Could not initialize review agent: {e}")

        # Create workflow
        workflow = OrchestrationWorkflow(planner, review_agents)

        # Create workflow from text
        result = asyncio.run(workflow.create_workflow_from_text(
            text_file, user_email, workflow_name
        ))

        return result

    except Exception as e:
        print(f"❌ Error creating workflow: {e}")
        return {"error": str(e)}

async def visualize_workflow(workflow_id: str) -> Dict[str, Any]:
    """Visualize a workflow in the Knowledge Graph."""
    try:
        from kg.models.graph_manager import KnowledgeGraphManager

        # Initialize KG manager
        kg_manager = KnowledgeGraphManager()
        await kg_manager.initialize()

        # Query workflow data
        workflow_uri = f"http://example.org/workflow/{workflow_id}"

        # Simple query to get workflow data
        query = f"""
        PREFIX ex: <http://example.org/ontology#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?predicate ?object
        WHERE {{
            <{workflow_uri}> ?predicate ?object .
        }}
        """

        results = await kg_manager.query_graph(query)

        # Get plan data
        plan_query = f"""
        PREFIX ex: <http://example.org/ontology#>

        SELECT ?plan ?step ?action ?agent ?description
        WHERE {{
            <{workflow_uri}> ex:hasPlan ?plan .
            ?step ex:belongsToPlan ?plan .
            ?step ex:action ?action .
            ?step ex:assignedAgent ?agent .
            ?step ex:description ?description .
        }}
        ORDER BY ?step
        """

        plan_results = await kg_manager.query_graph(plan_query)

        # Get step details
        step_details_query = f"""
        PREFIX ex: <http://example.org/ontology#>

        SELECT ?step ?stepNumber ?action ?agent ?description ?input ?output
        WHERE {{
            <{workflow_uri}> ex:hasPlan ?plan .
            ?step ex:belongsToPlan ?plan .
            ?step ex:stepNumber ?stepNumber .
            ?step ex:action ?action .
            ?step ex:assignedAgent ?agent .
            ?step ex:description ?description .
            OPTIONAL {{ ?step ex:input ?input . }}
            OPTIONAL {{ ?step ex:output ?output . }}
        }}
        ORDER BY ?stepNumber
        """

        step_details = await kg_manager.query_graph(step_details_query)

        # Close KG manager
        await kg_manager.shutdown()

        # Format results for display
        formatted_steps = []
        for step in step_details:
            formatted_steps.append({
                "step": step.get("step", ""),
                "step_number": step.get("stepNumber", ""),
                "action": step.get("action", ""),
                "agent": step.get("agent", ""),
                "description": step.get("description", ""),
                "input": step.get("input", "None"),
                "output": step.get("output", "None")
            })

        return {
            "workflow_id": workflow_id,
            "workflow_data": results,
            "plan_steps": plan_results,
            "step_details": formatted_steps,
            "sparql_queries": {
                "workflow": query,
                "plan": plan_query,
                "step_details": step_details_query
            },
            "status": "visualized",
            "message": f"Workflow {workflow_id} visualized successfully"
        }

    except Exception as e:
        print(f"❌ Error visualizing workflow: {e}")
        return {"error": str(e)}

def execute_workflow(workflow_id: str, user_email: str) -> Dict[str, Any]:
    """Execute a complete workflow."""
    try:
        from agents.domain.orchestration_workflow import OrchestrationWorkflow
        from agents.domain.planner_agent import PlannerAgent
        from agents.domain.code_review_agent import CodeReviewAgent
        from agents.core.agent_registry import AgentRegistry

        # Initialize registry and get planner
        registry = AgentRegistry(disable_auto_discovery=False)
        planner = PlannerAgent("planner", registry)

        # Initialize review agents
        review_agents = []
        try:
            review_agent = CodeReviewAgent("code_reviewer")
            review_agents.append(review_agent)
        except Exception as e:
            print(f"⚠️ Could not initialize review agent: {e}")

        # Create workflow
        workflow = OrchestrationWorkflow(planner, review_agents)

        # Execute workflow steps
        results = {}

        # Step 1: Send for review
        results["review"] = asyncio.run(workflow.send_plan_for_review(workflow_id, user_email))

        # Step 2: Validate execution readiness
        results["validation"] = asyncio.run(workflow.validate_execution_readiness(workflow_id))

        # Step 3: Execute (if validated)
        if results["validation"]["execution_ready"]:
            results["execution"] = asyncio.run(workflow.execute_workflow(workflow_id))
            results["analysis"] = asyncio.run(workflow.conduct_post_execution_analysis(workflow_id))

        return results

    except Exception as e:
        print(f"❌ Error executing workflow: {e}")
        return {"error": str(e)}

async def main():
    """Main command line interface."""
    if len(sys.argv) < 2:
        show_available_modes()
        return

    command = sys.argv[1]

    if command == "modes":
        show_available_modes()
    elif command == "example":
        # Handle both "example --theme space" and "example space"
        theme = None
        if len(sys.argv) > 2:
            if sys.argv[2] == "--theme":
                theme = sys.argv[3] if len(sys.argv) > 3 else None
            else:
                theme = sys.argv[2]

        if theme:
            # Get the story and run it
            generator = ConsolidatedBookGenerator()
            examples = generator.create_example_stories()
            if theme not in examples:
                print(f"❌ Unknown theme: {theme}")
                print("Available themes: space, dinosaur, robot")
                return

            story = examples[theme]
            print(f"\n🚀 Creating example book: {story['title']}")
            # Create generator and call the method directly (avoids nested asyncio.run)
            result = await generator._quick_mode(**story)
            print(f"✅ Book generation completed: {result.get('message', 'Success!')}")
        else:
            create_example_book(None)
    elif command == "workflow":
        if len(sys.argv) < 4:
            print("Usage: python3 consolidated_book_generator.py workflow <text_file> <email> [name]")
            return
        text_file = sys.argv[2]
        user_email = sys.argv[3]
        workflow_name = sys.argv[4] if len(sys.argv) > 4 else "Book Generation Workflow"

        result = asyncio.run(create_workflow_from_text(text_file, user_email, workflow_name))
        print(f"Workflow created: {result}")
    elif command == "visualize":
        if len(sys.argv) < 3:
            print("Usage: python3 consolidated_book_generator.py visualize <workflow_id>")
            return
        workflow_id = sys.argv[2]

        result = await visualize_workflow(workflow_id)
        print(f"Visualization created: {result}")
    elif command == "execute":
        if len(sys.argv) < 4:
            print("Usage: python3 consolidated_book_generator.py execute <workflow_id> <email>")
            return
        workflow_id = sys.argv[2]
        user_email = sys.argv[3]

        result = execute_workflow(workflow_id, user_email)
        print(f"Workflow execution: {result}")
    elif command == "quick":
        # Default quick mode
        await generate_book("quick")
    elif command == "one-click":
        await generate_book("one_click")
    elif command == "universal":
        await generate_book("universal")
    else:
        print(f"❌ Unknown command: {command}")
        show_available_modes()


if __name__ == "__main__":
    asyncio.run(main())
