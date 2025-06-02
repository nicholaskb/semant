import asyncio
import logging
from typing import Dict, Any, Optional

class WorkflowNotifier:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._notification_queue = None
        self._notification_task = None
        self._running = False
        self._loop = None

    async def initialize(self):
        """Initialize the notifier and start processing notifications."""
        if self._notification_queue is None:
            self._loop = asyncio.get_running_loop()
            self._notification_queue = asyncio.Queue()
            self._running = True
            self._notification_task = self._loop.create_task(self._process_notifications())
            self.logger.info("WorkflowNotifier initialized")

    async def _process_notifications(self):
        """Process notifications from the queue."""
        while self._running:
            try:
                notification = await self._notification_queue.get()
                if notification is None:  # Shutdown signal
                    break
                
                notification_type = notification.get("type")
                if notification_type == "agent_recovery":
                    await self._handle_agent_recovery(notification)
                elif notification_type == "capability_change":
                    await self._handle_capability_notification(notification)
                elif notification_type == "workflow_assembly":
                    await self._handle_workflow_notification(notification)
                
                self._notification_queue.task_done()
            except asyncio.CancelledError:
                self.logger.info("Notification processor cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error processing notification: {e}")

    async def cleanup(self):
        """Clean up resources and cancel pending tasks."""
        self.logger.info("Starting WorkflowNotifier cleanup")
        self._running = False
        
        if self._notification_task and not self._notification_task.done():
            self._notification_task.cancel()
            try:
                await self._notification_task
            except asyncio.CancelledError:
                pass
        
        if self._notification_queue:
            try:
                await self._notification_queue.put(None)  # Signal to stop
                await self._notification_queue.join()
            except Exception as e:
                self.logger.error(f"Error during queue cleanup: {e}")
        
        self._notification_task = None
        self._notification_queue = None
        self._loop = None
        self.logger.info("WorkflowNotifier cleanup completed")

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
        if self._notification_queue is None:
            await self.initialize()
        await self._notification_queue.put({
            "type": "agent_recovery",
            "agent_id": agent_id,
            "success": success
        })

    async def notify_capability_change(self, agent_id: str, capabilities: list):
        """Notify about agent capability changes."""
        if self._notification_queue is None:
            await self.initialize()
        await self._notification_queue.put({
            "type": "capability_change",
            "agent_id": agent_id,
            "capabilities": capabilities
        })

    async def notify_workflow_assembly(self, workflow_id: str, agents: list):
        """Notify about workflow assembly."""
        if self._notification_queue is None:
            await self.initialize()
        await self._notification_queue.put({
            "type": "workflow_assembly",
            "workflow_id": workflow_id,
            "agents": agents
        }) 