import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from midjourney_integration.client import MidjourneyClient, poll_until_complete, MidjourneyError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

async def main():
    """
    Demonstrates submitting a Midjourney imagine task with an Omni-Reference (--oref).
    """
    api_token = os.getenv("MIDJOURNEY_API_TOKEN")
    if not api_token:
        logging.error("MIDJOURNEY_API_TOKEN not found in environment variables.")
        return

    # --- Parameters for the imagine task ---
    # 1. The main text prompt for your image.
    prompt = "Vintage 1990s trading card design featuring a classic baseball card layout. Emphasize a distressed texture with nostalgic worn edges and authentic retro typography. Use a bold red, white, and blue color scheme to capture the era's spirit. Include a player name banner, position and number display, and team insignia to enhance the card's authenticity. The card should evoke a sense of collector nostalgia, fitting for a rare or limited edition piece"

    # 2. The public URL of your reference image for --oref.
    #    Replace this with a direct URL to your own image (e.g., from a GCS bucket or Discord).
    #    For this example, we'll use a public domain image URL.
    #    A good reference image is clear and focuses on the subject.
    oref_url = "https://storage.googleapis.com/bahroo_public/670047b5-4321-45d5-8c57-9df9355d60fc.png"

    # 3. The Omni-Weight (--ow) to control the influence of the reference image.
    #    Ranges from 0 to 1000. 100 is the default.
    #    Higher values mean the output will adhere more closely to the reference.
    oref_weight = 200

    # 4. Other optional parameters
    aspect_ratio = "5:7"
    process_mode = "fast" # or "fast", "turbo"

    try:
        client = MidjourneyClient(api_token=api_token)

        logging.info("Submitting imagine task with Omni-Reference...")
        task_response = await client.submit_imagine(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            process_mode=process_mode,
            oref_url=oref_url,
            oref_weight=oref_weight,
        )

        task_id = task_response.get("data", {}).get("task_id")
        if not task_id:
            logging.error("Failed to get task_id from submission response: %s", task_response)
            return

        logging.info(f"Task submitted successfully! Task ID: {task_id}")
        logging.info("Polling for task completion...")

        # Poll for the result
        final_result = await poll_until_complete(client, task_id)

        logging.info("Task completed!")
        image_url = final_result.get("output", {}).get("image_url")

        if image_url:
            logging.info(f"Final image URL: {image_url}")
        else:
            logging.error("Could not find image_url in the final result.")
            logging.info("Full result: %s", final_result)

    except MidjourneyError as e:
        logging.error(f"An error occurred with the Midjourney API: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())

