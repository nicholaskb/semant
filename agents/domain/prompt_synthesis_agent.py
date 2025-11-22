from agents.core.base_agent import BaseAgent, AgentMessage
import os

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class PromptSynthesisAgent(BaseAgent):
    """
    An agent that synthesizes a refined prompt from various analyses.
    """
    def __init__(self, agent_id: str, capabilities: set):
        super().__init__(agent_id, capabilities=capabilities)
        if not OpenAI:
            raise ImportError("The 'openai' library is required to use this agent.")
        self.openai_client = OpenAI()

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        original_prompt = message.content.get("original_prompt", "")
        logo_analysis = message.content.get("logo_analysis", "")
        aesthetics_analysis = message.content.get("aesthetics_analysis", "")
        color_palette_analysis = message.content.get("color_palette_analysis", "")
        composition_analysis = message.content.get("composition_analysis", "")

        system_prompt = (
            "You are a master prompt engineer. Your task is to synthesize a new, superior Midjourney prompt "
            "from an original prompt and several expert analyses of accompanying images. Combine all the information "
            "into a single, cohesive, and descriptive paragraph. The final prompt must not exceed 5000 words. "
            "Do not generate an image; your only output should be the refined text prompt."
        )
        
        user_prompt = f"""
        Original Prompt: "{original_prompt}"

        ---Expert Analyses---
        Logo and Graphics:
        {logo_analysis}

        Aesthetics and Style:
        {aesthetics_analysis}

        Color Palette:
        {color_palette_analysis}

        Composition and Layout:
        {composition_analysis}
        ---
        Synthesize the final prompt based on all the information above.
        """

        try:
            chat_resp = self.openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
            )
            refined_prompt = chat_resp.choices[0].message.content.strip()
        except Exception as e:
            return self._create_error_response(message.sender_id, f"Failed to synthesize prompt with OpenAI: {e}")

        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={"refined_prompt": refined_prompt},
            message_type="response",
        )

