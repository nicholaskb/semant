from typing import Dict, List, Optional, Any
from loguru import logger
import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from agents.core.base_agent import BaseAgent, AgentStatus

@dataclass
class HealthCheck:
    """Health check result for an agent."""
    agent_id: str
    status: str
    last_check: float
    response_time: float
    error_count: int
    memory_usage: float
    cpu_usage: float
    details: Dict[str, Any]

class AgentHealth:
    """Manages agent health checks and monitoring."""
    
    def __init__(self):
        self._health_checks: Dict[str, HealthCheck] = {}
        self._check_interval = 30  # seconds
        self._last_check = time.time()
        self._lock = asyncio.Lock()
        self.logger = logger.bind(component="AgentHealth")
        
    async def check_agent_health(self, agent: BaseAgent) -> HealthCheck:
        """Perform a health check on an agent."""
        start_time = time.time()
        try:
            # Check agent status
            status = await agent.get_status()
            
            # Get agent metrics
            metrics = await agent.get_metrics()
            
            # Create health check result
            health_check = HealthCheck(
                agent_id=agent.agent_id,
                status=status.value,
                last_check=start_time,
                response_time=time.time() - start_time,
                error_count=metrics.get("error_count", 0),
                memory_usage=metrics.get("memory_usage", 0.0),
                cpu_usage=metrics.get("cpu_usage", 0.0),
                details=metrics
            )
            
            async with self._lock:
                self._health_checks[agent.agent_id] = health_check
                
            return health_check
            
        except Exception as e:
            self.logger.error(f"Health check failed for agent {agent.agent_id}: {e}")
            health_check = HealthCheck(
                agent_id=agent.agent_id,
                status="error",
                last_check=start_time,
                response_time=time.time() - start_time,
                error_count=1,
                memory_usage=0.0,
                cpu_usage=0.0,
                details={"error": str(e)}
            )
            
            async with self._lock:
                self._health_checks[agent.agent_id] = health_check
                
            return health_check
            
    async def get_agent_health(self, agent_id: str) -> Optional[HealthCheck]:
        """Get the latest health check result for an agent."""
        async with self._lock:
            return self._health_checks.get(agent_id)
            
    async def get_unhealthy_agents(self) -> List[HealthCheck]:
        """Get all agents with health issues."""
        current_time = time.time()
        unhealthy = []
        
        async with self._lock:
            for check in self._health_checks.values():
                # Check if agent is unhealthy
                if (check.status != "idle" and check.status != "busy" or
                    check.response_time > 1.0 or  # Response time > 1 second
                    check.error_count > 0 or
                    check.memory_usage > 0.8 or  # Memory usage > 80%
                    check.cpu_usage > 0.8 or  # CPU usage > 80%
                    current_time - check.last_check > self._check_interval * 2):  # Stale check
                    unhealthy.append(check)
                    
        return unhealthy
        
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of agent health status."""
        current_time = time.time()
        total_agents = len(self._health_checks)
        healthy_agents = 0
        unhealthy_agents = 0
        error_agents = 0
        
        async with self._lock:
            for check in self._health_checks.values():
                if check.status == "error":
                    error_agents += 1
                elif (check.status == "idle" or check.status == "busy") and \
                     check.response_time <= 1.0 and \
                     check.error_count == 0 and \
                     check.memory_usage <= 0.8 and \
                     check.cpu_usage <= 0.8 and \
                     current_time - check.last_check <= self._check_interval * 2:
                    healthy_agents += 1
                else:
                    unhealthy_agents += 1
                    
        return {
            "total_agents": total_agents,
            "healthy_agents": healthy_agents,
            "unhealthy_agents": unhealthy_agents,
            "error_agents": error_agents,
            "timestamp": current_time
        } 