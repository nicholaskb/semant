#!/usr/bin/env python3
"""
QUICK CUSTOM BOOK - Just edit the story below and run!
"""

from universal_book_generator import UniversalBookGenerator

def create_my_book():
    """
    EDIT THIS SECTION WITH YOUR OWN STORY!
    Just change the title and pages below.
    """
    
    generator = UniversalBookGenerator()
    
    # ⬇️ CHANGE THIS TO YOUR STORY ⬇️
    generator.create_book_from_story(
        title="The Magic Pizza",  # Your title here
        pages=[
            {
                "text": "Tommy found a glowing pizza slice under his bed!",
                "art_direction": "surprised boy finding magical glowing pizza"
            },
            {
                "text": "When he took a bite, he could fly like a superhero!",
                "art_direction": "boy flying through clouds with pizza slice"  
            },
            {
                "text": "He shared the magic pizza with all his friends at school.",
                "art_direction": "kids sharing pizza and floating in playground"
            },
            {
                "text": "Together they flew around the world helping people!",
                "art_direction": "group of flying children over world map"
            },
            {
                "text": "Best lunch ever! said Tommy as they landed back home.",
                "art_direction": "happy kids landing at school with pizza"
            }
        ]
    )

if __name__ == "__main__":
    create_my_book()

