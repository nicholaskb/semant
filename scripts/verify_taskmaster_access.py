#!/usr/bin/env python3
"""
Verify TaskMaster Access for Agents

This script demonstrates that all agents can access TaskMaster tasks
and query them for coordination.

Date: 2025-01-08
"""

from agents.tools.taskmaster_accessor import get_taskmaster_accessor
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def main():
    """Demonstrate TaskMaster access."""
    console.print()
    console.print("=" * 70, style="bold blue")
    console.print("  TaskMaster Agent Access Verification", style="bold blue")
    console.print("=" * 70, style="bold blue")
    console.print()
    
    # Get accessor
    tm = get_taskmaster_accessor()
    console.print("✅ TaskMasterAccessor initialized", style="green")
    console.print()
    
    # Get all tasks
    all_tasks = tm.get_all_tasks()
    console.print(f"📋 Total tasks in TaskMaster: {len(all_tasks)}", style="cyan")
    console.print()
    
    # Get children's book tasks (IDs 100-112)
    book_tasks = [t for t in all_tasks if 100 <= t['id'] <= 112]
    console.print(f"📚 Children's Book Tasks: {len(book_tasks)}", style="cyan")
    console.print()
    
    # Show task summary table
    table = Table(title="Children's Book Generation Tasks", show_header=True)
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Title", style="white", width=40)
    table.add_column("Status", style="yellow", width=12)
    table.add_column("Priority", style="magenta", width=8)
    table.add_column("Dependencies", style="blue", width=15)
    
    for task in sorted(book_tasks, key=lambda t: t['id']):
        status_style = {
            "done": "green",
            "in-progress": "yellow",
            "pending": "white",
            "blocked": "red"
        }.get(task['status'], "white")
        
        deps = ", ".join(map(str, task.get('dependencies', []))) or "None"
        
        table.add_row(
            str(task['id']),
            task['title'][:38] + "..." if len(task['title']) > 38 else task['title'],
            f"[{status_style}]{task['status']}[/{status_style}]",
            task['priority'],
            deps
        )
    
    console.print(table)
    console.print()
    
    # Check task progress
    progress = tm.get_task_progress()
    
    progress_panel = Panel(
        f"""[cyan]Total Tasks:[/cyan] {progress['total']}
[green]Done:[/green] {progress['done']}
[yellow]In Progress:[/yellow] {progress['in_progress']}
[white]Pending:[/white] {progress['pending']}
[red]Blocked:[/red] {progress['blocked']}
[bold cyan]Completion:[/bold cyan] {progress['completion_percentage']:.1f}%""",
        title="📊 Overall Progress",
        border_style="blue"
    )
    console.print(progress_panel)
    console.print()
    
    # Get ready tasks
    ready_tasks = tm.get_ready_tasks()
    console.print(f"✅ Ready Tasks (no pending dependencies): {len(ready_tasks)}", style="green")
    console.print()
    
    # Show next task
    next_task = tm.get_next_task()
    if next_task:
        console.print(Panel(
            tm.format_task_summary(next_task),
            title="🎯 Next Task to Work On",
            border_style="green"
        ))
        console.print()
        
        # Show dependency chain
        chain = tm.get_dependency_chain(next_task['id'])
        console.print(f"📊 Dependency Chain for Task {next_task['id']}:", style="cyan")
        console.print(f"   {' → '.join(map(str, chain))}")
        console.print()
    
    # Show task 100 details (first children's book task)
    task_100 = tm.get_task_by_id(100)
    if task_100:
        console.print(Panel(
            f"""[bold]{task_100['title']}[/bold]

[cyan]Description:[/cyan]
{task_100['description']}

[cyan]Status:[/cyan] {task_100['status']}
[cyan]Priority:[/cyan] {task_100['priority']}
[cyan]Dependencies:[/cyan] {task_100.get('dependencies', []) or 'None'}

[green]✅ This task is ready to start![/green]""",
            title=f"Task {task_100['id']} - First Children's Book Task",
            border_style="yellow"
        ))
        console.print()
    
    # Demonstrate agent coordination
    console.print("=" * 70, style="bold blue")
    console.print("  Agent Coordination Example", style="bold blue")
    console.print("=" * 70, style="bold blue")
    console.print()
    
    console.print("[cyan]Example 1: Check if Task 101 is ready[/cyan]")
    task_101 = tm.get_task_by_id(101)
    if task_101:
        deps_satisfied = tm.are_dependencies_satisfied(101)
        console.print(f"   Task 101: {task_101['title']}")
        console.print(f"   Dependencies: {task_101.get('dependencies', [])}")
        console.print(f"   Dependencies Satisfied: {deps_satisfied}")
        if not deps_satisfied:
            console.print("   ⚠️  Task 101 is BLOCKED until Task 100 completes", style="yellow")
        console.print()
    
    console.print("[cyan]Example 2: Find all image-related tasks[/cyan]")
    image_tasks = [
        t for t in book_tasks 
        if 'image' in t['title'].lower()
    ]
    console.print(f"   Found {len(image_tasks)} image-related tasks:")
    for t in image_tasks:
        console.print(f"      • Task {t['id']}: {t['title']}")
    console.print()
    
    console.print("[cyan]Example 3: Query tasks by status[/cyan]")
    pending = tm.get_tasks_by_status("pending")
    book_pending = [t for t in pending if 100 <= t['id'] <= 112]
    console.print(f"   Children's book tasks pending: {len(book_pending)}")
    console.print()
    
    # Success summary
    console.print("=" * 70, style="bold green")
    console.print("  ✅ TaskMaster Access Verified!", style="bold green")
    console.print("=" * 70, style="bold green")
    console.print()
    console.print("All agents can now access TaskMaster tasks via:", style="green")
    console.print("   from agents.tools.taskmaster_accessor import get_taskmaster_accessor", style="cyan")
    console.print()
    console.print("Next steps:", style="yellow")
    console.print("   1. Implement Task 100 (KG Schema)")
    console.print("   2. Build orchestrator to coordinate agents")
    console.print("   3. Have agents check dependencies before executing")
    console.print()


if __name__ == "__main__":
    main()

