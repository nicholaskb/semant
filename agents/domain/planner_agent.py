from agents.core.base_agent import BaseAgent, AgentMessage
from agents.core.agent_registry import AgentRegistry
import asyncio
import json
from typing import Callable, Awaitable

class PlannerAgent(BaseAgent):
    """
    An agent that orchestrates the prompt refinement workflow by calling other agents in sequence.
    """
    def __init__(self, agent_id: str, registry: AgentRegistry):
        super().__init__(agent_id)
        self.registry = registry

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        original_prompt = message.content.get("prompt", "")
        image_urls = message.content.get("image_urls", [])
        streaming_callback = message.content.get("streaming_callback")

        async def stream(text: str):
            if streaming_callback:
                await streaming_callback(text)

        try:
            await stream("Initializing refinement workflow...")
            
            # 1. Get all required agents from the registry
            logo_agent = await self.registry.get_agent("logo_analyzer")
            aesthetics_agent = await self.registry.get_agent("aesthetics_analyzer")
            color_agent = await self.registry.get_agent("color_palette_analyzer")
            composition_agent = await self.registry.get_agent("composition_analyzer")
            synthesis_agent = await self.registry.get_agent("synthesis_agent")
            critic_agent = await self.registry.get_agent("critic_agent")
            judge_agent = await self.registry.get_agent("judge_agent")

            # 2. Run Analysis Agents in parallel
            await stream("Dispatching tasks to analysis agents: Logo, Aesthetics, Color, Composition...")
            analysis_tasks = [
                logo_agent.process_message(message),
                aesthetics_agent.process_message(message),
                color_agent.process_message(message),
                composition_agent.process_message(message)
            ]
            analysis_results = await asyncio.gather(*analysis_tasks)
            await stream("Analysis complete. Received results from all analysis agents.")
            
            # 3. Synthesize the new prompt
            synthesis_content = {"original_prompt": original_prompt}
            for result in analysis_results:
                synthesis_content.update(result.content)
            
            await stream(f"Sending to synthesis agent with content:\n{json.dumps(synthesis_content, indent=2)}")
            synthesis_message = AgentMessage(sender_id=self.agent_id, recipient_id="synthesis_agent", content=synthesis_content)
            synthesis_result = await synthesis_agent.process_message(synthesis_message)
            refined_prompt = synthesis_result.content.get("refined_prompt")
            await stream(f"Received refined prompt from synthesis agent:\n'{refined_prompt}'")

            # 4. Critique the new prompt
            await stream("Sending refined prompt to critic agent for review.")
            critique_message = AgentMessage(sender_id=self.agent_id, recipient_id="critic_agent", content={"refined_prompt": refined_prompt})
            critique_result = await critic_agent.process_message(critique_message)
            critique = critique_result.content.get("critique")
            await stream(f"Received critique from critic agent:\n'{critique}'")

            # 5. Judge the final prompt
            await stream("Sending all data to judge agent for final decision.")
            judge_content = {
                "original_prompt": original_prompt,
                "refined_prompt": refined_prompt,
                "critique": critique
            }
            judge_message = AgentMessage(sender_id=self.agent_id, recipient_id="judge_agent", content=judge_content)
            judge_result = await judge_agent.process_message(judge_message)
            final_prompt = judge_result.content.get("final_prompt")
            judgment = judge_result.content.get("judgment")
            await stream(f"Received final judgment. Approved prompt:\n'{final_prompt}'")

            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"final_prompt": final_prompt, "judgment": judgment},
                message_type="response",
            )

        except Exception as e:
            self.logger.error(f"Error in planner agent workflow: {e}", exc_info=True)
            await stream(f"An error occurred: {e}")
            return self._create_error_response(message.sender_id, str(e))
