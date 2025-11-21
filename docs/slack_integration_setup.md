# Slack Integration Setup Guide

## Current Status: Not Yet Implemented ⚠️

The Slack integration is **planned** but **not yet built**. This guide shows you:
1. How to view tasks **right now** (without Slack)
2. How to implement the Slack integration (Task 17)
3. What it will look like once implemented

---

## Viewing Tasks Right Now (Current Options)

### Option 1: TaskMaster CLI (Recommended)

```bash
# List all tasks
task-master list

# Show next task to work on
task-master next

# Show specific task details
task-master show 16

# List tasks by status
task-master list --status pending
task-master list --status in-progress
task-master list --status done

# List tasks with subtasks
task-master list --with-subtasks
```

### Option 2: View TaskMaster JSON Directly

```bash
# View all tasks
cat .taskmaster/tasks/tasks.json | python -m json.tool

# Or use jq if installed
cat .taskmaster/tasks/tasks.json | jq '.master.tasks[] | {id, title, status, priority}'
```

### Option 3: TaskMaster MCP Tools (If Available in Cursor)

Use the MCP tools:
- `get_tasks` - List all tasks
- `next_task` - Get next task
- `get_task` - Get specific task details

---

## Implementing Slack Integration (Task 17)

### Step 1: Create Slack App

1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: "Semant TaskMaster Bot"
4. Workspace: Select your workspace
5. Click "Create App"

### Step 2: Configure Slack App Permissions

**Bot Token Scopes** (OAuth & Permissions):
- `chat:write` - Send messages
- `chat:write.public` - Send messages to channels
- `commands` - Add slash commands
- `channels:read` - View channel information
- `channels:history` - Read channel messages

**Event Subscriptions** (Subscribe to bot events):
- `message.channels` - Listen to channel messages
- `app_mention` - Listen for @mentions

### Step 3: Install App to Workspace

1. Go to "Install App" in sidebar
2. Click "Install to Workspace"
3. Authorize permissions
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### Step 4: Create Slack Integration Module

Create `integrations/slack_integration.py`:

```python
"""
Slack integration for TaskMaster task monitoring.

This module provides:
- Task status change notifications
- Daily/weekly progress summaries
- Slack slash commands for task queries
- System health monitoring
"""

import os
import json
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from loguru import logger

# Import TaskMaster (adjust import path as needed)
# from taskmaster import TaskMaster  # or however you import it


class SlackTaskMonitor:
    """Monitor TaskMaster tasks and send updates to Slack."""
    
    def __init__(self, slack_token: str, channel: str = "#semant-tasks"):
        """
        Initialize Slack integration.
        
        Args:
            slack_token: Slack Bot User OAuth Token (xoxb-...)
            channel: Slack channel to post updates to
        """
        self.client = WebClient(token=slack_token)
        self.channel = channel
        self.taskmaster = None  # Will be initialized with TaskMaster instance
        
    async def initialize(self, taskmaster_instance):
        """Initialize with TaskMaster instance."""
        self.taskmaster = taskmaster_instance
        
    async def notify_task_status_change(self, task_id: int, old_status: str, new_status: str, task_title: str):
        """Send notification when task status changes."""
        emoji = {
            "pending": "⏳",
            "in-progress": "🔄",
            "done": "✅",
            "blocked": "🚫",
            "cancelled": "❌"
        }.get(new_status, "📝")
        
        message = f"{emoji} *Task {task_id}*: {task_title}\n"
        message += f"Status changed: `{old_status}` → `{new_status}`"
        
        try:
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=message,
                mrkdwn=True
            )
            logger.info(f"Sent Slack notification for task {task_id}")
            return response
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return None
    
    async def send_daily_summary(self):
        """Send daily progress summary to Slack."""
        if not self.taskmaster:
            logger.error("TaskMaster not initialized")
            return
            
        # Get task statistics (adjust based on your TaskMaster API)
        # tasks = await self.taskmaster.get_tasks()
        # stats = self._calculate_stats(tasks)
        
        # For now, placeholder implementation
        stats = {
            "total": 0,
            "pending": 0,
            "in_progress": 0,
            "done": 0,
            "completed_today": 0
        }
        
        message = "📊 *Daily Task Summary*\n\n"
        message += f"• Total tasks: {stats['total']}\n"
        message += f"• Pending: {stats['pending']}\n"
        message += f"• In Progress: {stats['in_progress']}\n"
        message += f"• Completed: {stats['done']}\n"
        message += f"• Completed Today: {stats['completed_today']}\n"
        
        try:
            self.client.chat_postMessage(
                channel=self.channel,
                text=message,
                mrkdwn=True
            )
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
    
    async def handle_slash_command(self, command: str, text: str, user_id: str) -> Dict:
        """
        Handle Slack slash commands.
        
        Commands:
        - /tasks list - List all tasks
        - /tasks show <id> - Show task details
        - /tasks next - Show next task
        - /tasks status <status> - Filter by status
        """
        if not self.taskmaster:
            return {"text": "TaskMaster not initialized"}
        
        parts = text.strip().split() if text else []
        subcommand = parts[0] if parts else "help"
        
        if subcommand == "list":
            # Get all tasks
            # tasks = await self.taskmaster.get_tasks()
            # Format and return task list
            return {
                "text": "📋 *All Tasks*\n\n(Implementation needed - connect to TaskMaster API)",
                "mrkdwn": True
            }
        
        elif subcommand == "show" and len(parts) > 1:
            task_id = parts[1]
            # task = await self.taskmaster.get_task(task_id)
            # Format and return task details
            return {
                "text": f"📝 *Task {task_id}*\n\n(Implementation needed - connect to TaskMaster API)",
                "mrkdwn": True
            }
        
        elif subcommand == "next":
            # next_task = await self.taskmaster.get_next_task()
            # Format and return next task
            return {
                "text": "➡️ *Next Task*\n\n(Implementation needed - connect to TaskMaster API)",
                "mrkdwn": True
            }
        
        elif subcommand == "status" and len(parts) > 1:
            status = parts[1]
            # tasks = await self.taskmaster.get_tasks(status=status)
            # Format and return filtered tasks
            return {
                "text": f"📊 *Tasks with status: {status}*\n\n(Implementation needed)",
                "mrkdwn": True
            }
        
        else:
            return {
                "text": """*TaskMaster Slack Commands*

`/tasks list` - List all tasks
`/tasks show <id>` - Show task details
`/tasks next` - Show next task to work on
`/tasks status <status>` - Filter by status (pending, in-progress, done)

Example: `/tasks show 16`""",
                "mrkdwn": True
            }
    
    def _calculate_stats(self, tasks: List[Dict]) -> Dict:
        """Calculate task statistics."""
        stats = {
            "total": len(tasks),
            "pending": 0,
            "in_progress": 0,
            "done": 0,
            "completed_today": 0
        }
        
        today = datetime.now().date()
        
        for task in tasks:
            status = task.get("status", "pending")
            if status == "pending":
                stats["pending"] += 1
            elif status == "in-progress":
                stats["in_progress"] += 1
            elif status == "done":
                stats["done"] += 1
                # Check if completed today (would need timestamp in task)
                # if task.get("completed_at") and task["completed_at"].date() == today:
                #     stats["completed_today"] += 1
        
        return stats


class SlackWebhookReceiver:
    """Receive and process Slack webhook events."""
    
    def __init__(self, slack_token: str, task_monitor: SlackTaskMonitor):
        self.client = WebClient(token=slack_token)
        self.task_monitor = task_monitor
    
    async def handle_event(self, event_data: Dict):
        """Handle incoming Slack event."""
        event_type = event_data.get("type")
        
        if event_type == "app_mention":
            # Handle @mentions
            text = event_data.get("text", "")
            user = event_data.get("user")
            channel = event_data.get("channel")
            
            # Extract command from mention
            # Process command and respond
            pass
        
        elif event_type == "message":
            # Handle direct messages
            pass


# FastAPI endpoint example for webhook receiver
"""
from fastapi import FastAPI, Request
app = FastAPI()

slack_monitor = SlackTaskMonitor(
    slack_token=os.getenv("SLACK_BOT_TOKEN"),
    channel="#semant-tasks"
)

@app.post("/slack/events")
async def slack_events(request: Request):
    data = await request.json()
    
    # Handle URL verification challenge
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}
    
    # Handle events
    event = data.get("event", {})
    if event.get("type") == "app_mention":
        # Handle mention
        pass
    
    return {"status": "ok"}

@app.post("/slack/commands")
async def slack_commands(request: Request):
    # Handle slash commands
    form_data = await request.form()
    command = form_data.get("command")
    text = form_data.get("text")
    user_id = form_data.get("user_id")
    
    response = await slack_monitor.handle_slash_command(command, text, user_id)
    return response
"""
```

### Step 5: Set Up Environment Variables

Add to `.env`:
```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_CHANNEL_TASKS=#semant-tasks
SLACK_CHANNEL_STRATEGY=#semant-strategy
SLACK_CHANNEL_GIT=#semant-git
# ... other channels
```

### Step 6: Install Dependencies

```bash
pip install slack-sdk
# or
pip install slack-bolt  # Alternative SDK
```

### Step 7: Create Slack Channels

In your Slack workspace, create these channels:
- `#semant-tasks` - TaskMaster task monitoring
- `#semant-strategy` - Strategic planning
- `#semant-git` - Git activity
- `#semant-kg` - Knowledge Graph operations
- `#semant-resilience` - System resilience
- `#semant-capabilities` - Capability management
- `#semant-engineering` - Engineering standards
- `#semant-self-discovery` - Self-discovery operations
- `#semant-multimodal` - Multi-modal integrations
- `#semant-symbiosis` - Human-agent collaboration

### Step 8: Set Up Webhook Endpoint

You'll need a webhook endpoint (FastAPI, Flask, etc.) to receive Slack events:

```python
# Example FastAPI endpoint
from fastapi import FastAPI, Request
import os

app = FastAPI()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")

@app.post("/slack/events")
async def slack_webhook(request: Request):
    data = await request.json()
    
    # URL verification challenge
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}
    
    # Process events
    event = data.get("event", {})
    # Handle event...
    
    return {"status": "ok"}
```

### Step 9: Configure Webhook URL in Slack App

1. Go to Slack App settings → "Event Subscriptions"
2. Enable Events
3. Enter your webhook URL: `https://your-domain.com/slack/events`
4. Subscribe to bot events (see Step 2)
5. Save changes

### Step 10: Connect to TaskMaster

Integrate the Slack monitor with your TaskMaster instance:

```python
from integrations.slack_integration import SlackTaskMonitor
# Import your TaskMaster instance

slack_monitor = SlackTaskMonitor(
    slack_token=os.getenv("SLACK_BOT_TOKEN"),
    channel="#semant-tasks"
)

# Initialize with TaskMaster
await slack_monitor.initialize(taskmaster_instance)

# Set up event listeners for task status changes
# (This depends on your TaskMaster implementation)
```

---

## What It Will Look Like Once Implemented

### In Slack Channel `#semant-tasks`:

```
📋 TaskMaster Bot
⏳ Task 16: Strategic Mission & Vision Documentation Framework
Status changed: pending → in-progress

🔄 Task 17: Slack Integration for Task Monitoring  
Status changed: pending → in-progress

✅ Task 18: Git Integration for Change Tracking
Status changed: in-progress → done

📊 Daily Task Summary
• Total tasks: 25
• Pending: 12
• In Progress: 8
• Completed: 5
• Completed Today: 2
```

### Slash Commands:

```
You: /tasks list
Bot: 📋 All Tasks
     • Task 16: Strategic Framework [in-progress]
     • Task 17: Slack Integration [pending]
     • Task 18: Git Integration [done]
     ...

You: /tasks show 16
Bot: 📝 Task 16: Strategic Mission & Vision Documentation Framework
     Status: in-progress
     Priority: high
     Dependencies: None
     ...

You: /tasks next
Bot: ➡️ Next Task: Task 17 - Slack Integration for Task Monitoring
     Ready to start (dependencies satisfied)
```

---

## Quick Start (Minimal Implementation)

If you want a quick implementation to see tasks in Slack right away:

1. **Create simple script** (`scripts/slack_task_notifier.py`):
```python
import os
from slack_sdk import WebClient
import json

# Read TaskMaster tasks
with open('.taskmaster/tasks/tasks.json') as f:
    tasks_data = json.load(f)

tasks = tasks_data['master']['tasks']

# Format message
message = "📋 *Current Tasks*\n\n"
for task in tasks[:10]:  # First 10 tasks
    emoji = {"pending": "⏳", "in-progress": "🔄", "done": "✅"}.get(task['status'], "📝")
    message += f"{emoji} Task {task['id']}: {task['title']} [{task['status']}]\n"

# Send to Slack
client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
client.chat_postMessage(channel="#semant-tasks", text=message, mrkdwn=True)
```

2. **Run it**:
```bash
export SLACK_BOT_TOKEN=xoxb-your-token
python scripts/slack_task_notifier.py
```

---

## Next Steps

1. **Implement Task 17** - Follow the subtasks in the breakdown document
2. **Test with simple script** - Use the quick start above
3. **Build full integration** - Implement the full `SlackTaskMonitor` class
4. **Set up webhooks** - Configure Slack app webhooks
5. **Add slash commands** - Enable interactive task queries

---

## Resources

- [Slack API Documentation](https://api.slack.com/)
- [Slack Python SDK](https://slack.dev/python-slack-sdk/)
- [Slack Bolt Framework](https://slack.dev/bolt-python/) (Alternative)
- Task 17 breakdown: `docs/strategic_mission_vision_breakdown.md`
