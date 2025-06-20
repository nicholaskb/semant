from typing import Dict, List, Any, Optional, Set
import asyncio
from loguru import logger
import time
from datetime import datetime, timedelta
from collections import defaultdict
from .base_agent import AgentMessage
from dataclasses import dataclass
from enum import Enum
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry
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
    """Monitors workflow execution and collects metrics."""
    
    def __init__(self):
        """Initialize workflow monitor."""
        self.metrics = {}
        self._initialize_metrics()
        
    def _initialize_metrics(self):
        """Initialize metrics storage."""
        self.metrics = {
            "workflow_count": 0,
            "active_workflows": 0,
            "completed_workflows": 0,
            "failed_workflows": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0
        }
        
    async def track_workflow_metrics(
        self,
        workflow_id: str,
        metrics: Dict[str, Any]
    ) -> None:
        """Track workflow execution metrics."""
        if workflow_id not in self.metrics:
            self.metrics[workflow_id] = {
                "state_changes": [],
                "agent_metrics": {},
                "error_counts": defaultdict(int),
                "response_times": [],
                "resource_usage": defaultdict(list)
            }
            
        workflow_metrics = self.metrics[workflow_id]
        
        # Add timestamp to metrics
        metrics["timestamp"] = datetime.now().isoformat()
        
        # Track state changes if status is provided
        if "state" in metrics:
            workflow_metrics["state_changes"].append({
                "state": metrics["state"],
                "timestamp": metrics["timestamp"]
            })
            
        # Track response time if provided
        if "response_time" in metrics:
            workflow_metrics["response_times"].append(metrics["response_time"])
            
        # Track resource usage if provided
        if "resource_usage" in metrics:
            for resource, value in metrics["resource_usage"].items():
                workflow_metrics["resource_usage"][resource].append({"usage": value, "timestamp": metrics["timestamp"]})
                
    async def get_workflow_metrics(
        self,
        workflow_id: str,
        metric_type: str = None
    ) -> Dict[str, Any]:
        """Get metrics for a workflow."""
        if workflow_id not in self.metrics:
            return {}
            
        workflow_metrics = self.metrics[workflow_id]
        
        if metric_type:
            return workflow_metrics.get(metric_type, {})
            
        return workflow_metrics
        
    async def get_active_alerts(
        self,
        workflow_id: str = None
    ) -> List[Dict[str, Any]]:
        """Get active alerts for workflows."""
        alerts = []
        
        for wf_id, metrics in self.metrics.items():
            if workflow_id and wf_id != workflow_id:
                continue
                
            # Check resource usage thresholds
            if "resource_usage" in metrics:
                for resource, values in metrics["resource_usage"].items():
                    # Each entry in the list is a dict {"usage": float, "timestamp": str}
                    if not values:
                        continue

                    latest_entry = values[-1]

                    # Guard against malformed entries (e.g., a bare float accidentally stored)
                    latest_usage = (
                        latest_entry["usage"] if isinstance(latest_entry, dict) and "usage" in latest_entry else latest_entry
                    )

                    if resource == "cpu" and latest_usage > 0.8:
                        alerts.append({
                            "workflow_id": wf_id,
                            "type": "high_cpu_usage",
                            "value": latest_usage,
                            "timestamp": datetime.now().isoformat()
                        })
                    elif resource == "memory" and latest_usage > 0.8:
                        alerts.append({
                            "workflow_id": wf_id,
                            "type": "high_memory_usage",
                            "value": latest_usage,
                            "timestamp": datetime.now().isoformat()
                        })
                            
            # Check response time thresholds
            if "response_times" in metrics and metrics["response_times"]:
                avg_response_time = sum(metrics["response_times"]) / len(metrics["response_times"])
                if avg_response_time > 5.0:  # 5 seconds threshold
                    alerts.append({
                        "workflow_id": wf_id,
                        "type": "high_response_time",
                        "value": avg_response_time,
                        "timestamp": datetime.now().isoformat()
                    })
                    
            # Check error counts
            if "error_counts" in metrics:
                total_errors = sum(metrics["error_counts"].values())
                if total_errors > 5:  # 5 errors threshold
                    alerts.append({
                        "workflow_id": wf_id,
                        "type": "high_error_count",
                        "value": total_errors,
                        "timestamp": datetime.now().isoformat()
                    })
                    
        return alerts
        
    async def clear_metrics(self, workflow_id: str = None) -> None:
        """Clear metrics for a workflow or all workflows."""
        if workflow_id:
            if workflow_id in self.metrics:
                del self.metrics[workflow_id]
        else:
            self.metrics.clear()
            self._initialize_metrics()
            
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics."""
        return {
            "workflow_count": len(self.metrics),
            "active_workflows": sum(1 for m in self.metrics.values() if m.get("state_changes") and m["state_changes"][-1]["state"] == "running"),
            "completed_workflows": sum(1 for m in self.metrics.values() if m.get("state_changes") and m["state_changes"][-1]["state"] == "completed"),
            "failed_workflows": sum(1 for m in self.metrics.values() if m.get("state_changes") and m["state_changes"][-1]["state"] == "failed"),
            "total_errors": sum(sum(m["error_counts"].values()) for m in self.metrics.values() if "error_counts" in m),
            "average_response_time": self._calculate_average_response_time()
        }
        
    def _calculate_average_response_time(self) -> float:
        """Calculate average response time across all workflows."""
        total_time = 0.0
        total_count = 0
        
        for metrics in self.metrics.values():
            if "response_times" in metrics and metrics["response_times"]:
                total_time += sum(metrics["response_times"])
                total_count += len(metrics["response_times"])
                
        return total_time / total_count if total_count > 0 else 0.0

    def __init__(self, registry=None):
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
        self._registry = registry
        
        # Prometheus metrics
        reg = registry if registry is not None else None
        self.workflow_latency = Histogram(
            'workflow_latency_seconds',
            'Time taken to complete workflows',
            ['workflow_id', 'capability'],
            registry=reg
        )
        self.workflow_errors = Counter(
            'workflow_errors_total',
            'Total number of workflow errors',
            ['workflow_id', 'error_type'],
            registry=reg
        )
        self.active_workflows = Gauge(
            'active_workflows',
            'Number of currently active workflows',
            ['status'],
            registry=reg
        )
        self.step_latency = Histogram(
            'workflow_step_latency_seconds',
            'Time taken to complete workflow steps',
            ['workflow_id', 'step_id', 'capability'],
            registry=reg
        )
        
    async def track_workflow_start(self, workflow_id: str, steps: List[Dict]) -> None:
        """Track workflow start."""
        self.workflow_steps.labels(workflow_id=workflow_id).set(len(steps))
        self.workflow_status.labels(workflow_id=workflow_id, status='running').set(1)
        
    async def track_workflow_completion(self, workflow_id: str, duration: float) -> None:
        """Track workflow completion."""
        self.workflow_duration.labels(workflow_id=workflow_id).set(duration)
        self.workflow_status.labels(workflow_id=workflow_id, status='completed').set(1)
        
    async def track_workflow_error(self, workflow_id: str, error: str) -> None:
        """Track workflow error."""
        self.workflow_status.labels(workflow_id=workflow_id, status='error').set(1)
        
    async def track_step_start(self, workflow_id: str, step_id: str) -> None:
        """Track step start."""
        self.step_duration.labels(workflow_id=workflow_id, step_id=step_id).observe(0)
        
    async def track_step_completion(self, workflow_id: str, step_id: str, duration: float) -> None:
        """Track step completion."""
        self.step_duration.labels(workflow_id=workflow_id, step_id=step_id).observe(duration)
        
    async def track_agent_usage(self, agent_id: str, capability: str) -> None:
        """Track agent usage."""
        self.agent_usage.labels(agent_id=agent_id, capability=capability).inc()
        
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