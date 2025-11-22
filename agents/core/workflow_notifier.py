import asyncio
import logging
from typing import Dict, Any, Optional

class WorkflowNotifier:
    """Handles workflow event notifications."""
    
    def __init__(self):
        self._subscribers = set()
        self._event_loop = None
        self._running = False
        self._tasks = set()
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize the notifier."""
        self._event_loop = asyncio.get_running_loop()
        self._running = True
        self.logger.info("WorkflowNotifier initialized")
    
    async def subscribe(self, subscriber):
        """Subscribe to workflow events."""
        if not self._running:
            await self.initialize()
        self._subscribers.add(subscriber)
    
    async def unsubscribe(self, subscriber):
        """Unsubscribe from workflow events."""
        self._subscribers.discard(subscriber)
    
    async def notify(self, event):
        """Notify all subscribers of an event."""
        if not self._running:
            await self.initialize()
            
        tasks = []
        for subscriber in self._subscribers:
            task = asyncio.create_task(subscriber.handle_event(event))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def cleanup(self):
        """Clean up resources."""
        self._running = False
        
        # Cancel all pending tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self._tasks.clear()
        self._subscribers.clear()
        self.logger.info("WorkflowNotifier cleaned up")

    async def _handle_agent_recovery(self, notification: Dict[str, Any]):
        """Handle agent recovery notifications."""
        agent_id = notification.get("agent_id")
        success = notification.get("success", False)
        self.logger.info(f"Agent {agent_id} recovery {'succeeded' if success else 'failed'}")

    async def _handle_capability_notification(self, notification: Dict[str, Any]):
        """Handle capability change notifications."""
        agent_id = notification.get("agent_id")
        capabilities = notification.get("capabilities", [])
        self.logger.info(f"Agent {agent_id} capabilities updated: {capabilities}")

    async def _handle_workflow_notification(self, notification: Dict[str, Any]):
        """Handle workflow assembly notifications."""
        workflow_id = notification.get("workflow_id")
        agents = notification.get("agents", [])
        self.logger.info(f"Workflow {workflow_id} assembled with agents: {agents}")

    async def notify_agent_recovery(self, agent_id: str, success: bool):
        """Notify about agent recovery attempt."""
        await self.notify({
            "type": "agent_recovery",
            "agent_id": agent_id,
            "success": success
        })

    async def notify_capability_change(self, agent_id: str, capabilities: list):
        """Notify about agent capability changes."""
        await self.notify({
            "type": "capability_change",
            "agent_id": agent_id,
            "capabilities": capabilities
        })

    async def notify_workflow_assembly(self, workflow_id: str, agents: list):
        """Notify about workflow assembly."""
        await self.notify({
            "type": "workflow_assembly",
            "workflow_id": workflow_id,
            "agents": agents
        })

    async def notify_agent_registered(self, agent_id: str, capabilities: list):
        """Notify about agent registration."""
        await self.notify({
            "type": "agent_registered",
            "agent_id": agent_id,
            "capabilities": capabilities
        }) 