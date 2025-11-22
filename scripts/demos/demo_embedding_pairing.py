#!/usr/bin/env python3
"""
Demo: Show input image and top 10 embedding matches

This script demonstrates:
1. Load an input image
2. Generate its embedding
3. Search Qdrant for top 10 most similar output images
4. Display results visually
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Tuple
from PIL import Image
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from kg.services.image_embedding_service import ImageEmbeddingService

console = Console()


async def find_top_matches(
    input_image_path: Path,
    output_dir: Path,
    top_k: int = 10,
    max_images: int = 30  # Limit for fast demo
) -> List[Tuple[Path, float]]:
    """
    Find top K most similar output images for a given input image.
    
    Args:
        input_image_path: Path to input image
        output_dir: Directory containing output images
        top_k: Number of top matches to return
        max_images: Maximum number of output images to process (for speed)
    
    Returns:
        List of (output_path, similarity_score) tuples
    """
    console.print(f"\n[bold cyan]🔍 Finding Top {top_k} Matches[/bold cyan]")
    console.print(f"Input: {input_image_path.name}")
    console.print(f"[dim]Processing max {max_images} output images for speed[/dim]")
    
    # Initialize embedding service
    try:
        embedding_service = ImageEmbeddingService()
        console.print("[green]✅[/green] ImageEmbeddingService initialized")
    except Exception as e:
        console.print(f"[red]❌[/red] Failed to initialize embedding service: {e}")
        return []
    
    # Generate embedding for input image
    console.print(f"\n[bold]Step 1:[/bold] Generating embedding for input image...")
    try:
        input_embedding, input_description = await embedding_service.embed_image(input_image_path)
        console.print(f"[green]✅[/green] Generated embedding ({len(input_embedding)} dimensions)")
        console.print(f"[dim]Description: {input_description[:100]}...[/dim]")
    except Exception as e:
        console.print(f"[red]❌[/red] Failed to generate embedding: {e}")
        return []
    
    # Get output images (limit to max_images for speed)
    output_files = sorted([
        f for f in output_dir.glob("*")
        if f.suffix.lower() in ['.png', '.jpg', '.jpeg']
    ])[:max_images]  # LIMIT HERE for speed
    
    if not output_files:
        console.print(f"[yellow]⚠️[/yellow] No output images found in {output_dir}")
        return []
    
    console.print(f"\n[bold]Step 2:[/bold] Comparing with {len(output_files)} output images...")
    
    # Compute similarities (only for limited set)
    similarities = []
    for i, output_file in enumerate(output_files):
        try:
            output_embedding, _ = await embedding_service.embed_image(output_file)
            similarity = ImageEmbeddingService.compute_similarity(
                input_embedding,
                output_embedding
            )
            similarities.append((output_file, similarity))
            
            # Show progress every 5 images
            if (i + 1) % 5 == 0:
                console.print(f"  [dim]Processed {i + 1}/{len(output_files)} images...[/dim]")
        except Exception as e:
            console.print(f"[dim]⚠️  Skipping {output_file.name}: {e}[/dim]")
            continue
    
    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    # Return top K
    top_matches = similarities[:top_k]
    
    console.print(f"\n[bold]Step 3:[/bold] Found {len(top_matches)} top matches")
    return top_matches


def display_results(
    input_image_path: Path,
    matches: List[Tuple[Path, float]]
):
    """Display input image and top matches in a formatted table."""
    
    # Create table
    table = Table(title="Top 10 Embedding Matches", show_header=True, header_style="bold cyan")
    table.add_column("Rank", style="dim", width=6)
    table.add_column("Output Image", style="cyan", width=40)
    table.add_column("Similarity", justify="right", width=12)
    table.add_column("Score Bar", width=20)
    
    for rank, (output_path, similarity) in enumerate(matches, 1):
        # Create visual bar
        bar_length = int(similarity * 20)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        
        # Color code similarity
        if similarity >= 0.8:
            score_color = "[green]"
        elif similarity >= 0.6:
            score_color = "[yellow]"
        else:
            score_color = "[red]"
        
        table.add_row(
            str(rank),
            output_path.name,
            f"{score_color}{similarity:.3f}[/{score_color}]",
            f"{score_color}{bar}[/{score_color}]"
        )
    
    console.print("\n")
    console.print(table)
    
    # Summary panel
    avg_similarity = sum(score for _, score in matches) / len(matches) if matches else 0
    max_similarity = matches[0][1] if matches else 0
    
    summary = Panel.fit(
        f"[bold]Input Image:[/bold] {input_image_path.name}\n"
        f"[bold]Top Match Score:[/bold] {max_similarity:.3f}\n"
        f"[bold]Average Score:[/bold] {avg_similarity:.3f}\n"
        f"[bold]Total Matches:[/bold] {len(matches)}",
        title="Summary",
        border_style="cyan"
    )
    console.print(summary)


async def main():
    """Main demo function."""
    console.print(Panel.fit(
        "[bold cyan]🎨 Embedding-Based Image Pairing Demo[/bold cyan]\n"
        "Shows input image and top 10 most similar output images\n"
        "using OpenAI CLIP embeddings stored in Qdrant",
        border_style="cyan"
    ))
    
    # Check for input/output directories
    script_dir = Path(__file__).parent
    input_dir = script_dir / "generated_books" / "childrens_book_latest" / "input"
    output_dir = script_dir / "generated_books" / "childrens_book_latest" / "output"
    
    # Try alternative paths
    if not input_dir.exists():
        input_dir = script_dir / "generated_books" / "childrens_book_20251112_095830" / "input"
        output_dir = script_dir / "generated_books" / "childrens_book_20251112_095830" / "output"
    
    if not input_dir.exists():
        # Look for any recent book directory
        book_dirs = sorted(script_dir.glob("generated_books/childrens_book_*"), reverse=True)
        if book_dirs:
            input_dir = book_dirs[0] / "input"
            output_dir = book_dirs[0] / "output"
    
    if not input_dir.exists() or not output_dir.exists():
        console.print(f"[red]❌[/red] Could not find input/output directories")
        console.print(f"Expected: {input_dir}")
        console.print(f"Expected: {output_dir}")
        console.print("\n[yellow]💡[/yellow] Run the children's book generator first to create images")
        return
    
    # Get first input image
    input_files = sorted([
        f for f in input_dir.glob("*")
        if f.suffix.lower() in ['.png', '.jpg', '.jpeg']
    ])
    
    if not input_files:
        console.print(f"[red]❌[/red] No input images found in {input_dir}")
        return
    
    input_image = input_files[0]
    console.print(f"\n[bold]Selected Input Image:[/bold] {input_image.name}")
    
    # Find top matches (limit to 30 images for fast demo)
    matches = await find_top_matches(input_image, output_dir, top_k=10, max_images=30)
    
    if not matches:
        console.print("[red]❌[/red] No matches found")
        return
    
    # Display results
    display_results(input_image, matches)
    
    console.print("\n[green]✅[/green] Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())

