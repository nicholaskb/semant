#!/usr/bin/env python3
"""
Monitor and Report on Book Creation Progress

This script monitors the book creation workflow and generates detailed reports
on what the code is actually doing at each step.
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.text import Text

from kg.models.graph_manager import KnowledgeGraphManager

console = Console()

class BookCreationMonitor:
    """Monitors book creation workflow and generates reports."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.log_entries = []
        self.start_time = None
        self.kg_manager = None
        
    async def initialize(self):
        """Initialize monitoring."""
        self.kg_manager = KnowledgeGraphManager(persistent_storage=True)
        await self.kg_manager.initialize()
        self.start_time = time.time()
        
    async def monitor_workflow(self) -> Dict[str, Any]:
        """Monitor the workflow by querying KG."""
        console.print("[cyan]🔍 Monitoring book creation workflow...[/cyan]\n")
        
        # Query KG for project context
        project_uri = f"http://example.org/project/{self.project_id}"
        
        query = f"""
        PREFIX core: <http://example.org/core#>
        PREFIX project: <http://example.org/project/>
        
        SELECT ?step ?name ?status ?result ?timestamp WHERE {{
            <{project_uri}> core:hasWorkflowStep ?step .
            ?step core:stepName ?name .
            ?step core:stepStatus ?status .
            OPTIONAL {{ ?step core:stepResult ?result }}
            OPTIONAL {{ ?step core:stepTimestamp ?timestamp }}
        }}
        ORDER BY ?timestamp
        """
        
        steps = await self.kg_manager.query_graph(query)
        
        # Query for agent diary entries
        diary_query = f"""
        PREFIX core: <http://example.org/core#>
        PREFIX agent: <http://example.org/agent/>
        
        SELECT ?agent ?message ?timestamp ?details WHERE {{
            ?agent core:hasDiaryEntry ?entry .
            ?entry core:message ?message .
            ?entry core:timestamp ?timestamp .
            OPTIONAL {{ ?entry core:details ?details }}
        }}
        ORDER BY DESC(?timestamp)
        LIMIT 50
        """
        
        diary_entries = await self.kg_manager.query_graph(diary_query)
        
        # Query for agent messages/notes
        messages_query = f"""
        PREFIX core: <http://example.org/core#>
        PREFIX project: <http://example.org/project/>
        
        SELECT ?message ?type ?content ?sender ?timestamp WHERE {{
            ?message core:relatedToProject <{project_uri}> .
            ?message core:messageType ?type .
            ?message core:content ?content .
            ?message core:sender ?sender .
            ?message core:timestamp ?timestamp .
        }}
        ORDER BY DESC(?timestamp)
        LIMIT 20
        """
        
        messages = await self.kg_manager.query_graph(messages_query)
        
        return {
            "workflow_steps": steps,
            "diary_entries": diary_entries,
            "messages": messages,
            "project_id": self.project_id,
            "monitoring_time": time.time() - self.start_time
        }
    
    def generate_report(self, data: Dict[str, Any]) -> str:
        """Generate detailed report on what the code is doing."""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("BOOK CREATION WORKFLOW MONITORING REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().isoformat()}")
        report_lines.append(f"Project ID: {data['project_id']}")
        report_lines.append(f"Monitoring Duration: {data['monitoring_time']:.2f} seconds")
        report_lines.append("")
        
        # Workflow Steps Analysis
        report_lines.append("=" * 80)
        report_lines.append("WORKFLOW STEPS ANALYSIS")
        report_lines.append("=" * 80)
        
        steps = data.get("workflow_steps", [])
        if steps:
            for step in steps:
                step_name = step.get("name", "unknown")
                status = step.get("status", "unknown")
                timestamp = step.get("timestamp", "unknown")
                
                report_lines.append(f"\nStep: {step_name}")
                report_lines.append(f"  Status: {status}")
                report_lines.append(f"  Timestamp: {timestamp}")
                
                # Parse result if available
                result = step.get("result", "")
                if result:
                    try:
                        result_data = json.loads(result)
                        report_lines.append(f"  Result: {json.dumps(result_data, indent=4)}")
                    except:
                        report_lines.append(f"  Result: {result[:200]}...")
        else:
            report_lines.append("\nNo workflow steps found in KG yet.")
        
        # Diary Entries Analysis
        report_lines.append("\n" + "=" * 80)
        report_lines.append("AGENT DIARY ENTRIES")
        report_lines.append("=" * 80)
        
        diary_entries = data.get("diary_entries", [])
        if diary_entries:
            for entry in diary_entries[:20]:  # Limit to 20 most recent
                agent = entry.get("agent", "unknown")
                message = entry.get("message", "")
                timestamp = entry.get("timestamp", "unknown")
                
                report_lines.append(f"\nAgent: {agent}")
                report_lines.append(f"  Time: {timestamp}")
                report_lines.append(f"  Message: {message[:200]}...")
        else:
            report_lines.append("\nNo diary entries found yet.")
        
        # Messages Analysis
        report_lines.append("\n" + "=" * 80)
        report_lines.append("INTER-AGENT MESSAGES")
        report_lines.append("=" * 80)
        
        messages = data.get("messages", [])
        if messages:
            for msg in messages:
                msg_type = msg.get("type", "unknown")
                sender = msg.get("sender", "unknown")
                timestamp = msg.get("timestamp", "unknown")
                content = msg.get("content", "")
                
                report_lines.append(f"\nType: {msg_type}")
                report_lines.append(f"  From: {sender}")
                report_lines.append(f"  Time: {timestamp}")
                try:
                    content_data = json.loads(content)
                    report_lines.append(f"  Content: {json.dumps(content_data, indent=4)}")
                except:
                    report_lines.append(f"  Content: {content[:200]}...")
        else:
            report_lines.append("\nNo inter-agent messages found yet.")
        
        report_lines.append("\n" + "=" * 80)
        report_lines.append("END OF REPORT")
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)
    
    def analyze_code_behavior(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze what the code is actually doing."""
        analysis = {
            "phases_completed": [],
            "phases_in_progress": [],
            "phases_pending": [],
            "agents_active": set(),
            "key_actions": [],
            "issues": []
        }
        
        steps = data.get("workflow_steps", [])
        
        for step in steps:
            step_name = step.get("name", "")
            status = step.get("status", "")
            
            if status == "completed":
                analysis["phases_completed"].append(step_name)
            elif status == "in_progress":
                analysis["phases_in_progress"].append(step_name)
            else:
                analysis["phases_pending"].append(step_name)
            
            # Extract key actions from step names
            if "research" in step_name.lower():
                analysis["key_actions"].append("Scientific research phase")
            elif "story" in step_name.lower():
                analysis["key_actions"].append("Story writing phase")
            elif "image" in step_name.lower():
                analysis["key_actions"].append("Image generation/selection phase")
            elif "judgment" in step_name.lower():
                analysis["key_actions"].append("Image judgment phase")
            elif "review" in step_name.lower():
                analysis["key_actions"].append("McKinsey review phase")
        
        # Extract active agents from diary entries
        diary_entries = data.get("diary_entries", [])
        for entry in diary_entries:
            agent = entry.get("agent", "")
            if agent:
                analysis["agents_active"].add(agent)
        
        analysis["agents_active"] = list(analysis["agents_active"])
        
        return analysis

async def main():
    """Main monitoring function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor book creation workflow")
    parser.add_argument("--project-id", required=True, help="Project ID to monitor")
    parser.add_argument("--output", help="Output file for report (default: stdout)")
    parser.add_argument("--watch", action="store_true", help="Watch mode (continuous monitoring)")
    args = parser.parse_args()
    
    monitor = BookCreationMonitor(args.project_id)
    await monitor.initialize()
    
    if args.watch:
        console.print("[cyan]👀 Watching workflow progress...[/cyan]")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        
        try:
            with Live(console=console, refresh_per_second=2) as live:
                while True:
                    data = await monitor.monitor_workflow()
                    analysis = monitor.analyze_code_behavior(data)
                    
                    # Create live display
                    table = Table(title=f"Project: {args.project_id}")
                    table.add_column("Phase", style="cyan")
                    table.add_column("Status", style="green")
                    
                    for step in data.get("workflow_steps", []):
                        table.add_row(
                            step.get("name", "unknown"),
                            step.get("status", "unknown")
                        )
                    
                    live.update(table)
                    await asyncio.sleep(2)
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped[/yellow]")
    else:
        # Single monitoring run
        data = await monitor.monitor_workflow()
        analysis = monitor.analyze_code_behavior(data)
        
        # Generate report
        report = monitor.generate_report(data)
        
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(report)
            console.print(f"[green]✅ Report saved to: {output_path}[/green]")
        else:
            console.print(Panel(report, title="Monitoring Report", border_style="cyan"))
        
        # Display analysis
        console.print("\n[bold cyan]CODE BEHAVIOR ANALYSIS[/bold cyan]\n")
        
        analysis_table = Table()
        analysis_table.add_column("Category", style="cyan")
        analysis_table.add_column("Details", style="yellow")
        
        analysis_table.add_row("Phases Completed", str(len(analysis["phases_completed"])))
        analysis_table.add_row("Phases In Progress", str(len(analysis["phases_in_progress"])))
        analysis_table.add_row("Phases Pending", str(len(analysis["phases_pending"])))
        analysis_table.add_row("Active Agents", str(len(analysis["agents_active"])))
        analysis_table.add_row("Key Actions", ", ".join(analysis["key_actions"][:5]))
        
        console.print(analysis_table)

if __name__ == "__main__":
    asyncio.run(main())

