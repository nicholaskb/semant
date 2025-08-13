from agents.core.base_agent import BaseAgent, AgentMessage
import os

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class PromptCriticAgent(BaseAgent):
    """
    An agent that critiques a refined prompt.
    """
    def __init__(self, agent_id: str, capabilities: set):
        super().__init__(agent_id, capabilities=capabilities)
        if not OpenAI:
            raise ImportError("The 'openai' library is required to use this agent.")
        self.openai_client = OpenAI()

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        refined_prompt = message.content.get("refined_prompt")
        if not refined_prompt:
            return self._create_error_response(message.sender_id, "No refined prompt provided for critique.")

        system_prompt = (
            "You are a sharp and insightful art and design critic. Your task is to review the following Midjourney prompt. "
            "Is it clear, vivid, and detailed? Does it effectively describe a compelling and aesthetically pleasing image? "
            "Does it leave room for creative interpretation while providing enough guidance? "
            "Provide your critique and suggest specific, actionable improvements. Frame your feedback constructively."
        )
        
        try:
            chat_resp = self.openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": refined_prompt},
                ],
                temperature=0.7,
            )
            critique = chat_resp.choices[0].message.content.strip()
        except Exception as e:
            return self._create_error_response(message.sender_id, f"Failed to critique prompt with OpenAI: {e}")

        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={"critique": critique},
            message_type="response",
        )

