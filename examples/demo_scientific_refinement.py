"""
Example script: demo_scientific_refinement

This script demonstrates the full scientific reasoning workflow for prompt refinement.
It initializes a suite of specialized agents, orchestrated by a PlannerAgent, to
analyze, synthesize, critique, and judge a prompt based on text and image inputs.

Run from project root:
    python -m examples.demo_scientific_refinement

Or:
    PYTHONPATH=. python examples/demo_scientific_refinement.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from dotenv import load_dotenv
load_dotenv(dotenv_path=project_root / '.env')

from agents.core.agent_registry import AgentRegistry
from agents.core.workflow_manager import WorkflowManager
from agents.domain.planner_agent import PlannerAgent
from agents.domain.logo_analysis_agent import LogoAnalysisAgent
from agents.domain.aesthetics_agent import AestheticsAgent
from agents.domain.color_palette_agent import ColorPaletteAgent
from agents.domain.composition_agent import CompositionAgent
from agents.domain.prompt_synthesis_agent import PromptSynthesisAgent
from agents.domain.prompt_critic_agent import PromptCriticAgent
from agents.domain.prompt_judge_agent import PromptJudgeAgent
from agents.core.base_agent import AgentMessage

# Ensure you have an OPENAI_API_KEY set in your .env file

async def run_scientific_refinement_demo():
    """
    Demonstrates the full scientific reasoning workflow for prompt refinement.
    """
    print("--- Scientific Reasoning Prompt Refinement Demo ---")

    # 1. Initialize the core components
    agent_registry = AgentRegistry(disable_auto_discovery=True)
    await agent_registry.initialize()
    workflow_manager = WorkflowManager(agent_registry)
    await workflow_manager.initialize()

    # 2. Register all the necessary agents
    print("\n[Step 1: Registering Agents]")
    agents_to_register = [
        PlannerAgent("planner", agent_registry),
        LogoAnalysisAgent("logo_analyzer"),
        AestheticsAgent("aesthetics_analyzer"),
        ColorPaletteAgent("color_palette_analyzer"),
        CompositionAgent("composition_analyzer"),
        PromptSynthesisAgent("synthesis_agent"),
        PromptCriticAgent("critic_agent"),
        PromptJudgeAgent("judge_agent")
    ]
    for agent in agents_to_register:
        await agent_registry.register_agent(agent)
        print(f"- Registered: {agent.agent_id}")

    # 3. Define the test case
    original_prompt = "A vintage-inspired baseball trading card for player photo taking up the top half, 'MVP' heading across the top, team name at bottom. Modern 2 tone. CREATE A TRADITIONAL 1970s trading card."
    image_urls = [
        "https://storage.googleapis.com/bahroo_public/522c-4eb5-ad0f-d5b8fa601c.jpeg"
    ]
    
    print(f"\n[Step 2: Starting workflow with Original Prompt]")
    print(f"Prompt: '{original_prompt}'")
    print(f"Image URL: {image_urls[0]}")

    # 4. Get the planner agent to start the workflow
    planner_agent = await agent_registry.get_agent("planner")
    if not planner_agent:
        print("Error: Planner agent not found.")
        return

    # The PlannerAgent's process method will create and execute the entire workflow
    initial_message = AgentMessage(
        sender_id="system_test",
        recipient_id="planner",
        content={"prompt": original_prompt, "image_urls": image_urls},
        message_type="request"
    )
    
    print("\n[Step 3: Executing Workflow...]")
    final_result_message = await planner_agent.process_message(initial_message)
    
    # 5. Print the final result
    print("\n[Step 4: Workflow Complete]")
    final_prompt = final_result_message.content.get("final_prompt", "No final prompt was returned.")
    judgment = final_result_message.content.get("judgment", "No judgment was made.")
    
    print("\n--- Final Result ---")
    print(f"Judgment: {judgment}")
    print(f"Final Prompt:\n{final_prompt}")
    print("--------------------")


if __name__ == "__main__":
    # Ensure you have an OPENAI_API_KEY in your .env file for this to work
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set.")
        print("Please create a .env file in the root directory and add your key.")
    else:
        asyncio.run(run_scientific_refinement_demo())
