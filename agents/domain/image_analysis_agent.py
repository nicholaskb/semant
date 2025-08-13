from agents.core.base_agent import BaseAgent, AgentMessage
import os

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class ImageAnalysisAgent(BaseAgent):
    """
    An agent that analyzes images and generates a detailed description.
    """
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        if not OpenAI:
            raise ImportError("The 'openai' library is required to use this agent.")
        self.openai_client = OpenAI()

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        image_urls = message.content.get("image_urls", [])
        if not image_urls:
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={"analysis": "No images provided."},
                message_type="response",
            )

        content = [{
            "type": "text",
            "text": "Analyze these images in detail. Describe the aesthetic, color palette, any logos or text, and the overall composition. This analysis will be used to create a new Midjourney prompt."
        }]
        for url in image_urls:
            content.append({"type": "image_url", "image_url": {"url": url}})

        chat_resp = self.openai_client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=[{"role": "user", "content": content}],
            temperature=0.7,
        )
        
        analysis = chat_resp.choices[0].message.content.strip()

        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={"analysis": analysis},
            message_type="response",
        )
