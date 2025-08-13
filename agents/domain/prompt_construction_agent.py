from agents.core.base_agent import BaseAgent, AgentMessage
import os

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class PromptConstructionAgent(BaseAgent):
    """
    An agent that constructs a refined prompt from an original prompt and image analysis.
    """
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        if not OpenAI:
            raise ImportError("The 'openai' library is required to use this agent.")
        self.openai_client = OpenAI()

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        original_prompt = message.content.get("original_prompt")
        image_analysis = message.content.get("image_analysis")

        system_prompt = (
            "You are a world-class Midjourney prompt engineer. Your task is to synthesize an original user prompt "
            "with a detailed analysis of user-provided images to create a new, superior prompt. The final prompt "
            "should be a single, coherent paragraph, limited to 5000 words. Do not generate an image, only the prompt."
        )
        user_prompt = f"Original prompt: '{original_prompt}'\n\nImage analysis:\n{image_analysis}"

        chat_resp = self.openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        
        refined_prompt = chat_resp.choices[0].message.content.strip()

        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={"refined_prompt": refined_prompt},
            message_type="response",
        )
