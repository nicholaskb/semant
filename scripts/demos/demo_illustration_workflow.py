#!/usr/bin/env python3
"""
Demonstration of Midjourney Integration with Multi-Agent Orchestration
for Quacky McWaddles' Big Adventure Illustrations
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn
import httpx

console = Console()

class IllustrationDemo:
    """Demonstrate the complete illustration workflow with Midjourney."""
    
    def __init__(self):
        self.workflow_id = f"illustration_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.book_pages = {
            1: {
                "text": "Down by the sparkly pond lived Quacky McWaddles",
                "key_elements": ["yellow duckling", "big orange feet", "sparkly pond", "splashing"]
            },
            7: {
                "text": "His feet got tangled in the reedy grass - time for the Waddle Hop!",
                "key_elements": ["tangled in reeds", "hopping motion", "watching bunnies", "meadow"]
            },
            9: {
                "text": "The Wise Old Goose adjusted her spectacles",
                "key_elements": ["wise white goose", "tiny spectacles", "hilltop", "pond below"]
            }
        }
        
    async def run_complete_demonstration(self):
        """Run the complete illustration workflow demonstration."""
        
        console.print(Panel.fit(
            "[bold cyan]🎨 Midjourney Illustration Workflow Demo[/bold cyan]\n"
            "[yellow]Creating Illustrations for: Quacky McWaddles' Big Adventure[/yellow]\n"
            "Multi-Agent Evaluation & Refinement System",
            border_style="cyan"
        ))
        
        # Phase 1: Generate and Refine Prompts
        console.print("\n[bold]📝 Phase 1: Prompt Generation & Refinement[/bold]")
        prompts = await self.generate_and_refine_prompts()
        
        # Phase 2: Generate Illustrations with Midjourney
        console.print("\n[bold]🎨 Phase 2: Midjourney Image Generation[/bold]")
        illustrations = await self.generate_illustrations(prompts)
        
        # Phase 3: Multi-Agent Evaluation
        console.print("\n[bold]👥 Phase 3: Multi-Agent Evaluation[/bold]")
        evaluations = await self.evaluate_illustrations(illustrations)
        
        # Phase 4: Upscale Best Images
        console.print("\n[bold]⬆️ Phase 4: Upscaling Best Selections[/bold]")
        upscaled = await self.upscale_best_images(evaluations)
        
        # Phase 5: Alternative Branches
        console.print("\n[bold]🌿 Phase 5: Alternative Illustration Branches[/bold]")
        alternatives = await self.create_alternative_branches(evaluations)
        
        # Phase 6: Final Selection
        console.print("\n[bold]✅ Phase 6: Final Illustration Selection[/bold]")
        final = await self.finalize_illustrations(upscaled, alternatives)
        
        # Summary
        await self.display_summary(final)
    
    async def generate_and_refine_prompts(self):
        """Generate base prompts and refine them."""
        prompts = {}
        
        for page_num, content in self.book_pages.items():
            # Generate base prompt
            base_prompt = self.create_base_prompt(page_num, content)
            
            # Show base prompt
            console.print(f"\n[cyan]Page {page_num} Base Prompt:[/cyan]")
            console.print(Panel(base_prompt, border_style="dim"))
            
            # Simulate refinement via API
            refined_prompt = await self.refine_prompt_via_api(base_prompt)
            
            # Show refined prompt
            console.print(f"[green]Refined Prompt:[/green]")
            console.print(Panel(refined_prompt, border_style="green"))
            
            prompts[page_num] = {
                "base": base_prompt,
                "refined": refined_prompt,
                "improvements": self.analyze_prompt_improvements(base_prompt, refined_prompt)
            }
        
        # Display improvements table
        table = Table(title="Prompt Refinement Analysis")
        table.add_column("Page", style="cyan")
        table.add_column("Improvements", style="green")
        table.add_column("Added Details", style="yellow")
        
        for page_num, prompt_data in prompts.items():
            improvements = prompt_data["improvements"]
            table.add_row(
                str(page_num),
                improvements["type"],
                ", ".join(improvements["additions"][:3])
            )
        
        console.print(table)
        
        return prompts
    
    def create_base_prompt(self, page_num: int, content: Dict) -> str:
        """Create base Midjourney prompt."""
        elements = content["key_elements"]
        
        if page_num == 1:
            return (
                f"Children's book watercolor illustration: {content['text']}, "
                f"featuring {', '.join(elements)}, bright cheerful colors, "
                f"whimsical style --ar 16:9 --v 6"
            )
        elif page_num == 7:
            return (
                f"Funny children's book scene: {content['text']}, "
                f"showing {', '.join(elements)}, dynamic action, "
                f"cartoon style watercolor --ar 16:9 --v 6"
            )
        else:
            return (
                f"Storybook illustration: {content['text']}, "
                f"featuring {', '.join(elements)}, warm lighting, "
                f"professional children's book art --ar 16:9 --v 6"
            )
    
    async def refine_prompt_via_api(self, base_prompt: str) -> str:
        """Simulate prompt refinement via Planner agent."""
        # Simulate API call for refinement
        await asyncio.sleep(0.5)  # Simulate processing
        
        # Add refinements
        refinements = {
            "style_details": ["soft edges", "dreamy atmosphere", "storybook quality"],
            "technical": ["high detail", "professional illustration", "publication ready"],
            "mood": ["joyful", "whimsical", "endearing"],
            "composition": ["rule of thirds", "dynamic angles", "visual hierarchy"]
        }
        
        # Build refined prompt
        refined = base_prompt.replace("--ar 16:9", "")
        refined += f", {', '.join(refinements['style_details'])}"
        refined += f", {', '.join(refinements['mood'])}"
        refined += ", masterpiece quality --ar 16:9 --v 6 --quality 2"
        
        return refined
    
    def analyze_prompt_improvements(self, base: str, refined: str) -> Dict:
        """Analyze what improvements were made."""
        return {
            "type": "Enhanced with style and mood",
            "additions": [
                "soft edges",
                "dreamy atmosphere", 
                "masterpiece quality",
                "professional illustration",
                "visual hierarchy"
            ],
            "quality_boost": "+40% detail level"
        }
    
    async def generate_illustrations(self, prompts: Dict) -> Dict:
        """Simulate Midjourney image generation."""
        illustrations = {}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            for page_num, prompt_data in prompts.items():
                task = progress.add_task(f"Generating illustrations for page {page_num}...", total=None)
                
                # Simulate API call to Midjourney
                await asyncio.sleep(1.5)
                
                # Generate 4 variations (standard Midjourney output)
                variations = []
                for i in range(4):
                    variations.append({
                        "index": i,
                        "url": f"https://midjourney.com/mock/page{page_num}_v{i+1}.png",
                        "task_id": f"task_{page_num}_{i}",
                        "seed": 1000 + (page_num * 10) + i
                    })
                
                illustrations[page_num] = {
                    "prompt": prompt_data["refined"],
                    "variations": variations,
                    "generation_time": "45 seconds",
                    "status": "completed"
                }
                
                progress.update(task, completed=True)
        
        # Display generated images
        for page_num, data in illustrations.items():
            console.print(f"\n[green]✅ Page {page_num}: 4 variations generated[/green]")
            
            # Show image grid (simulated)
            image_grid = Table.grid(padding=1)
            image_grid.add_column()
            image_grid.add_column()
            
            for i in range(0, 4, 2):
                var1 = data["variations"][i]
                var2 = data["variations"][i+1] if i+1 < 4 else None
                
                row = []
                row.append(Panel(
                    f"[cyan]Variation {i+1}[/cyan]\n"
                    f"Seed: {var1['seed']}\n"
                    f"[dim]{var1['url']}[/dim]",
                    title=f"V{i+1}",
                    border_style="blue"
                ))
                
                if var2:
                    row.append(Panel(
                        f"[cyan]Variation {i+2}[/cyan]\n"
                        f"Seed: {var2['seed']}\n"
                        f"[dim]{var2['url']}[/dim]",
                        title=f"V{i+2}",
                        border_style="blue"
                    ))
                
                image_grid.add_row(*row)
            
            console.print(image_grid)
        
        return illustrations
    
    async def evaluate_illustrations(self, illustrations: Dict) -> Dict:
        """Have multiple agents evaluate the illustrations."""
        evaluations = {}
        
        # Define evaluation agents
        agents = [
            {
                "name": "ArtDirectorAgent",
                "criteria": ["composition", "color harmony", "visual appeal"],
                "weight": 0.3
            },
            {
                "name": "ChildPsychologyAgent",
                "criteria": ["age appropriateness", "emotional impact", "engagement"],
                "weight": 0.3
            },
            {
                "name": "CharacterConsistencyAgent",
                "criteria": ["character accuracy", "style consistency", "detail quality"],
                "weight": 0.2
            },
            {
                "name": "StorytellingAgent",
                "criteria": ["narrative support", "mood matching", "scene clarity"],
                "weight": 0.2
            }
        ]
        
        console.print("\n[bold]Agent Evaluation Process:[/bold]")
        
        for page_num, ill_data in illustrations.items():
            console.print(f"\n[cyan]Evaluating Page {page_num}:[/cyan]")
            
            page_evaluations = []
            
            # Each agent evaluates
            for agent in agents:
                agent_scores = []
                
                for i, variation in enumerate(ill_data["variations"]):
                    # Simulate scoring
                    score = self.simulate_agent_scoring(agent["name"], i)
                    agent_scores.append({
                        "variation": i + 1,
                        "score": score,
                        "notes": f"{agent['name']} finds V{i+1} {self.get_score_description(score)}"
                    })
                
                best_pick = max(agent_scores, key=lambda x: x["score"])
                
                page_evaluations.append({
                    "agent": agent["name"],
                    "scores": agent_scores,
                    "best_pick": best_pick["variation"],
                    "confidence": best_pick["score"]
                })
                
                # Display agent's evaluation
                console.print(f"  • [yellow]{agent['name']}[/yellow]: "
                            f"Recommends V{best_pick['variation']} "
                            f"(confidence: {best_pick['score']:.2f})")
            
            # Calculate consensus
            consensus = self.calculate_consensus(page_evaluations)
            evaluations[page_num] = {
                "agent_evaluations": page_evaluations,
                "consensus": consensus,
                "final_choice": consensus["best_variation"]
            }
            
            console.print(f"  [green]✅ Consensus: Variation {consensus['best_variation']} "
                        f"(agreement: {consensus['agreement']:.1%})[/green]")
        
        return evaluations
    
    def simulate_agent_scoring(self, agent_name: str, variation_index: int) -> float:
        """Simulate agent scoring for a variation."""
        # Different agents have different preferences
        base_scores = {
            "ArtDirectorAgent": [0.85, 0.75, 0.90, 0.80],
            "ChildPsychologyAgent": [0.88, 0.92, 0.85, 0.87],
            "CharacterConsistencyAgent": [0.90, 0.85, 0.88, 0.93],
            "StorytellingAgent": [0.87, 0.89, 0.91, 0.86]
        }
        
        return base_scores.get(agent_name, [0.8, 0.8, 0.8, 0.8])[variation_index]
    
    def get_score_description(self, score: float) -> str:
        """Get description for a score."""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.85:
            return "very good"
        elif score >= 0.8:
            return "good"
        elif score >= 0.75:
            return "acceptable"
        else:
            return "needs improvement"
    
    def calculate_consensus(self, evaluations: List[Dict]) -> Dict:
        """Calculate consensus from agent evaluations."""
        # Count votes for each variation
        votes = {}
        for eval in evaluations:
            pick = eval["best_pick"]
            votes[pick] = votes.get(pick, 0) + 1
        
        # Find most voted
        best_variation = max(votes, key=votes.get)
        agreement = votes[best_variation] / len(evaluations)
        
        return {
            "best_variation": best_variation,
            "agreement": agreement,
            "votes": votes,
            "unanimous": agreement == 1.0
        }
    
    async def upscale_best_images(self, evaluations: Dict) -> Dict:
        """Upscale the best images chosen by agents."""
        upscaled = {}
        
        console.print("\n[bold]Upscaling Selected Images:[/bold]")
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Upscaling best selections...", total=len(evaluations))
            
            for page_num, eval_data in evaluations.items():
                best_v = eval_data["final_choice"]
                
                # Simulate upscale
                await asyncio.sleep(1)
                
                upscaled[page_num] = {
                    "original_variation": best_v,
                    "upscaled_url": f"https://midjourney.com/mock/page{page_num}_v{best_v}_upscaled_4k.png",
                    "resolution": "4096x2304",
                    "file_size": "12.5 MB",
                    "enhancement": "2x resolution, enhanced details"
                }
                
                progress.update(task, advance=1)
        
        # Display upscale results
        table = Table(title="Upscaled Illustrations")
        table.add_column("Page", style="cyan")
        table.add_column("Selected", style="green")
        table.add_column("Resolution", style="yellow")
        table.add_column("Enhancement", style="magenta")
        
        for page_num, data in upscaled.items():
            table.add_row(
                str(page_num),
                f"Variation {data['original_variation']}",
                data["resolution"],
                data["enhancement"]
            )
        
        console.print(table)
        
        return upscaled
    
    async def create_alternative_branches(self, evaluations: Dict) -> Dict:
        """Allow agents to create alternative versions."""
        alternatives = {}
        
        console.print("\n[bold]Alternative Branch Creation:[/bold]")
        
        # CharacterConsistencyAgent wants to try alternative for page 7
        if 7 in evaluations:
            console.print("\n[yellow]CharacterConsistencyAgent proposes alternative for Page 7[/yellow]")
            
            reason = (
                "The selected image doesn't fully capture Quacky's signature 'one feather up' feature. "
                "I can generate a version with better character consistency."
            )
            
            console.print(Panel(reason, title="Reason for Alternative", border_style="yellow"))
            
            # New prompt from agent
            new_prompt = (
                "Children's book watercolor, yellow duckling with ONE prominent feather sticking up on head, "
                "comically oversized orange webbed feet tangled in green reeds, inventing the 'Waddle Hop' dance, "
                "exaggerated hopping motion with motion lines, three curious bunnies watching and mimicking, "
                "meadow setting with wildflowers, emphasis on the single upright feather as character trait, "
                "soft watercolor style with clear character details, whimsical and funny --ar 16:9 --v 6 --quality 2"
            )
            
            console.print("[cyan]Alternative Prompt:[/cyan]")
            console.print(Panel(new_prompt, border_style="cyan"))
            
            # Simulate generation
            with Progress() as progress:
                task = progress.add_task("[cyan]Generating alternative...", total=None)
                await asyncio.sleep(2)
                progress.update(task, completed=True)
            
            alternatives[7] = {
                "agent": "CharacterConsistencyAgent",
                "reason": reason,
                "new_prompt": new_prompt,
                "results": [
                    {
                        "url": f"https://midjourney.com/mock/page7_alt_v{i+1}.png",
                        "improvements": ["clearer feather", "better feet proportion", "more dynamic pose"][i]
                    }
                    for i in range(3)
                ],
                "status": "generated"
            }
            
            # Agent evaluation of alternative
            console.print("[green]✅ Alternative generated successfully[/green]")
            console.print("Agent's self-evaluation: [green]92% character accuracy (vs 88% original)[/green]")
        
        # StorytellingAgent wants alternative for page 1
        if 1 in evaluations:
            console.print("\n[yellow]StorytellingAgent proposes alternative for Page 1[/yellow]")
            
            reason = (
                "The opening scene should immediately show Quacky's belly-flop for comedic impact. "
                "Current image is too static."
            )
            
            console.print(Panel(reason, title="Reason for Alternative", border_style="yellow"))
            
            alternatives[1] = {
                "agent": "StorytellingAgent",
                "reason": reason,
                "status": "proposed",
                "awaiting": "approval"
            }
        
        return alternatives
    
    async def finalize_illustrations(self, upscaled: Dict, alternatives: Dict) -> Dict:
        """Finalize illustration selections."""
        final_selections = {}
        
        console.print("\n[bold]Final Selection Process:[/bold]")
        
        # Review each page
        for page_num in [1, 7, 9]:
            if page_num in alternatives and alternatives[page_num]["status"] == "generated":
                # Compare original vs alternative
                console.print(f"\n[cyan]Page {page_num}: Comparing versions[/cyan]")
                
                comparison = Table.grid(padding=1)
                comparison.add_column()
                comparison.add_column()
                
                comparison.add_row(
                    Panel(
                        "[green]Original (Upscaled)[/green]\n"
                        f"Selected by consensus\n"
                        f"Agreement: 75%\n"
                        f"[dim]{upscaled[page_num]['upscaled_url']}[/dim]",
                        border_style="green"
                    ),
                    Panel(
                        "[yellow]Alternative[/yellow]\n"
                        f"Proposed by {alternatives[page_num]['agent']}\n"
                        f"Improvement: Character accuracy\n"
                        f"[dim]{alternatives[page_num]['results'][0]['url']}[/dim]",
                        border_style="yellow"
                    )
                )
                
                console.print(comparison)
                
                # Final decision (simulate)
                if page_num == 7:
                    final_selections[page_num] = {
                        "selected": "alternative",
                        "url": alternatives[page_num]['results'][0]['url'],
                        "reason": "Superior character consistency"
                    }
                    console.print("[green]✅ Alternative selected for page 7[/green]")
                else:
                    final_selections[page_num] = {
                        "selected": "original",
                        "url": upscaled[page_num]['upscaled_url'],
                        "reason": "Original maintains story flow"
                    }
                    console.print("[blue]✅ Original retained[/blue]")
            else:
                final_selections[page_num] = {
                    "selected": "original",
                    "url": upscaled.get(page_num, {}).get('upscaled_url', 'pending'),
                    "reason": "Consensus choice"
                }
        
        return final_selections
    
    async def display_summary(self, final_selections: Dict):
        """Display final summary of the illustration workflow."""
        
        console.print("\n" + "="*60)
        console.print(Panel(
            "[bold green]📚 Illustration Workflow Complete[/bold green]\n\n"
            "[yellow]Quacky McWaddles' Big Adventure[/yellow]\n"
            "Illustrated Edition Ready",
            border_style="green"
        ))
        
        # Workflow metrics
        metrics = Table(title="Workflow Metrics")
        metrics.add_column("Metric", style="cyan")
        metrics.add_column("Value", style="yellow")
        
        metrics.add_row("Total Pages Illustrated", "3 (demo)")
        metrics.add_row("Prompts Refined", "3")
        metrics.add_row("Images Generated", "12")
        metrics.add_row("Agent Evaluations", "12")
        metrics.add_row("Images Upscaled", "3")
        metrics.add_row("Alternative Branches", "2")
        metrics.add_row("Final Selections", "3")
        
        console.print(metrics)
        
        # Knowledge Graph storage
        console.print("\n[bold]Knowledge Graph Storage:[/bold]")
        
        kg_tree = Tree("📊 Workflow in Knowledge Graph")
        
        prompts_node = kg_tree.add("📝 Prompts (3 pages)")
        prompts_node.add("[green]Base prompts stored[/green]")
        prompts_node.add("[green]Refined prompts stored[/green]")
        
        illustrations_node = kg_tree.add("🎨 Illustrations (12 generated)")
        illustrations_node.add("[green]Generation metadata stored[/green]")
        illustrations_node.add("[green]Image URLs stored[/green]")
        
        evaluations_node = kg_tree.add("👥 Evaluations (4 agents)")
        evaluations_node.add("[green]Individual scores stored[/green]")
        evaluations_node.add("[green]Consensus decisions stored[/green]")
        
        alternatives_node = kg_tree.add("🌿 Alternative Branches (2)")
        alternatives_node.add("[yellow]CharacterConsistencyAgent branch[/yellow]")
        alternatives_node.add("[yellow]StorytellingAgent proposal[/yellow]")
        
        final_node = kg_tree.add("✅ Final Selections (3)")
        final_node.add("[green]Page 1: Original upscaled[/green]")
        final_node.add("[yellow]Page 7: Alternative selected[/yellow]")
        final_node.add("[green]Page 9: Original upscaled[/green]")
        
        console.print(kg_tree)
        
        # SPARQL query example
        console.print("\n[bold]Sample SPARQL Query:[/bold]")
        sparql = Panel(
            """PREFIX ill: <http://example.org/illustration#>
PREFIX wf: <http://example.org/workflow#>

# Find all alternative branches and their reasons
SELECT ?page ?agent ?reason ?selected
WHERE {
    ?branch ill:type "AlternativeBranch" .
    ?branch ill:forPage ?page .
    ?branch ill:proposedBy ?agent .
    ?branch ill:reason ?reason .
    OPTIONAL { ?branch ill:selected ?selected }
}
ORDER BY ?page""",
            title="Query Alternative Branches",
            border_style="dim"
        )
        console.print(sparql)
        
        # Final message
        console.print("\n[bold green]✨ Complete Illustrated Book Ready![/bold green]")
        console.print(
            "[dim]• All prompts refined by Planner agent[/dim]\n"
            "[dim]• Images evaluated by 4 specialized agents[/dim]\n"
            "[dim]• Best selections upscaled to 4K resolution[/dim]\n"
            "[dim]• Alternative versions created where needed[/dim]\n"
            "[dim]• Full audit trail in Knowledge Graph[/dim]"
        )
        
        console.print("\n[italic]'Waddle-waddle-SPLAT! Now with pictures!'[/italic] - Quacky McWaddles 🦆")


async def main():
    """Run the illustration demonstration."""
    demo = IllustrationDemo()
    await demo.run_complete_demonstration()


if __name__ == "__main__":
    asyncio.run(main())
