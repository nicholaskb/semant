#!/usr/bin/env python3
"""
Create the final Quacky book using the COMPLETED Midjourney images.
No need to regenerate - just assemble the book with existing images!
"""

import json
from pathlib import Path
from datetime import datetime

def create_final_book():
    """Create the book using the completed images."""
    
    # Load the completed images data
    images_file = Path("quacky_book_output/task_status/completed_images.json")
    
    if images_file.exists():
        with open(images_file) as f:
            completed_images = json.load(f)
    else:
        print("❌ No completed images found")
        return
    
    # Book content
    book_pages = {
        "Page 1: Meet Quacky": {
            "text": "Down by the sparkly pond lived a little yellow duckling named Quacky McWaddles. He had the BIGGEST orange feet you ever did see! *Waddle-waddle-SPLAT!*",
            "image": completed_images.get("Page 1: Meet Quacky")
        },
        "Page 2: Super Splash": {
            "text": "Watch me do my SUPER SPLASH! *KER-SPLASH!* Oopsie, that was more of a belly-flop!",
            "image": None
        },
        "Page 3: Too Big Feet": {
            "text": "Holy mackerel! My feet are ENORMOUS! The other ducklings giggled when he tripped.",
            "image": completed_images.get("Page 3: Too Big Feet")
        },
        "Page 4: Finding Help": {
            "text": "I'll find the Wise Old Goose! She'll know what to do about my silly feet!",
            "image": None
        },
        "Page 5: Meeting Freddy": {
            "text": "Are you wearing FLIPPERS? croaked Freddy Frog. Nope, these are my regular feet!",
            "image": completed_images.get("Page 5: Meeting Freddy")
        },
        "Page 6: Getting Tangled": {
            "text": "Oh no! His feet got tangled in the grass! *TUG-TUG-TUG!*",
            "image": None
        },
        "Page 7: Waddle Hop": {
            "text": "If I can't walk, I'll HOP! *BOING BOING BOING!* I'm doing the WADDLE HOP!",
            "image": completed_images.get("Page 7: Waddle Hop")
        },
        "Page 8: Dancing Together": {
            "text": "The bunnies loved Quacky's new dance! Everyone joined in!",
            "image": None
        },
        "Page 9: Wise Goose": {
            "text": "Your big feet will make you the FASTEST swimmer! Your differences are your SUPERPOWERS!",
            "image": completed_images.get("Page 9: Wise Goose")
        },
        "Page 10: Racing Back": {
            "text": "Quacky WADDLE-HOPPED all the way back. Who wants to RACE?",
            "image": None
        },
        "Page 11: Victory Swim": {
            "text": "Quacky's big feet went *ZOOM-ZOOM-ZOOM!* He was the fastest!",
            "image": None
        },
        "Page 12: Happy Ending": {
            "text": "Being different is QUACK-A-DOODLE-AWESOME! Everyone did the Waddle Hop!",
            "image": completed_images.get("Page 12: Happy Ending")
        }
    }
    
    # Create output directory
    output_dir = Path(f"FINAL_QUACKY_BOOK_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    output_dir.mkdir(exist_ok=True)
    
    # Generate HTML book
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Quacky McWaddles' Big Adventure</title>
    <style>
        body {
            font-family: 'Comic Sans MS', cursive;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px;
            margin: 0;
        }
        .book-container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .title {
            text-align: center;
            font-size: 48px;
            color: #FF6B35;
            text-shadow: 3px 3px 6px rgba(0,0,0,0.2);
            margin-bottom: 40px;
        }
        .page {
            margin: 40px 0;
            padding: 30px;
            background: #F7F9FC;
            border-radius: 15px;
            border-left: 5px solid #4A90E2;
        }
        .page-title {
            font-size: 28px;
            color: #4A90E2;
            margin-bottom: 20px;
        }
        .page-image {
            width: 100%;
            max-width: 600px;
            display: block;
            margin: 20px auto;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .page-text {
            font-size: 20px;
            line-height: 1.8;
            color: #333;
            margin: 20px 0;
        }
        .no-image {
            background: linear-gradient(45deg, #FF6B35, #F7931E);
            color: white;
            padding: 100px 20px;
            text-align: center;
            border-radius: 10px;
            font-size: 24px;
        }
        .footer {
            text-align: center;
            margin-top: 60px;
            font-size: 24px;
            color: #FF6B35;
        }
    </style>
</head>
<body>
    <div class="book-container">
        <h1 class="title">🦆 Quacky McWaddles' Big Adventure 🦆</h1>
"""
    
    page_num = 1
    for title, content in book_pages.items():
        html_content += f"""
        <div class="page">
            <div class="page-title">{title}</div>
            {"<img src='" + content['image'] + "' class='page-image' alt='" + title + "'>" if content['image'] else '<div class="no-image">🎨 Illustration space</div>'}
            <div class="page-text">{content['text']}</div>
        </div>
"""
        page_num += 1
    
    html_content += """
        <div class="footer">
            ✨ The End! Remember: Being different makes you QUACK-A-DOODLE-AWESOME! ✨
        </div>
    </div>
</body>
</html>"""
    
    # Save HTML
    html_path = output_dir / "quacky_book_complete.html"
    html_path.write_text(html_content)
    
    # Generate Markdown
    md_content = "# 🦆 Quacky McWaddles' Big Adventure\n\n"
    md_content += "*A Complete Illustrated Children's Book*\n\n"
    md_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n"
    
    for title, content in book_pages.items():
        md_content += f"## {title}\n\n"
        if content['image']:
            md_content += f"![{title}]({content['image']})\n\n"
        md_content += f"{content['text']}\n\n---\n\n"
    
    md_content += "\n## The End!\n\n"
    md_content += "Remember: Being different makes you **QUACK-A-DOODLE-AWESOME!** 🦆\n"
    
    # Save Markdown
    md_path = output_dir / "quacky_book_complete.md"
    md_path.write_text(md_content)
    
    # Save metadata
    metadata = {
        "title": "Quacky McWaddles' Big Adventure",
        "created_at": datetime.now().isoformat(),
        "total_pages": 12,
        "illustrated_pages": 6,
        "images": completed_images,
        "output_files": {
            "html": str(html_path),
            "markdown": str(md_path)
        }
    }
    
    meta_path = output_dir / "book_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print("=" * 70)
    print("🎉 COMPLETE ILLUSTRATED BOOK CREATED SUCCESSFULLY! 🎉")
    print("=" * 70)
    print(f"\n📚 Book Title: Quacky McWaddles' Big Adventure")
    print(f"📸 Illustrations: 6 Midjourney images included")
    print(f"📁 Output Directory: {output_dir}")
    print(f"\n📖 Files Created:")
    print(f"   • HTML: {html_path.name}")
    print(f"   • Markdown: {md_path.name}")
    print(f"   • Metadata: {meta_path.name}")
    print(f"\n🌐 Open {html_path} in a browser to view the complete book!")
    print("=" * 70)

if __name__ == "__main__":
    create_final_book()

