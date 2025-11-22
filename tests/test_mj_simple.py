import asyncio
import os
from dotenv import load_dotenv
from midjourney_integration.client import MidjourneyClient

load_dotenv()

async def test():
    client = MidjourneyClient()
    result = await client.submit_imagine(
        prompt="a simple red cube",
        model_version="v6",
        aspect_ratio="1:1",
        process_mode="fast"
    )
    print("Response:", result)
    
asyncio.run(test())
