from agents.core.base_agent import BaseAgent, AgentMessage
from agents.core.agent_registry import AgentRegistry
import asyncio
import json
from typing import Callable, Awaitable

# Optional Midjourney workflow (keeps existing flows intact)
try:
    from semant.agent_tools.midjourney.workflows import imagine_then_mirror
    _MJ_AVAILABLE = True
except Exception:
    _MJ_AVAILABLE = False

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
            # Minimal, non-breaking: allow a Midjourney imagine→mirror workflow when requested
            # Usage: message.content["midjourney"] = { "prompt": str, "version": "v7", ... }
            mj_cfg = message.content.get("midjourney")
            if _MJ_AVAILABLE and isinstance(mj_cfg, dict):
                await stream("Running Midjourney imagine→mirror workflow via agent tools...")
                prompt = mj_cfg.get("prompt") or original_prompt
                version = mj_cfg.get("version", "v7")
                aspect_ratio = mj_cfg.get("aspect_ratio")
                process_mode = mj_cfg.get("process_mode")
                cref = mj_cfg.get("cref")
                cw = mj_cfg.get("cw")
                oref = mj_cfg.get("oref")
                ow = mj_cfg.get("ow")
                interval = float(mj_cfg.get("interval", 5.0))
                timeout = int(mj_cfg.get("timeout", 900))

                result = await imagine_then_mirror(
                    prompt=prompt,
                    version=version,
                    aspect_ratio=aspect_ratio,
                    process_mode=process_mode,
                    cref=cref,
                    cw=cw,
                    oref=oref,
                    ow=ow,
                    poll_interval=interval,
                    poll_timeout=timeout,
                )
                await stream("Midjourney workflow completed.")
                return AgentMessage(
                    sender_id=self.agent_id,
                    recipient_id=message.sender_id,
                    content={
                        "midjourney": result,
                        "note": "Returned by Planner via midjourney workflow",
                    },
                    message_type="response",
                )

            await stream("COMMENCING AUTHORITATIVE REFINEMENT PROTOCOL...")
            
            # 1. Get all required agents from the registry
            logo_agent = await self.registry.get_agent("logo_analyzer")
            aesthetics_agent = await self.registry.get_agent("aesthetics_analyzer")
            color_agent = await self.registry.get_agent("color_palette_analyzer")
            composition_agent = await self.registry.get_agent("composition_analyzer")
            synthesis_agent = await self.registry.get_agent("synthesis_agent")
            critic_agent = await self.registry.get_agent("critic_agent")
            judge_agent = await self.registry.get_agent("judge_agent")

            # 2. Run Analysis Agents in parallel
            await stream("DEPLOYING ELITE ANALYSIS SQUAD: Logo, Aesthetics, Color, Composition...")
            analysis_tasks = [
                logo_agent.process_message(message),
                aesthetics_agent.process_message(message),
                color_agent.process_message(message),
                composition_agent.process_message(message)
            ]
            analysis_results = await asyncio.gather(*analysis_tasks)
            await stream("ANALYSIS SQUAD REPORTS RECEIVED. All intelligence gathered successfully.")
            
            # 3. Synthesize the new prompt
            synthesis_content = {"original_prompt": original_prompt}
            for result in analysis_results:
                synthesis_content.update(result.content)
            
            await stream(f"TRANSMITTING INTELLIGENCE PACKAGE TO SYNTHESIS COMMANDER:\n{json.dumps(synthesis_content, indent=2)}")
            synthesis_message = AgentMessage(sender_id=self.agent_id, recipient_id="synthesis_agent", content=synthesis_content)
            synthesis_result = await synthesis_agent.process_message(synthesis_message)
            refined_prompt = synthesis_result.content.get("refined_prompt")
            await stream(f"I have received the AUTHORITATIVE refined prompt from synthesis:\n'{refined_prompt}'")

            # 4. Critique the new prompt
            await stream("SUBMITTING REFINED PROMPT TO THE UNCOMPROMISING CRITIC.")
            critique_message = AgentMessage(sender_id=self.agent_id, recipient_id="critic_agent", content={"refined_prompt": refined_prompt})
            critique_result = await critic_agent.process_message(critique_message)
            critique = critique_result.content.get("critique")
            await stream(f"The SUPREME CRITIC has delivered its VERDICT:\n'{critique}'")

            # 5. Judge the final prompt
            await stream("Now presenting evidence to the ULTIMATE JUDGE for FINAL VERDICT.")
            judge_content = {
                "original_prompt": original_prompt,
                "refined_prompt": refined_prompt,
                "critique": critique
            }
            judge_message = AgentMessage(sender_id=self.agent_id, recipient_id="judge_agent", content=judge_content)
            judge_result = await judge_agent.process_message(judge_message)
            final_prompt = judge_result.content.get("final_prompt")
            judgment = judge_result.content.get("judgment")
            await stream(f"THE ULTIMATE JUDGE HAS SPOKEN. The AUTHORITATIVE prompt is:\n'{final_prompt}'")

            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"final_prompt": final_prompt, "judgment": judgment, "authority": "SUPREME"},
                message_type="response",
            )

        except Exception as e:
            self.logger.error(f"Error in planner agent workflow: {e}", exc_info=True)
            await stream(f"An error occurred: {e}")
            return self._create_error_response(message.sender_id, str(e))
