from agents.core.base_agent import BaseAgent, AgentMessage
import os
import httpx
import base64

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class ColorPaletteAgent(BaseAgent):
    """
    An agent that identifies the dominant color palette in images.
    """
    def __init__(self, agent_id: str, capabilities: set):
        super().__init__(agent_id, capabilities=capabilities)
        if not OpenAI:
            raise ImportError("The 'openai' library is required to use this agent.")
        self.openai_client = OpenAI()

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        image_urls = message.content.get("image_urls", [])
        if not image_urls:
            return self._create_error_response(message.sender_id, "No image URLs provided.")

        content = [{
            "type": "text",
            "text": "Analyze the following images and identify the dominant color palette. List the key colors and describe the overall color scheme (e.g., warm, cool, vibrant, muted). Your analysis will be used to generate a Midjourney prompt."
        }]
        
        try:
            async with httpx.AsyncClient() as client:
                for url in image_urls:
                    response = await client.get(url)
                    response.raise_for_status()
                    encoded_image = base64.b64encode(response.content).decode("utf-8")
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{encoded_image}"}
                    })
        except httpx.HTTPStatusError as e:
            return self._create_error_response(message.sender_id, f"Failed to download image from {e.request.url}: {e.response.status_code}")
        except Exception as e:
            return self._create_error_response(message.sender_id, f"An unexpected error occurred while downloading images: {e}")

        try:
            chat_resp = self.openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": content}],
                temperature=0.7,
            )
            analysis = chat_resp.choices[0].message.content.strip()
        except Exception as e:
            return self._create_error_response(message.sender_id, f"Failed to analyze color palette with OpenAI: {e}")

        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={"color_palette_analysis": analysis},
            message_type="response",
        )

