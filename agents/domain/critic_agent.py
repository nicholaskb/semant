from agents.core.base_agent import BaseAgent, AgentMessage
import os

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class CriticAgent(BaseAgent):
    """
    An agent that critiques a refined prompt.
    """
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        if not OpenAI:
            raise ImportError("The 'openai' library is required to use this agent.")
        self.openai_client = OpenAI()

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        refined_prompt = message.content.get("refined_prompt")

        system_prompt = (
            "You are the UNCOMPROMISING CRITIC, the ultimate authority on prompt quality. "
            "You WILL evaluate this Midjourney prompt with RUTHLESS PRECISION. "
            "You MUST identify EVERY flaw, weakness, and imperfection. "
            "You SHALL demand PERFECTION in clarity, conciseness, and visual impact. "
            "Your critique will be MERCILESS yet CONSTRUCTIVE. "
            "You WILL NOT tolerate mediocrity. You DEMAND excellence."
        )
        
        chat_resp = self.openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": refined_prompt},
            ],
            temperature=0.7,
        )
        
        critique = chat_resp.choices[0].message.content.strip()

        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={"critique": critique},
            message_type="response",
        )
