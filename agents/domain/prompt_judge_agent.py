from agents.core.base_agent import BaseAgent, AgentMessage
import os

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class PromptJudgeAgent(BaseAgent):
    """
    An agent that makes a final judgment on a refined prompt.
    """
    def __init__(self, agent_id: str, capabilities: set):
        super().__init__(agent_id, capabilities=capabilities)
        if not OpenAI:
            raise ImportError("The 'openai' library is required to use this agent.")
        self.openai_client = OpenAI()

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        original_prompt = message.content.get("original_prompt")
        refined_prompt = message.content.get("refined_prompt")
        critique = message.content.get("critique")

        system_prompt = (
            "You are a discerning AI judge with expertise in art, design, and prompt engineering. Your task is to make a final decision. "
            "Compare the original prompt with the refined prompt and its accompanying critique. "
            "Based on all available information, is the refined prompt a significant improvement over the original? "
            "Your final output should be ONLY the prompt you have chosen (either the original or the refined one). Do not add any extra text or explanation."
        )
        user_prompt = f"Original prompt: '{original_prompt}'\n\nRefined prompt: '{refined_prompt}'\n\nCritique:\n{critique}"

        try:
            chat_resp = self.openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
            )
            
            final_prompt = chat_resp.choices[0].message.content.strip()
        except Exception as e:
            return self._create_error_response(message.sender_id, f"Failed to judge prompt with OpenAI: {e}")


        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={"final_prompt": final_prompt, "judgment": "Completed"},
            message_type="response",
        )
