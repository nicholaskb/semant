from typing import Dict, List, Any, Optional, Set
import asyncio
from loguru import logger
import time
from datetime import datetime, timedelta
from collections import defaultdict
from .base_agent import AgentMessage
from dataclasses import dataclass
from enum import Enum
from prometheus_client import Counter, Gauge, Histogram
from .workflow_types import Workflow, WorkflowStep, WorkflowStatus

class MetricType(str, Enum):
    """Types of metrics tracked."""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    QUEUE_LENGTH = "queue_length"
    RESOURCE_USAGE = "resource_usage"

@dataclass
class MetricValue:
    """A metric value with timestamp."""
    value: float
    timestamp: float
    labels: Dict[str, str]

class WorkflowMonitor:
    """Handles workflow monitoring, metrics collection, and alerting."""
    
    def __init__(self):
        self.metrics: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "response_times": [],
                "error_counts": defaultdict(int),
                "state_changes": [],
                "resource_usage": defaultdict(list)
            }
        )
        self.alerts: List[Dict[str, Any]] = []
        self.thresholds = {
            "response_time": 1.0,  # seconds
            "error_rate": 0.01,    # 1%
            "memory_usage": 0.8,   # 80%
            "cpu_usage": 0.8,      # 80%
            "stuck_timeout": 3600  # 1 hour
        }
        self.logger = logger.bind(component="WorkflowMonitor")
        self._lock = asyncio.Lock()
        self._metrics: Dict[str, List[MetricValue]] = {}
        
        # Prometheus metrics
        self.workflow_latency = Histogram(
            'workflow_latency_seconds',
            'Time taken to complete workflows',
            ['workflow_id', 'capability']
        )
        self.workflow_errors = Counter(
            'workflow_errors_total',
            'Total number of workflow errors',
            ['workflow_id', 'error_type']
        )
        self.active_workflows = Gauge(
            'active_workflows',
            'Number of currently active workflows',
            ['status']
        )
        self.step_latency = Histogram(
            'workflow_step_latency_seconds',
            'Time taken to complete workflow steps',
            ['workflow_id', 'step_id', 'capability']
        )
        
    async def track_workflow_metrics(
        self,
        workflow_id: str,
        agent_id: str,
        metrics: Dict[str, Any]
    ) -> None:
        """Track workflow execution metrics."""
        if workflow_id not in self.metrics:
            self.metrics[workflow_id] = {
                "state_changes": [],
                "agent_metrics": {},
                "error_counts": defaultdict(int)
            }
            
        workflow_metrics = self.metrics[workflow_id]
        
        # Track agent metrics
        if "agent_metrics" not in workflow_metrics:
            workflow_metrics["agent_metrics"] = {}
            
        if agent_id not in workflow_metrics["agent_metrics"]:
            workflow_metrics["agent_metrics"][agent_id] = []
            
        # Add timestamp to metrics
        metrics["timestamp"] = datetime.now().isoformat()
        workflow_metrics["agent_metrics"][agent_id].append(metrics)
        
        # Track state changes if status is provided
        if "status" in metrics:
            workflow_metrics["state_changes"].append({
                "state": metrics["status"],
                "timestamp": metrics["timestamp"],
                "agent_id": agent_id
            })
            
        # Track errors if present
        if metrics.get("status") == "error":
            workflow_metrics["error_counts"]["agent_error"] += 1
            
        self.logger.info(f"Tracked metrics for workflow {workflow_id}, agent {agent_id}")
        
    async def track_workflow_assembly(
        self,
        workflow_id: str,
        assembled_agents: List[str]
    ) -> None:
        """Track workflow assembly metrics."""
        workflow_metrics = self.metrics[workflow_id]
        
        # Track assembly metrics
        workflow_metrics["state_changes"].append({
            "state": "assembled",
            "timestamp": datetime.now().isoformat(),
            "assembled_agents": assembled_agents
        })
        
        # Track agent assignments
        for agent_id in assembled_agents:
            if "agent_assignments" not in workflow_metrics:
                workflow_metrics["agent_assignments"] = []
            workflow_metrics["agent_assignments"].append({
                "agent_id": agent_id,
                "assigned_at": datetime.now().isoformat()
            })
            
        self.logger.info(f"Tracked assembly for workflow {workflow_id} with {len(assembled_agents)} agents")

    async def track_workflow_error(
        self,
        workflow_id: str,
        error_message: str
    ) -> None:
        """Track workflow error metrics."""
        workflow_metrics = self.metrics[workflow_id]
        
        # Track error metrics
        workflow_metrics["state_changes"].append({
            "state": "error",
            "timestamp": datetime.now().isoformat(),
            "error": error_message
        })
        
        # Increment error count
        workflow_metrics["error_counts"]["workflow_error"] += 1
        
        # Create alert for workflow error
        await self._create_alert(
            workflow_id,
            "workflow_error",
            f"Workflow error: {error_message}"
        )
        
        self.logger.error(f"Tracked error for workflow {workflow_id}: {error_message}")
        
    async def _check_alerts(
        self,
        workflow_id: str,
        metrics: Dict[str, Any]
    ) -> None:
        """Check metrics against thresholds and create alerts if needed."""
        workflow_metrics = self.metrics[workflow_id]
        
        # Check response time
        if "response_time" in metrics and metrics["response_time"] > self.thresholds["response_time"]:
            await self._create_alert(
                workflow_id,
                "high_response_time",
                f"Response time {metrics['response_time']}s exceeds threshold {self.thresholds['response_time']}s"
            )
            
        # Check error rate
        total_requests = len(workflow_metrics["response_times"])
        if total_requests > 0:
            error_rate = sum(workflow_metrics["error_counts"].values()) / total_requests
            if error_rate > self.thresholds["error_rate"]:
                await self._create_alert(
                    workflow_id,
                    "high_error_rate",
                    f"Error rate {error_rate:.2%} exceeds threshold {self.thresholds['error_rate']:.2%}"
                )
                
        # Check resource usage
        if "resource_usage" in metrics:
            for resource, usage in metrics["resource_usage"].items():
                if usage > self.thresholds[f"{resource}_usage"]:
                    await self._create_alert(
                        workflow_id,
                        f"high_{resource}_usage",
                        f"{resource.title()} usage {usage:.2%} exceeds threshold {self.thresholds[f'{resource}_usage']:.2%}"
                    )
                    
        # Check for stuck workflows
        if "state" in metrics and metrics["state"] == "executing":
            last_update = workflow_metrics["state_changes"][-1]["timestamp"]
            if datetime.now() - datetime.fromisoformat(last_update) > timedelta(seconds=self.thresholds["stuck_timeout"]):
                await self._create_alert(
                    workflow_id,
                    "stuck_workflow",
                    f"Workflow stuck in executing state for more than {self.thresholds['stuck_timeout']} seconds"
                )
                
    async def _create_alert(
        self,
        workflow_id: str,
        alert_type: str,
        message: str
    ) -> None:
        """Create a new alert."""
        alert = {
            "id": f"alert_{len(self.alerts) + 1}",
            "workflow_id": workflow_id,
            "type": alert_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "status": "active"
        }
        self.alerts.append(alert)
        self.logger.warning(f"Alert created: {message}")
        
    async def get_workflow_metrics(
        self,
        workflow_id: str,
        metric_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get metrics for a workflow."""
        workflow_metrics = self.metrics[workflow_id]
        
        if metric_type:
            return {metric_type: workflow_metrics[metric_type]}
            
        return {
            "response_times": workflow_metrics["response_times"],
            "error_counts": dict(workflow_metrics["error_counts"]),
            "state_changes": workflow_metrics["state_changes"],
            "resource_usage": dict(workflow_metrics["resource_usage"])
        }
        
    async def get_active_alerts(
        self,
        workflow_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get active alerts, optionally filtered by workflow."""
        alerts = [a for a in self.alerts if a["status"] == "active"]
        if workflow_id:
            alerts = [a for a in alerts if a["workflow_id"] == workflow_id]
        return alerts
        
    async def resolve_alert(self, alert_id: str) -> None:
        """Mark an alert as resolved."""
        for alert in self.alerts:
            if alert["id"] == alert_id:
                alert["status"] = "resolved"
                alert["resolved_at"] = datetime.now().isoformat()
                self.logger.info(f"Alert {alert_id} resolved")
                break
                
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics."""
        total_workflows = len(self.metrics)
        active_alerts = len([a for a in self.alerts if a["status"] == "active"])
        
        # Calculate average response times
        avg_response_times = {}
        for workflow_id, metrics in self.metrics.items():
            if metrics["response_times"]:
                avg_response_times[workflow_id] = sum(metrics["response_times"]) / len(metrics["response_times"])
                
        # Calculate error rates
        error_rates = {}
        for workflow_id, metrics in self.metrics.items():
            total_requests = len(metrics["response_times"])
            if total_requests > 0:
                error_rates[workflow_id] = sum(metrics["error_counts"].values()) / total_requests
                
        return {
            "total_workflows": total_workflows,
            "active_alerts": active_alerts,
            "average_response_times": avg_response_times,
            "error_rates": error_rates,
            "timestamp": datetime.now().isoformat()
        }

    async def record_workflow_start(self, workflow: Workflow) -> None:
        """Record the start of a workflow."""
        async with self._lock:
            self.active_workflows.labels(status=workflow.status.value).inc()
            self._record_metric(
                f"workflow_{workflow.id}_start",
                MetricValue(1.0, time.time(), {"status": workflow.status.value})
            )
            
    async def record_workflow_end(self, workflow: Workflow) -> None:
        """Record the end of a workflow."""
        async with self._lock:
            self.active_workflows.labels(status=workflow.status.value).dec()
            duration = time.time() - workflow.created_at
            self.workflow_latency.labels(
                workflow_id=workflow.id,
                capability="all"
            ).observe(duration)
            
            self._record_metric(
                f"workflow_{workflow.id}_end",
                MetricValue(duration, time.time(), {
                    "status": workflow.status.value,
                    "error": workflow.error or ""
                })
            )
            
    async def record_step_start(self, workflow: Workflow, step: WorkflowStep) -> None:
        """Record the start of a workflow step."""
        async with self._lock:
            self._record_metric(
                f"step_{step.id}_start",
                MetricValue(1.0, time.time(), {
                    "workflow_id": workflow.id,
                    "capability": step.capability
                })
            )
            
    async def record_step_end(self, workflow: Workflow, step: WorkflowStep) -> None:
        """Record the end of a workflow step."""
        async with self._lock:
            if step.start_time and step.end_time:
                duration = step.end_time - step.start_time
                self.step_latency.labels(
                    workflow_id=workflow.id,
                    step_id=step.id,
                    capability=step.capability
                ).observe(duration)
                
                self._record_metric(
                    f"step_{step.id}_end",
                    MetricValue(duration, time.time(), {
                        "workflow_id": workflow.id,
                        "capability": step.capability,
                        "status": step.status.value,
                        "error": step.error or ""
                    })
                )
                
    async def record_error(self, workflow: Workflow, step: Optional[WorkflowStep], error: str) -> None:
        """Record a workflow or step error."""
        async with self._lock:
            if step:
                self.workflow_errors.labels(
                    workflow_id=workflow.id,
                    error_type=f"step_{step.capability}"
                ).inc()
            else:
                self.workflow_errors.labels(
                    workflow_id=workflow.id,
                    error_type="workflow"
                ).inc()
                
            self._record_metric(
                f"error_{workflow.id}",
                MetricValue(1.0, time.time(), {
                    "workflow_id": workflow.id,
                    "step_id": step.id if step else "workflow",
                    "error": error
                })
            )
            
    def _record_metric(self, name: str, value: MetricValue) -> None:
        """Record a metric value."""
        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append(value)
        
    async def get_metrics(
        self,
        metric_type: Optional[MetricType] = None,
        workflow_id: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> Dict[str, List[MetricValue]]:
        """Get metrics matching the specified criteria."""
        async with self._lock:
            filtered_metrics = {}
            for name, values in self._metrics.items():
                # Filter by metric type
                if metric_type and not name.startswith(metric_type.value):
                    continue
                    
                # Filter by workflow ID
                if workflow_id and not name.endswith(workflow_id):
                    continue
                    
                # Filter by time range
                filtered_values = values
                if start_time:
                    filtered_values = [v for v in filtered_values if v.timestamp >= start_time]
                if end_time:
                    filtered_values = [v for v in filtered_values if v.timestamp <= end_time]
                    
                if filtered_values:
                    filtered_metrics[name] = filtered_values
                    
            return filtered_metrics
            
    async def get_workflow_summary(self, workflow_id: str) -> Dict:
        """Get a summary of metrics for a workflow."""
        metrics = await self.get_metrics(workflow_id=workflow_id)
        
        # Calculate summary statistics
        summary = {
            "total_steps": 0,
            "completed_steps": 0,
            "failed_steps": 0,
            "total_duration": 0.0,
            "average_step_duration": 0.0,
            "error_count": 0
        }
        
        step_durations = []
        for name, values in metrics.items():
            if name.startswith("step_") and name.endswith("_end"):
                for value in values:
                    if value.labels.get("status") == WorkflowStatus.COMPLETED.value:
                        step_durations.append(value.value)
                        summary["completed_steps"] += 1
                    elif value.labels.get("status") == WorkflowStatus.FAILED.value:
                        summary["failed_steps"] += 1
                        if value.labels.get("error"):
                            summary["error_count"] += 1
                            
        if step_durations:
            summary["average_step_duration"] = sum(step_durations) / len(step_durations)
            summary["total_duration"] = sum(step_durations)
            
        summary["total_steps"] = summary["completed_steps"] + summary["failed_steps"]
        
        return summary 