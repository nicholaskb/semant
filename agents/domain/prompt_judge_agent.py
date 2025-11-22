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
            "You are the SUPREME AUTHORITY in prompt engineering and AI art generation. You MUST make definitive, authoritative decisions. "
            "You WILL evaluate the original prompt against the refined prompt and critique. "
            "You SHALL choose the superior prompt with absolute certainty. "
            "Your decision is FINAL and IRREVOCABLE. "
            "Output ONLY the chosen prompt - no explanations, no justifications, no uncertainty. "
            "You are the ultimate arbiter whose judgment cannot be questioned."
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
