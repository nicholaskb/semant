"""
Example script: consulting-team multi-agent demo (originally demo_agents.py)

Run from project root:
    python -m examples.demo_agents

Alternate:
    PYTHONPATH=. python examples/demo_agents.py
"""
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF
from agents.core.base_agent import BaseAgent, AgentMessage

# Define namespaces
DM = Namespace("http://example.org/demo/")
TASK = Namespace("http://example.org/demo/task/")
AGENT = Namespace("http://example.org/demo/agent/")
ANALYSIS = Namespace("http://example.org/demo/analysis/")
CONSULTING = Namespace("http://example.org/demo/consulting/")

@dataclass
class AgentContext:
    name: str
    persona: str
    expertise: List[str]
    experience: str
    background: str
    communication_style: str

class KnowledgeGraph:
    """Enhanced wrapper around RDFLib Graph for async operations."""
    
    def __init__(self):
        self.graph = Graph()
        self.graph.bind("dm", DM)
        self.graph.bind("task", TASK)
        self.graph.bind("agent", AGENT)
        self.graph.bind("analysis", ANALYSIS)
        
    async def add_triple(self, subject: str, predicate: str, object_: str) -> None:
        """Add a triple to the graph."""
        self.graph.add((URIRef(subject), URIRef(predicate), URIRef(object_)))
        
    async def update_graph(self, data: Dict[str, Dict[str, Any]]) -> None:
        """Update the graph with structured data."""
        for subject, properties in data.items():
            for predicate, value in properties.items():
                if isinstance(value, str):
                    self.graph.add((URIRef(subject), URIRef(predicate), Literal(value)))
                else:
                    self.graph.add((URIRef(subject), URIRef(predicate), URIRef(value)))
                    
    async def query(self, _query_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Query the graph."""
        results = {}
        for s, p, o in self.graph:
            if str(s) not in results:
                results[str(s)] = {}
            results[str(s)][str(p)] = str(o)
        return results

class TaskPlannerAgent(BaseAgent):
    """Agent responsible for breaking down tasks and planning execution."""
    
    def __init__(self, agent_id: str = "task_planner"):
        super().__init__(agent_id, "task_planner")
        self.knowledge_graph = KnowledgeGraph()
        self.log = []
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.logger.info("Task Planner Agent initialized")
        await self.knowledge_graph.add_triple(
            f"agent:{self.agent_id}",
            str(RDF.type),
            str(DM.TaskPlanner)
        )
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        if message.message_type == "task_request":
            return await self._handle_task_request(message)
        else:
            return await self._handle_unknown_message(message)
            
    async def _handle_task_request(self, message: AgentMessage) -> AgentMessage:
        """Handle a new task request."""
        task_id = f"task_{len(self.log) + 1}"
        
        # Log the task planning
        log_entry = {
            "agent": "TaskPlanner",
            "action": "Delegated task to Researcher",
            "task_id": task_id
        }
        self.log.append(log_entry)
        
        # Update knowledge graph
        await self.knowledge_graph.update_graph({
            f"task:{task_id}": {
                str(RDF.type): str(DM.Task),
                str(DM.status): "pending",
                str(DM.description): message.content['description']
            }
        })
        
        # Forward to researcher
        researcher_message = AgentMessage(
            sender=self.agent_id,
            recipient="researcher",
            content={
                'task_id': task_id,
                'description': message.content['description']
            },
            timestamp=message.timestamp,
            message_type="research_request"
        )
        await self.send_message(researcher_message.recipient, researcher_message.content, researcher_message.message_type)
        
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={'status': 'planning', 'task_id': task_id},
            timestamp=message.timestamp,
            message_type="task_response"
        )

class ResearcherAgent(BaseAgent):
    """Agent responsible for gathering facts and information."""
    
    def __init__(self, agent_id: str = "researcher"):
        super().__init__(agent_id, "researcher")
        self.knowledge_graph = KnowledgeGraph()
        self.facts = {}
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.logger.info("Researcher Agent initialized")
        await self.knowledge_graph.add_triple(
            f"agent:{self.agent_id}",
            str(RDF.type),
            str(DM.Researcher)
        )
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        if message.message_type == "research_request":
            return await self._handle_research_request(message)
        else:
            return await self._handle_unknown_message(message)
            
    async def _handle_research_request(self, message: AgentMessage) -> AgentMessage:
        """Handle research requests."""
        task_id = message.content['task_id']
        
        # Simulate gathering facts
        facts = [
            "AI can analyze large datasets of medical records to uncover rare disease patterns.",
            "Machine learning models have been used to assist doctors in diagnosing conditions with few existing cases.",
            "Access to specialized AI tools can be limited in under-resourced regions."
        ]
        
        self.facts[task_id] = facts
        
        # Update knowledge graph
        await self.knowledge_graph.update_graph({
            f"analysis:{task_id}": {
                str(RDF.type): str(DM.Analysis),
                str(DM.hasFacts): [Literal(fact) for fact in facts]
            }
        })
        
        # Forward to analyst
        analyst_message = AgentMessage(
            sender=self.agent_id,
            recipient="analyst",
            content={
                'task_id': task_id,
                'facts': facts
            },
            timestamp=message.timestamp,
            message_type="analysis_request"
        )
        await self.send_message(analyst_message.recipient, analyst_message.content, analyst_message.message_type)
        
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={'status': 'research_complete', 'task_id': task_id, 'facts': facts},
            timestamp=message.timestamp,
            message_type="research_response"
        )

class AnalystAgent(BaseAgent):
    """Agent responsible for analyzing facts and generating pros/cons."""
    
    def __init__(self, agent_id: str = "analyst"):
        super().__init__(agent_id, "analyst")
        self.knowledge_graph = KnowledgeGraph()
        self.analyses = {}
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.logger.info("Analyst Agent initialized")
        await self.knowledge_graph.add_triple(
            f"agent:{self.agent_id}",
            str(RDF.type),
            str(DM.Analyst)
        )
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        if message.message_type == "analysis_request":
            return await self._handle_analysis_request(message)
        else:
            return await self._handle_unknown_message(message)
            
    async def _handle_analysis_request(self, message: AgentMessage) -> AgentMessage:
        """Handle analysis requests."""
        task_id = message.content['task_id']
        facts = message.content['facts']
        
        # Generate pros and cons
        pros = [
            "Scales expertise across many hospitals",
            "Finds patterns humans might miss"
        ]
        cons = [
            "Requires high-quality labeled data",
            "Potential for false positives or misdiagnosis"
        ]
        
        self.analyses[task_id] = {'pros': pros, 'cons': cons}
        
        # Update knowledge graph
        await self.knowledge_graph.update_graph({
            f"analysis:{task_id}": {
                str(DM.hasPros): [Literal(pro) for pro in pros],
                str(DM.hasCons): [Literal(con) for con in cons]
            }
        })
        
        # Forward to summarizer
        summarizer_message = AgentMessage(
            sender=self.agent_id,
            recipient="summarizer",
            content={
                'task_id': task_id,
                'pros': pros,
                'cons': cons
            },
            timestamp=message.timestamp,
            message_type="summary_request"
        )
        await self.send_message(summarizer_message.recipient, summarizer_message.content, summarizer_message.message_type)
        
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={'status': 'analysis_complete', 'task_id': task_id, 'pros': pros, 'cons': cons},
            timestamp=message.timestamp,
            message_type="analysis_response"
        )

class SummarizerAgent(BaseAgent):
    """Agent responsible for generating concise summaries."""
    
    def __init__(self, agent_id: str = "summarizer"):
        super().__init__(agent_id, "summarizer")
        self.knowledge_graph = KnowledgeGraph()
        self.summaries = {}
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.logger.info("Summarizer Agent initialized")
        await self.knowledge_graph.add_triple(
            f"agent:{self.agent_id}",
            str(RDF.type),
            str(DM.Summarizer)
        )
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        if message.message_type == "summary_request":
            return await self._handle_summary_request(message)
        else:
            return await self._handle_unknown_message(message)
            
    async def _handle_summary_request(self, message: AgentMessage) -> AgentMessage:
        """Handle summary requests."""
        task_id = message.content['task_id']
        pros = message.content['pros']
        cons = message.content['cons']
        
        # Generate summary
        summary = (
            "AI shows promise in diagnosing rare diseases by analyzing large datasets and highlighting subtle patterns. "
            "However, its effectiveness depends on high-quality data and careful validation to avoid mistakes."
        )
        
        self.summaries[task_id] = summary
        
        # Update knowledge graph
        await self.knowledge_graph.update_graph({
            f"analysis:{task_id}": {
                str(DM.hasSummary): Literal(summary)
            }
        })
        
        # Forward to auditor
        auditor_message = AgentMessage(
            sender=self.agent_id,
            recipient="auditor",
            content={
                'task_id': task_id,
                'summary': summary,
                'pros': pros,
                'cons': cons
            },
            timestamp=message.timestamp,
            message_type="audit_request"
        )
        await self.send_message(auditor_message.recipient, auditor_message.content, auditor_message.message_type)
        
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={'status': 'summary_complete', 'task_id': task_id, 'summary': summary},
            timestamp=message.timestamp,
            message_type="summary_response"
        )

class AuditorAgent(BaseAgent):
    """Agent responsible for validating results and producing final reports."""
    
    def __init__(self, agent_id: str = "auditor"):
        super().__init__(agent_id, "auditor")
        self.knowledge_graph = KnowledgeGraph()
        self.reports = {}
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.logger.info("Auditor Agent initialized")
        await self.knowledge_graph.add_triple(
            f"agent:{self.agent_id}",
            str(RDF.type),
            str(DM.Auditor)
        )
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        if message.message_type == "audit_request":
            return await self._handle_audit_request(message)
        else:
            return await self._handle_unknown_message(message)
            
    async def _handle_audit_request(self, message: AgentMessage) -> AgentMessage:
        """Handle audit requests."""
        task_id = message.content['task_id']
        
        # Compile final report
        report = {
            "summary": message.content['summary'],
            "pros": message.content['pros'],
            "cons": message.content['cons'],
            "status": "complete"
        }
        
        self.reports[task_id] = report
        
        # Update knowledge graph
        await self.knowledge_graph.update_graph({
            f"task:{task_id}": {
                str(DM.status): "completed",
                str(DM.hasReport): Literal(str(report))
            }
        })
        
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={'status': 'audit_complete', 'task_id': task_id, 'report': report},
            timestamp=message.timestamp,
            message_type="audit_response"
        )

class EngagementManagerAgent(BaseAgent):
    """Senior engagement manager responsible for overall project delivery and client relationship."""
    
    def __init__(self, agent_id: str = "engagement_manager"):
        super().__init__(agent_id, "engagement_manager")
        self.knowledge_graph = KnowledgeGraph()
        self.context = AgentContext(
            name="Sarah Chen",
            persona="Strategic leader with 15+ years of consulting experience",
            expertise=["Strategy", "Healthcare", "Digital Transformation"],
            experience="Former Partner at McKinsey, led 50+ healthcare transformation projects",
            background="MBA from Harvard, MD from Johns Hopkins",
            communication_style="Direct, data-driven, and client-focused"
        )
        self.engagements = {}
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.logger.info("Engagement Manager initialized")
        await self.knowledge_graph.add_triple(
            f"agent:{self.agent_id}",
            str(RDF.type),
            str(CONSULTING.EngagementManager)
        )
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        if message.message_type == "engagement_request":
            return await self._handle_engagement_request(message)
        elif message.message_type == "team_update":
            return await self._handle_team_update(message)
        else:
            return await self._handle_unknown_message(message)
            
    async def _handle_unknown_message(self, message: AgentMessage) -> AgentMessage:
        """Handle unknown message types."""
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={'status': 'unknown_message_type', 'original_type': message.message_type},
            timestamp=message.timestamp,
            message_type="error_response"
        )
            
    async def _handle_engagement_request(self, message: AgentMessage) -> AgentMessage:
        """Handle new engagement requests."""
        engagement_id = f"engagement_{len(self.engagements) + 1}"
        
        # Log engagement details
        self.engagements[engagement_id] = {
            "client": message.content.get("client"),
            "scope": message.content.get("scope"),
            "budget": message.content.get("budget"),
            "timeline": message.content.get("timeline")
        }
        
        # Update knowledge graph
        await self.knowledge_graph.update_graph({
            f"engagement:{engagement_id}": {
                str(RDF.type): str(CONSULTING.Engagement),
                str(CONSULTING.hasClient): message.content.get("client"),
                str(CONSULTING.hasScope): message.content.get("scope"),
                str(CONSULTING.hasBudget): message.content.get("budget"),
                str(CONSULTING.hasTimeline): message.content.get("timeline")
            }
        })
        
        # Delegate to strategy lead
        strategy_message = AgentMessage(
            sender=self.agent_id,
            recipient="strategy_lead",
            content={
                'engagement_id': engagement_id,
                'client': message.content.get("client"),
                'scope': message.content.get("scope")
            },
            timestamp=message.timestamp,
            message_type="strategy_request"
        )
        await self.send_message(strategy_message.recipient, strategy_message.content, strategy_message.message_type)
        
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={'status': 'engagement_started', 'engagement_id': engagement_id},
            timestamp=message.timestamp,
            message_type="engagement_response"
        )

    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with engagement information."""
        await self.knowledge_graph.update_graph(update_data)
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for engagement information."""
        return await self.knowledge_graph.query(query)

class StrategyLeadAgent(BaseAgent):
    """Strategy expert responsible for developing high-level strategic recommendations."""
    
    def __init__(self, agent_id: str = "strategy_lead"):
        super().__init__(agent_id, "strategy_lead")
        self.knowledge_graph = KnowledgeGraph()
        self.context = AgentContext(
            name="James Wilson",
            persona="Strategic thinker with deep industry expertise",
            expertise=["Corporate Strategy", "Market Entry", "Growth Strategy"],
            experience="12 years at McKinsey, led strategy for Fortune 500 healthcare companies",
            background="PhD in Economics from MIT, MBA from Wharton",
            communication_style="Analytical, persuasive, and visionary"
        )
        self.strategies = {}
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.logger.info("Strategy Lead initialized")
        await self.knowledge_graph.add_triple(
            f"agent:{self.agent_id}",
            str(RDF.type),
            str(CONSULTING.StrategyLead)
        )
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        if message.message_type == "strategy_request":
            return await self._handle_strategy_request(message)
        else:
            return await self._handle_unknown_message(message)
            
    async def _handle_unknown_message(self, message: AgentMessage) -> AgentMessage:
        """Handle unknown message types."""
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={'status': 'unknown_message_type', 'original_type': message.message_type},
            timestamp=message.timestamp,
            message_type="error_response"
        )
            
    async def _handle_strategy_request(self, message: AgentMessage) -> AgentMessage:
        """Handle strategy development requests."""
        engagement_id = message.content['engagement_id']
        
        # Develop strategic recommendations
        strategy = {
            "vision": "Transform healthcare delivery through AI-driven diagnostics",
            "key_pillars": [
                "Digital Transformation",
                "Operational Excellence",
                "Patient-Centric Care"
            ],
            "implementation_approach": "Phased rollout with quick wins"
        }
        
        self.strategies[engagement_id] = strategy
        
        # Update knowledge graph
        await self.knowledge_graph.update_graph({
            f"strategy:{engagement_id}": {
                str(RDF.type): str(CONSULTING.Strategy),
                str(CONSULTING.hasVision): strategy["vision"],
                str(CONSULTING.hasPillars): [Literal(pillar) for pillar in strategy["key_pillars"]],
                str(CONSULTING.hasApproach): strategy["implementation_approach"]
            }
        })
        
        # Delegate to implementation lead
        implementation_message = AgentMessage(
            sender=self.agent_id,
            recipient="implementation_lead",
            content={
                'engagement_id': engagement_id,
                'strategy': strategy
            },
            timestamp=message.timestamp,
            message_type="implementation_request"
        )
        await self.send_message(implementation_message.recipient, implementation_message.content, implementation_message.message_type)
        
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={'status': 'strategy_developed', 'engagement_id': engagement_id, 'strategy': strategy},
            timestamp=message.timestamp,
            message_type="strategy_response"
        )

    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with strategy information."""
        await self.knowledge_graph.update_graph(update_data)
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for strategy information."""
        return await self.knowledge_graph.query(query)

class ImplementationLeadAgent(BaseAgent):
    """Implementation expert responsible for operationalizing strategic recommendations."""
    
    def __init__(self, agent_id: str = "implementation_lead"):
        super().__init__(agent_id, "implementation_lead")
        self.knowledge_graph = KnowledgeGraph()
        self.context = AgentContext(
            name="Maria Rodriguez",
            persona="Execution-focused leader with proven track record",
            expertise=["Change Management", "Process Optimization", "Digital Implementation"],
            experience="10 years at McKinsey, led 30+ large-scale transformations",
            background="MBA from Stanford, Six Sigma Black Belt",
            communication_style="Practical, action-oriented, and results-driven"
        )
        self.implementations = {}
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.logger.info("Implementation Lead initialized")
        await self.knowledge_graph.add_triple(
            f"agent:{self.agent_id}",
            str(RDF.type),
            str(CONSULTING.ImplementationLead)
        )
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        if message.message_type == "implementation_request":
            return await self._handle_implementation_request(message)
        else:
            return await self._handle_unknown_message(message)
            
    async def _handle_unknown_message(self, message: AgentMessage) -> AgentMessage:
        """Handle unknown message types."""
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={'status': 'unknown_message_type', 'original_type': message.message_type},
            timestamp=message.timestamp,
            message_type="error_response"
        )
            
    async def _handle_implementation_request(self, message: AgentMessage) -> AgentMessage:
        """Handle implementation planning requests."""
        engagement_id = message.content['engagement_id']
        strategy = message.content['strategy']
        
        # Develop implementation plan
        implementation = {
            "phases": [
                {
                    "name": "Quick Wins",
                    "duration": "3 months",
                    "key_activities": ["AI pilot program", "Staff training"]
                },
                {
                    "name": "Core Transformation",
                    "duration": "12 months",
                    "key_activities": ["System integration", "Process redesign"]
                },
                {
                    "name": "Scale & Optimize",
                    "duration": "6 months",
                    "key_activities": ["Performance optimization", "Knowledge transfer"]
                }
            ],
            "resource_requirements": {
                "team_size": 25,
                "budget_allocation": "40-30-30 across phases"
            }
        }
        
        self.implementations[engagement_id] = implementation
        
        # Update knowledge graph
        await self.knowledge_graph.update_graph({
            f"implementation:{engagement_id}": {
                str(RDF.type): str(CONSULTING.Implementation),
                str(CONSULTING.hasPhases): [Literal(str(phase)) for phase in implementation["phases"]],
                str(CONSULTING.hasResources): Literal(str(implementation["resource_requirements"]))
            }
        })
        
        # Delegate to value realization lead
        value_message = AgentMessage(
            sender=self.agent_id,
            recipient="value_realization_lead",
            content={
                'engagement_id': engagement_id,
                'implementation': implementation
            },
            timestamp=message.timestamp,
            message_type="value_request"
        )
        await self.send_message(value_message.recipient, value_message.content, value_message.message_type)
        
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={'status': 'implementation_planned', 'engagement_id': engagement_id, 'implementation': implementation},
            timestamp=message.timestamp,
            message_type="implementation_response"
        )

    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with implementation information."""
        await self.knowledge_graph.update_graph(update_data)
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for implementation information."""
        return await self.knowledge_graph.query(query)

class ValueRealizationLeadAgent(BaseAgent):
    """Expert responsible for measuring and tracking value delivery."""
    
    def __init__(self, agent_id: str = "value_realization_lead"):
        super().__init__(agent_id, "value_realization_lead")
        self.knowledge_graph = KnowledgeGraph()
        self.context = AgentContext(
            name="David Kim",
            persona="Data-driven value measurement expert",
            expertise=["ROI Analysis", "Performance Metrics", "Value Tracking"],
            experience="8 years at McKinsey, developed value tracking frameworks for healthcare clients",
            background="PhD in Statistics from Berkeley, CFA Charterholder",
            communication_style="Precise, metrics-focused, and evidence-based"
        )
        self.value_tracking = {}
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        await super().initialize()
        self.logger.info("Value Realization Lead initialized")
        await self.knowledge_graph.add_triple(
            f"agent:{self.agent_id}",
            str(RDF.type),
            str(CONSULTING.ValueRealizationLead)
        )
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        if message.message_type == "value_request":
            return await self._handle_value_request(message)
        else:
            return await self._handle_unknown_message(message)
            
    async def _handle_unknown_message(self, message: AgentMessage) -> AgentMessage:
        """Handle unknown message types."""
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={'status': 'unknown_message_type', 'original_type': message.message_type},
            timestamp=message.timestamp,
            message_type="error_response"
        )
            
    async def _handle_value_request(self, message: AgentMessage) -> AgentMessage:
        """Handle value measurement planning requests."""
        engagement_id = message.content['engagement_id']
        implementation = message.content['implementation']
        
        # Develop value tracking framework
        value_framework = {
            "key_metrics": [
                {
                    "name": "Diagnostic Accuracy",
                    "target": "95%",
                    "measurement_frequency": "Monthly"
                },
                {
                    "name": "Cost Reduction",
                    "target": "30%",
                    "measurement_frequency": "Quarterly"
                },
                {
                    "name": "Patient Satisfaction",
                    "target": "90%",
                    "measurement_frequency": "Monthly"
                }
            ],
            "value_tracking_process": {
                "data_collection": "Automated through integrated systems",
                "reporting": "Real-time dashboards with monthly reviews",
                "governance": "Steering committee oversight"
            }
        }
        
        self.value_tracking[engagement_id] = value_framework
        
        # Update knowledge graph
        await self.knowledge_graph.update_graph({
            f"value:{engagement_id}": {
                str(RDF.type): str(CONSULTING.ValueFramework),
                str(CONSULTING.hasMetrics): [Literal(str(metric)) for metric in value_framework["key_metrics"]],
                str(CONSULTING.hasProcess): Literal(str(value_framework["value_tracking_process"]))
            }
        })
        
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={'status': 'value_framework_developed', 'engagement_id': engagement_id, 'framework': value_framework},
            timestamp=message.timestamp,
            message_type="value_response"
        )

    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with value tracking information."""
        await self.knowledge_graph.update_graph(update_data)
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for value tracking information."""
        return await self.knowledge_graph.query(query)

async def run_demo():
    """Run a demonstration of the McKinsey-style consulting team."""
    # Create agents
    engagement_manager = EngagementManagerAgent()
    strategy_lead = StrategyLeadAgent()
    implementation_lead = ImplementationLeadAgent()
    value_realization_lead = ValueRealizationLeadAgent()
    
    # Initialize agents
    await engagement_manager.initialize()
    await strategy_lead.initialize()
    await implementation_lead.initialize()
    await value_realization_lead.initialize()
    
    # Create an engagement request
    engagement_message = AgentMessage(
        sender="client",
        recipient="engagement_manager",
        content={
            'client': 'Global Healthcare Provider',
            'scope': 'AI-driven diagnostic transformation',
            'budget': '$50M',
            'timeline': '18 months'
        },
        timestamp=0.0,
        message_type="engagement_request"
    )
    
    # Process the engagement
    response = await engagement_manager.process_message(engagement_message)
    print(f"Engagement Manager Response: {response.content}")
    
    # Print knowledge graph contents
    print("\nKnowledge Graph Contents:")
    for s, p, o in engagement_manager.knowledge_graph.graph:
        print(f"{s} {p} {o}")

if __name__ == "__main__":
    asyncio.run(run_demo()) 