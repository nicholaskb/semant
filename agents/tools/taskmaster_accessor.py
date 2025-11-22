"""
TaskMaster Accessor for Agent Collaboration

This module provides agents with read-only access to TaskMaster tasks.
All agents can query task state, dependencies, and status through this interface.

Date: 2025-01-08
Purpose: Enable agents to coordinate work based on TaskMaster task definitions
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger
from datetime import datetime


class TaskMasterAccessor:
    """
    Provides agents with access to TaskMaster task data.
    
    Features:
    - Read task definitions and status
    - Query tasks by ID, status, or tag
    - Check dependencies and readiness
    - Monitor task progress
    
    Note: This is READ-ONLY access. Agents cannot modify TaskMaster tasks directly.
    Use the task-master CLI or MCP tools for task updates.
    """
    
    def __init__(self, tasks_file: Optional[Path] = None):
        """
        Initialize the TaskMaster accessor.
        
        Args:
            tasks_file: Path to tasks.json file. If None, auto-detects from .taskmaster/
        """
        if tasks_file is None:
            # Auto-detect tasks.json
            project_root = Path.cwd()
            tasks_file = project_root / ".taskmaster" / "tasks" / "tasks.json"
        
        self.tasks_file = Path(tasks_file)
        self.logger = logger.bind(component="TaskMasterAccessor")
        
        if not self.tasks_file.exists():
            self.logger.warning(f"TaskMaster tasks file not found: {self.tasks_file}")
            self.tasks_data = {"master": {"tasks": []}}
        else:
            self._load_tasks()
    
    def _load_tasks(self) -> None:
        """Load tasks from the tasks.json file."""
        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                self.tasks_data = json.load(f)
            self.logger.debug(f"Loaded tasks from {self.tasks_file}")
        except Exception as e:
            self.logger.error(f"Failed to load tasks: {e}")
            self.tasks_data = {"master": {"tasks": []}}
    
    def refresh(self) -> None:
        """Reload tasks from disk (call when tasks are updated externally)."""
        self._load_tasks()
    
    def get_all_tasks(self, tag: str = "master") -> List[Dict[str, Any]]:
        """
        Get all tasks for a specific tag.
        
        Args:
            tag: The tag context (default: "master")
        
        Returns:
            List of task dictionaries
        """
        if tag not in self.tasks_data:
            self.logger.warning(f"Tag '{tag}' not found in TaskMaster")
            return []
        
        return self.tasks_data[tag].get("tasks", [])
    
    def get_task_by_id(self, task_id: int, tag: str = "master") -> Optional[Dict[str, Any]]:
        """
        Get a specific task by ID.
        
        Args:
            task_id: The task ID
            tag: The tag context
        
        Returns:
            Task dictionary or None if not found
        """
        tasks = self.get_all_tasks(tag)
        for task in tasks:
            if task.get("id") == task_id:
                return task
        
        self.logger.debug(f"Task {task_id} not found in tag '{tag}'")
        return None
    
    def get_tasks_by_status(self, status: str, tag: str = "master") -> List[Dict[str, Any]]:
        """
        Get all tasks with a specific status.
        
        Args:
            status: The task status (e.g., "pending", "done", "in-progress")
            tag: The tag context
        
        Returns:
            List of matching tasks
        """
        tasks = self.get_all_tasks(tag)
        return [t for t in tasks if t.get("status") == status]
    
    def get_ready_tasks(self, tag: str = "master") -> List[Dict[str, Any]]:
        """
        Get all tasks that are ready to work on (pending with satisfied dependencies).
        
        Args:
            tag: The tag context
        
        Returns:
            List of ready tasks
        """
        tasks = self.get_all_tasks(tag)
        pending_tasks = [t for t in tasks if t.get("status") == "pending"]
        
        ready = []
        for task in pending_tasks:
            if self.are_dependencies_satisfied(task["id"], tag):
                ready.append(task)
        
        return ready
    
    def are_dependencies_satisfied(self, task_id: int, tag: str = "master") -> bool:
        """
        Check if all dependencies for a task are satisfied (status='done').
        
        Args:
            task_id: The task ID to check
            tag: The tag context
        
        Returns:
            True if all dependencies are done, False otherwise
        """
        task = self.get_task_by_id(task_id, tag)
        if not task:
            return False
        
        dependencies = task.get("dependencies", [])
        if not dependencies:
            return True
        
        tasks = self.get_all_tasks(tag)
        task_map = {t["id"]: t for t in tasks}
        
        for dep_id in dependencies:
            dep_task = task_map.get(dep_id)
            if not dep_task or dep_task.get("status") != "done":
                return False
        
        return True
    
    def get_task_progress(self, tag: str = "master") -> Dict[str, Any]:
        """
        Get overall progress statistics for a tag.
        
        Args:
            tag: The tag context
        
        Returns:
            Dictionary with progress metrics
        """
        tasks = self.get_all_tasks(tag)
        if not tasks:
            return {
                "total": 0,
                "done": 0,
                "in_progress": 0,
                "pending": 0,
                "blocked": 0,
                "completion_percentage": 0.0
            }
        
        status_counts = {}
        for task in tasks:
            status = task.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        total = len(tasks)
        done = status_counts.get("done", 0)
        in_progress = status_counts.get("in-progress", 0)
        pending = status_counts.get("pending", 0)
        
        # Count blocked tasks (pending with unsatisfied dependencies)
        blocked = 0
        for task in self.get_tasks_by_status("pending", tag):
            if not self.are_dependencies_satisfied(task["id"], tag):
                blocked += 1
        
        return {
            "total": total,
            "done": done,
            "in_progress": in_progress,
            "pending": pending,
            "blocked": blocked,
            "completion_percentage": (done / total * 100) if total > 0 else 0.0,
            "status_breakdown": status_counts
        }
    
    def get_next_task(self, tag: str = "master") -> Optional[Dict[str, Any]]:
        """
        Get the next task to work on (highest priority ready task).
        
        Args:
            tag: The tag context
        
        Returns:
            Next task to work on, or None if no ready tasks
        """
        ready_tasks = self.get_ready_tasks(tag)
        if not ready_tasks:
            return None
        
        # Sort by priority (high > medium > low) and then by ID
        priority_order = {"high": 0, "medium": 1, "low": 2}
        
        sorted_tasks = sorted(
            ready_tasks,
            key=lambda t: (
                priority_order.get(t.get("priority", "medium"), 1),
                t.get("id", 999)
            )
        )
        
        return sorted_tasks[0] if sorted_tasks else None
    
    def get_dependency_chain(self, task_id: int, tag: str = "master") -> List[int]:
        """
        Get the full dependency chain for a task (recursive).
        
        Args:
            task_id: The task ID
            tag: The tag context
        
        Returns:
            List of task IDs in dependency order
        """
        visited = set()
        chain = []
        
        def _traverse(tid: int):
            if tid in visited:
                return
            
            task = self.get_task_by_id(tid, tag)
            if not task:
                return
            
            visited.add(tid)
            
            # First add dependencies
            for dep_id in task.get("dependencies", []):
                _traverse(dep_id)
            
            # Then add this task
            chain.append(tid)
        
        _traverse(task_id)
        return chain
    
    def format_task_summary(self, task: Dict[str, Any]) -> str:
        """
        Format a task as a human-readable summary.
        
        Args:
            task: Task dictionary
        
        Returns:
            Formatted string
        """
        status_emoji = {
            "done": "✅",
            "in-progress": "🔄",
            "pending": "⏳",
            "blocked": "🚫"
        }
        
        status = task.get("status", "unknown")
        emoji = status_emoji.get(status, "❓")
        
        deps = task.get("dependencies", [])
        deps_str = f" [deps: {', '.join(map(str, deps))}]" if deps else ""
        
        return (
            f"{emoji} Task {task['id']}: {task.get('title', 'Untitled')}\n"
            f"   Status: {status} | Priority: {task.get('priority', 'medium')}{deps_str}\n"
            f"   Description: {task.get('description', 'No description')[:100]}"
        )
    
    def get_available_tags(self) -> List[str]:
        """
        Get all available tag contexts.
        
        Returns:
            List of tag names
        """
        return list(self.tasks_data.keys())


# Singleton instance for convenient access
_accessor_instance: Optional[TaskMasterAccessor] = None


def get_taskmaster_accessor() -> TaskMasterAccessor:
    """
    Get or create the global TaskMaster accessor instance.
    
    Returns:
        TaskMasterAccessor instance
    """
    global _accessor_instance
    if _accessor_instance is None:
        _accessor_instance = TaskMasterAccessor()
    return _accessor_instance


# Example usage for agents:
"""
# In any agent:
from agents.tools.taskmaster_accessor import get_taskmaster_accessor

class MyAgent(BaseAgent):
    async def process_message(self, message):
        # Access TaskMaster tasks
        tm = get_taskmaster_accessor()
        
        # Get next task to work on
        next_task = tm.get_next_task()
        if next_task:
            self.logger.info(f"Working on: {tm.format_task_summary(next_task)}")
        
        # Check task progress
        progress = tm.get_task_progress()
        self.logger.info(f"Overall progress: {progress['completion_percentage']:.1f}%")
        
        # Find specific tasks
        image_tasks = [t for t in tm.get_all_tasks() if 'image' in t.get('title', '').lower()]
"""

