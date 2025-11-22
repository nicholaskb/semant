#!/usr/bin/env python3
"""
Use the EXISTING BookGeneratorTool to create Quacky McWaddles book.
This leverages all the working infrastructure already built.
"""

import asyncio
import os
from dotenv import load_dotenv
from semant.agent_tools.midjourney.tools.book_generator_tool import BookGeneratorTool

load_dotenv()

async def create_quacky_book():
    """Create the Quacky book using the existing tool."""
    
    # Initialize the book generator tool
    tool = BookGeneratorTool()
    
    # Define the book content
    title = "Quacky McWaddles' Big Adventure"
    
    pages = [
        {
            "title": "Meet Quacky McWaddles",
            "text": "Down by the sparkly pond lived a little yellow duckling named Quacky McWaddles. He had the BIGGEST orange feet you ever did see! *Waddle-waddle-SPLAT!*",
            "prompt": "cute yellow duckling with huge orange webbed feet by a blue pond, children's book watercolor illustration --ar 16:9"
        },
        {
            "title": "The Super Splash",
            "text": "Watch me do my SUPER SPLASH! shouted Quacky. *THUMP-THUMP-THUMP* went his big feet! *KER-SPLASH!* Oopsie! That was more of a belly-flop!",
            "prompt": "yellow duckling belly-flopping into pond, big water splash, comic expression --ar 16:9"
        },
        {
            "title": "The Big Feet Problem",
            "text": "Holy mackerel! gasped Quacky. My feet are ENORMOUS! The other ducklings giggled when he tripped over them.",
            "prompt": "sad yellow duckling looking at his huge orange feet, other small ducklings nearby --ar 16:9"
        },
        {
            "title": "Finding the Wise Goose",
            "text": "I'll find the Wise Old Goose! She'll know how to fix my silly big feet!",
            "prompt": "determined yellow duckling waddling through meadow on a quest --ar 16:9"
        },
        {
            "title": "Meeting Freddy Frog",
            "text": "Are you wearing FLIPPERS? croaked Freddy Frog. Nope! said Quacky. These are my regular feet!",
            "prompt": "yellow duckling meeting green frog in meadow, frog looking amazed at big feet --ar 16:9"
        },
        {
            "title": "Getting Tangled",
            "text": "Oh no! Quacky's big feet got tangled in the reedy grass! He pulled and tugged... *TUG-TUG-TUG!*",
            "prompt": "yellow duckling with feet tangled in green reeds, struggling but determined --ar 16:9"
        },
        {
            "title": "The Waddle Hop",
            "text": "If he couldn't walk... he'd HOP! *BOING! BOING! BOING!* I'm doing the WADDLE HOP!",
            "prompt": "yellow duckling hopping with joy, motion lines, bunnies watching and copying --ar 16:9"
        },
        {
            "title": "Dancing Bunnies",
            "text": "The bunnies loved Quacky's new dance! They all started doing the Waddle Hop together!",
            "prompt": "yellow duckling and three bunnies all hopping together in meadow --ar 16:9"
        },
        {
            "title": "The Wise Old Goose",
            "text": "Those magnificent feet will make you the FASTEST swimmer! Your differences are your SUPERPOWERS!",
            "prompt": "wise white goose with tiny spectacles talking to excited yellow duckling on hilltop --ar 16:9"
        },
        {
            "title": "Racing Back",
            "text": "Quacky WADDLE-HOPPED all the way back! Who wants to RACE? he called.",
            "prompt": "yellow duckling rushing back to pond, leaving dust trail, excited expression --ar 16:9"
        },
        {
            "title": "The Swimming Race",
            "text": "Into the pond they dove! Quacky's big feet went *ZOOM-ZOOM-ZOOM!* He was SO FAST!",
            "prompt": "yellow duckling swimming fast with big feet as propellers, other ducks behind --ar 16:9"
        },
        {
            "title": "Happy Ending",
            "text": "Quacky won! Being different was QUACK-A-DOODLE-AWESOME! Everyone wanted to learn the Waddle Hop!",
            "prompt": "yellow duckling celebrating with all ducks doing the waddle hop dance by pond --ar 16:9"
        }
    ]
    
    print("=" * 60)
    print("📚 CREATING QUACKY MCWADDLES BOOK")
    print("Using the existing BookGeneratorTool")
    print("=" * 60)
    print()
    
    # Generate the book
    result = await tool.generate_book(
        title=title,
        pages=pages,
        max_pages_to_illustrate=3  # Start with 3 to test
    )
    
    print("\n" + "=" * 60)
    print("✨ BOOK GENERATION COMPLETE!")
    print(f"Workflow ID: {result['workflow_id']}")
    print(f"Pages with illustrations: {result['pages_generated']}/{result['total_pages']}")
    print(f"Output files: {result['output_files']}")
    print("=" * 60)
    
    return result


async def main():
    # Check for API token
    if not os.getenv("MIDJOURNEY_API_TOKEN"):
        print("❌ Error: MIDJOURNEY_API_TOKEN not set")
        print("Please add to your .env file")
        return
    
    await create_quacky_book()


if __name__ == "__main__":
    asyncio.run(main())

