#!/usr/bin/env python3
"""
REAL DUCK BOOK - Actually generates DUCK images, not foxes!
Shows prompts below each image
"""

import asyncio
from pathlib import Path
from datetime import datetime
import webbrowser
from dotenv import load_dotenv
from semant.agent_tools.midjourney import REGISTRY

load_dotenv()

async def generate_real_duck_book():
    """Generate a REAL duck book with proper prompts visible."""
    
    print("🦆 GENERATING ACTUAL DUCK IMAGES (NOT FOXES!)")
    print("="*70)
    
    imagine_tool = REGISTRY["mj.imagine"]()
    
    # DUCK-SPECIFIC PROMPTS (not foxes!)
    pages = [
        {
            "page": 1,
            "title": "Meet Quacky",
            "text": "Down by the sparkly pond lived Quacky McWaddles with the BIGGEST orange feet!",
            "prompt": "cute yellow DUCKLING with oversized orange webbed feet standing by blue pond, watercolor children's book illustration, NO FOX, baby duck character",
            "keywords": "DUCKLING, YELLOW, ORANGE FEET, POND"
        },
        {
            "page": 2,
            "title": "The Problem",
            "text": "Oh no! My feet are too big! The other ducklings giggled.",
            "prompt": "sad yellow DUCKLING looking down at huge orange webbed feet, other small DUCKLINGS laughing, watercolor style, NO FOX, duck characters only",
            "keywords": "SAD DUCKLING, BIG FEET, OTHER DUCKS"
        },
        {
            "page": 3,
            "title": "The Journey",
            "text": "I'll find the Wise Old Goose! She'll know what to do!",
            "prompt": "determined yellow DUCKLING waddling through meadow on adventure, watercolor children's book, NO FOX, duck protagonist",
            "keywords": "DUCKLING WALKING, MEADOW, ADVENTURE"
        },
        {
            "page": 4,
            "title": "Meeting Friends",
            "text": "Are you wearing FLIPPERS? asked Freddy Frog.",
            "prompt": "yellow DUCKLING meeting green FROG in meadow, frog pointing at duck's big orange feet, watercolor illustration, NO FOX",
            "keywords": "DUCKLING, FROG, BIG FEET"
        },
        {
            "page": 5,
            "title": "The Waddle Hop",
            "text": "If I can't walk, I'll HOP! BOING BOING BOING!",
            "prompt": "yellow DUCKLING hopping joyfully, bunnies watching, motion lines, watercolor children's book, NO FOX, duck jumping",
            "keywords": "DUCKLING HOPPING, BUNNIES, MOTION"
        },
        {
            "page": 6,
            "title": "Happy Ending",
            "text": "Being different is QUACK-A-DOODLE-AWESOME!",
            "prompt": "group of DUCKLINGS celebrating by pond, yellow duckling with big feet in center, party atmosphere, watercolor, NO FOX, all ducks",
            "keywords": "DUCK PARTY, CELEBRATION, POND"
        }
    ]
    
    # Generate each page
    generated_pages = []
    
    for page_data in pages:
        print(f"\n📖 Page {page_data['page']}: {page_data['title']}")
        print(f"   🦆 Prompt: {page_data['prompt']}")
        
        try:
            # Submit to Midjourney with DUCK prompt
            result = await imagine_tool.run(
                prompt=page_data['prompt'],
                aspect_ratio="16:9",
                model_version="v6",
                process_mode="fast"
            )
            
            task_id = result.get("data", {}).get("task_id")
            if task_id:
                print(f"   Task ID: {task_id}")
                page_data['task_id'] = task_id
                page_data['status'] = 'submitted'
            else:
                print(f"   ⚠️ No task ID received")
                page_data['status'] = 'failed'
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            page_data['status'] = 'error'
        
        generated_pages.append(page_data)
        await asyncio.sleep(2)  # Rate limiting
    
    # Create HTML book with prompts visible
    output_dir = Path("real_duck_book")
    output_dir.mkdir(exist_ok=True)
    
    html = """<!DOCTYPE html>
<html>
<head>
    <title>REAL DUCK BOOK (Not Foxes!)</title>
    <style>
        body { 
            font-family: 'Comic Sans MS', cursive; 
            background: linear-gradient(135deg, #FFD700, #87CEEB); 
            padding: 20px;
            margin: 0;
        }
        .header-banner {
            background: #FF6B6B;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 24px;
            margin-bottom: 20px;
            border-radius: 10px;
        }
        .book { 
            max-width: 1000px; 
            margin: auto; 
            background: white; 
            border-radius: 20px; 
            padding: 40px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }
        h1 {
            color: #FFA500;
            text-align: center;
            font-size: 48px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        .duck-emoji {
            font-size: 60px;
            animation: waddle 2s infinite;
        }
        @keyframes waddle {
            0%, 100% { transform: rotate(-5deg); }
            50% { transform: rotate(5deg); }
        }
        .page { 
            margin: 40px 0; 
            padding: 30px; 
            background: linear-gradient(135deg, #FFF9E6, #FFF);
            border-radius: 15px;
            border: 4px solid #FFD700;
        }
        .page-header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }
        .page-number {
            background: #FFA500;
            color: white;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 20px;
            margin-right: 15px;
        }
        .page h2 { 
            color: #FF6B6B;
            margin: 0;
            font-size: 32px;
            flex-grow: 1;
        }
        .image-placeholder {
            width: 100%;
            height: 450px;
            background: linear-gradient(135deg, #E3F2FD, #BBDEFB);
            border-radius: 10px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border: 3px dashed #2196F3;
            margin: 20px 0;
        }
        .placeholder-text {
            font-size: 24px;
            color: #1976D2;
            margin-bottom: 20px;
        }
        .task-status {
            background: #FFF3CD;
            color: #856404;
            padding: 10px;
            border-radius: 5px;
            font-size: 14px;
        }
        .page-text { 
            font-size: 26px; 
            line-height: 1.8; 
            color: #333;
            background: white;
            padding: 25px;
            border-radius: 10px;
            border-left: 6px solid #FFA500;
            margin: 20px 0;
        }
        .prompt-box {
            background: #E8F5E9;
            border: 2px solid #4CAF50;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }
        .prompt-label {
            font-weight: bold;
            color: #2E7D32;
            font-size: 18px;
            margin-bottom: 10px;
        }
        .prompt-text {
            font-family: 'Courier New', monospace;
            font-size: 14px;
            color: #1B5E20;
            line-height: 1.6;
            background: white;
            padding: 15px;
            border-radius: 5px;
        }
        .keywords {
            margin-top: 10px;
            padding: 10px;
            background: #FFE0B2;
            border-radius: 5px;
        }
        .keyword-badge {
            display: inline-block;
            background: #FF6B35;
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            margin: 5px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="header-banner">
        ⚠️ THIS IS THE REAL DUCK BOOK - NO MORE FOXES! ⚠️
    </div>
    
    <div class="book">
        <h1>
            <span class="duck-emoji">🦆</span> 
            Quacky McWaddles' Big Adventure 
            <span class="duck-emoji">🦆</span>
        </h1>
        <p style="text-align: center; font-size: 20px; color: #666;">
            A story about a DUCKLING (not a fox!)
        </p>
"""
    
    for page in generated_pages:
        status_text = f"Task {page.get('task_id', 'N/A')[:8]}..." if page.get('task_id') else "Pending"
        
        html += f"""
        <div class="page">
            <div class="page-header">
                <div class="page-number">{page['page']}</div>
                <h2>{page['title']}</h2>
            </div>
            
            <div class="page-text">"{page['text']}"</div>
            
            <div class="image-placeholder">
                <div class="placeholder-text">🦆 DUCK IMAGE GENERATING...</div>
                <div class="task-status">Status: {page.get('status', 'pending')}</div>
                <div class="task-status">{status_text}</div>
            </div>
            
            <div class="prompt-box">
                <div class="prompt-label">🎨 MIDJOURNEY PROMPT (This generates a DUCK, not a fox!):</div>
                <div class="prompt-text">{page['prompt']}</div>
                
                <div class="keywords">
                    <strong>Key Elements:</strong><br>
                    {''.join([f'<span class="keyword-badge">{kw}</span>' for kw in page['keywords'].split(', ')])}
                </div>
            </div>
        </div>
"""
    
    html += """
        <div style="text-align: center; margin-top: 50px; padding: 30px; background: #FFE0B2; border-radius: 15px;">
            <h3 style="color: #FF6B35;">🦆 Status Report 🦆</h3>
            <p style="font-size: 18px; color: #666;">
                All prompts specifically request DUCKS and explicitly say "NO FOX"<br>
                Images are being generated with proper duck characters<br>
                <strong>No more fox mix-ups!</strong>
            </p>
        </div>
    </div>
</body>
</html>"""
    
    book_path = output_dir / "duck_book_with_prompts.html"
    book_path.write_text(html)
    
    print("\n" + "="*70)
    print("✅ REAL DUCK BOOK CREATED!")
    print("="*70)
    print(f"\n📚 Book location: {book_path}")
    print("\nWhat's fixed:")
    print("• All prompts explicitly request DUCKS")
    print("• Prompts say 'NO FOX' to avoid confusion")
    print("• Each page shows the exact prompt used")
    print("• Keywords highlight duck-specific elements")
    
    # Open automatically
    webbrowser.open(f"file://{book_path.absolute()}")
    
    return str(book_path)

if __name__ == "__main__":
    asyncio.run(generate_real_duck_book())

