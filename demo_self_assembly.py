import asyncio
from typing import Dict, Any, List, Set
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS
from agents.core.base_agent import BaseAgent, AgentMessage
import logging

# Define namespaces
DM = Namespace("http://example.org/demo/")
AGENT = Namespace("http://example.org/demo/agent/")
CAPABILITY = Namespace("http://example.org/demo/capability/")

class KnowledgeGraph:
    """Knowledge graph for agent coordination."""
    
    def __init__(self):
        self.graph = Graph()
        self.graph.bind("dm", DM)
        self.graph.bind("agent", AGENT)
        self.graph.bind("capability", CAPABILITY)
        
    async def add_triple(self, subject: str, predicate: str, object_: str) -> None:
        self.graph.add((URIRef(subject), URIRef(predicate), URIRef(object_)))
        
    async def update_graph(self, data: Dict[str, Dict[str, Any]]) -> None:
        for subject, properties in data.items():
            for predicate, value in properties.items():
                self.graph.add((URIRef(subject), URIRef(predicate), Literal(value)))
        
    async def query(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        results = {}
        for s, p, o in self.graph:
            if str(s) not in results:
                results[str(s)] = {}
            results[str(s)][str(p)] = str(o)
        return results

class AgentRegistry:
    """Registry for managing agent discovery and coordination."""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.capabilities: Dict[str, Set[str]] = {}  # capability -> set of agent_ids
        self.knowledge_graph = KnowledgeGraph()
        
    async def register_agent(self, agent: BaseAgent, capabilities: List[str]) -> None:
        """Register an agent and its capabilities."""
        self.agents[agent.agent_id] = agent
        agent.knowledge_graph = self.knowledge_graph
        
        # Register agent in knowledge graph
        await self.knowledge_graph.add_triple(
            f"agent:{agent.agent_id}",
            str(RDF.type),
            str(DM.Agent)
        )
        
        # Register capabilities
        for capability in capabilities:
            if capability not in self.capabilities:
                self.capabilities[capability] = set()
            self.capabilities[capability].add(agent.agent_id)
            
            await self.knowledge_graph.add_triple(
                f"agent:{agent.agent_id}",
                str(DM.hasCapability),
                f"capability:{capability}"
            )
            
    async def find_agents_for_capability(self, capability: str) -> List[str]:
        """Find agents that can provide a specific capability."""
        return list(self.capabilities.get(capability, set()))
        
    async def route_message(self, message: AgentMessage) -> AgentMessage:
        """Route a message to the appropriate agent."""
        if message.recipient in self.agents:
            return await self.agents[message.recipient].process_message(message)
        return AgentMessage(
            sender="registry",
            recipient=message.sender,
            content={"error": "Agent not found"},
            timestamp=message.timestamp,
            message_type="error"
        )

class BaseAgent:
    """Base class for all agents."""
    
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.knowledge_graph = None
        self.logger = logging.getLogger(agent_id)
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        self.logger.info(f"{self.agent_type} Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        raise NotImplementedError
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph."""
        raise NotImplementedError
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph."""
        raise NotImplementedError
        
    async def _handle_unknown_message(self, message: AgentMessage) -> AgentMessage:
        """Handle unknown message types."""
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"error": f"Unknown message type: {message.message_type}"},
            timestamp=message.timestamp,
            message_type="error"
        )

class ResearchAgent(BaseAgent):
    """Agent capable of conducting research."""
    
    def __init__(self, agent_id: str = "research_agent"):
        super().__init__(agent_id, "researcher")
        
    async def initialize(self) -> None:
        self.logger.info("Research Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "research_request":
            return await self._handle_research_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with research findings."""
        await self.knowledge_graph.update_graph({
            f"research:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Research),
                str(DM.topic): update_data.get('topic', ''),
                str(DM.findings): str(update_data.get('findings', []))
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for research information."""
        return await self.knowledge_graph.query(query)
        
    async def _handle_research_request(self, message: AgentMessage) -> AgentMessage:
        # Simulate research
        findings = [
            "AI can analyze large datasets of medical records",
            "Machine learning models assist in diagnosis",
            "Access to AI tools varies by region"
        ]
        
        # Update knowledge graph
        await self.update_knowledge_graph({
            'topic': message.content['topic'],
            'findings': findings
        })
        
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"findings": findings},
            timestamp=message.timestamp,
            message_type="research_response"
        )

class AnalysisAgent(BaseAgent):
    """Agent capable of analyzing research findings."""
    
    def __init__(self, agent_id: str = "analysis_agent"):
        super().__init__(agent_id, "analyst")
        
    async def initialize(self) -> None:
        self.logger.info("Analysis Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "analysis_request":
            return await self._handle_analysis_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with analysis results."""
        await self.knowledge_graph.update_graph({
            f"analysis:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Analysis),
                str(DM.pros): str(update_data.get('pros', [])),
                str(DM.cons): str(update_data.get('cons', []))
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for analysis information."""
        return await self.knowledge_graph.query(query)
        
    async def _handle_analysis_request(self, message: AgentMessage) -> AgentMessage:
        findings = message.content.get("findings", [])
        
        # Simulate analysis
        analysis = {
            "pros": [
                "Scales expertise across hospitals",
                "Finds patterns humans might miss"
            ],
            "cons": [
                "Requires high-quality data",
                "Potential for false positives"
            ]
        }
        
        # Update knowledge graph
        await self.update_knowledge_graph(analysis)
        
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"analysis": analysis},
            timestamp=message.timestamp,
            message_type="analysis_response"
        )

class CoordinatorAgent(BaseAgent):
    """Agent that coordinates other agents to complete tasks."""
    
    def __init__(self, agent_id: str = "coordinator_agent"):
        super().__init__(agent_id, "coordinator")
        self.registry = None
        
    async def initialize(self) -> None:
        self.logger.info("Coordinator Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "task_request":
            return await self._handle_task_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with task coordination information."""
        await self.knowledge_graph.update_graph({
            f"task:{update_data.get('task_id', 'latest')}": {
                str(RDF.type): str(DM.Task),
                str(DM.status): update_data.get('status', ''),
                str(DM.coordinator): self.agent_id
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for task information."""
        return await self.knowledge_graph.query(query)
        
    async def _handle_task_request(self, message: AgentMessage) -> AgentMessage:
        # Update knowledge graph with new task
        await self.update_knowledge_graph({
            'task_id': 'task_1',
            'status': 'in_progress'
        })
        
        # Find agents for research
        research_agents = await self.registry.find_agents_for_capability("research")
        if not research_agents:
            return await self._handle_unknown_message(message)
            
        # Request research
        research_request = AgentMessage(
            sender=self.agent_id,
            recipient=research_agents[0],
            content={"topic": message.content["topic"]},
            timestamp=message.timestamp,
            message_type="research_request"
        )
        research_response = await self.registry.route_message(research_request)
        
        # Find agents for analysis
        analysis_agents = await self.registry.find_agents_for_capability("analysis")
        if not analysis_agents:
            return await self._handle_unknown_message(message)
            
        # Request analysis
        analysis_request = AgentMessage(
            sender=self.agent_id,
            recipient=analysis_agents[0],
            content={"findings": research_response.content["findings"]},
            timestamp=message.timestamp,
            message_type="analysis_request"
        )
        analysis_response = await self.registry.route_message(analysis_request)
        
        # Update knowledge graph with completed task
        await self.update_knowledge_graph({
            'task_id': 'task_1',
            'status': 'completed'
        })
        
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={
                "research": research_response.content,
                "analysis": analysis_response.content
            },
            timestamp=message.timestamp,
            message_type="task_response"
        )

class KnowledgeGraphConsultantAgent(BaseAgent):
    """
    Knowledge Graph Consultant Persona
    ----------------------------------
    - Expert in ontology design, semantic modeling, and best practices.
    - Provides consulting on how to model concepts, align with standards, and use external vocabularies.
    - Capability: 'consulting'
    """
    def __init__(self, agent_id: str = "kg_consultant_agent"):
        super().__init__(agent_id, "consultant")
    async def initialize(self) -> None:
        self.logger.info("Knowledge Graph Consultant initialized")
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "consulting_request":
            return await self._handle_consulting_request(message)
        return await self._handle_unknown_message(message)
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"consulting:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Consulting),
                str(DM.advice): update_data.get('advice', '')
            }
        })
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
    async def _handle_consulting_request(self, message: AgentMessage) -> AgentMessage:
        # Simulate consulting advice
        advice = (
            "For disease modeling, use MONDO or DOID as base classes. "
            "Align symptoms with HPO. Use owl:equivalentClass for exact mappings."
        )
        await self.update_knowledge_graph({'advice': advice})
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"advice": advice},
            timestamp=message.timestamp,
            message_type="consulting_response"
        )

class KnowledgeGraphEngineerAgent(BaseAgent):
    """
    Knowledge Graph Engineer (OpenI Expert) Persona
    ----------------------------------------------
    - Senior engineer with expertise in building, querying, and optimizing knowledge graphs.
    - Can write SPARQL queries, design ingestion pipelines, and optimize graph storage.
    - Capability: 'engineering'
    """
    def __init__(self, agent_id: str = "kg_engineer_agent"):
        super().__init__(agent_id, "engineer")
    async def initialize(self) -> None:
        self.logger.info("Knowledge Graph Engineer initialized")
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "engineering_request":
            return await self._handle_engineering_request(message)
        return await self._handle_unknown_message(message)
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"engineering:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Engineering),
                str(DM.sparql): update_data.get('sparql', '')
            }
        })
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
    async def _handle_engineering_request(self, message: AgentMessage) -> AgentMessage:
        # Simulate SPARQL query design
        sparql = (
            "SELECT ?disease WHERE { ?disease rdf:type :Disease ; :hasSymptom :Fever . }"
        )
        await self.update_knowledge_graph({'sparql': sparql})
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"sparql": sparql},
            timestamp=message.timestamp,
            message_type="engineering_response"
        )

class KnowledgeGraphVPAgent(BaseAgent):
    """
    Knowledge Graph VP/Lead Persona
    ------------------------------
    - Executive/lead who can take complex business or technical queries, break them down, and coordinate the right experts.
    - Delegates to consultant and engineer, then assembles a comprehensive answer (including code if needed).
    - Capability: 'leadership'
    """
    def __init__(self, agent_id: str = "kg_vp_agent"):
        super().__init__(agent_id, "vp_lead")
        self.registry = None
    async def initialize(self) -> None:
        self.logger.info("Knowledge Graph VP/Lead initialized")
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "complex_query":
            return await self._handle_complex_query(message)
        return await self._handle_unknown_message(message)
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"leadership:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Leadership),
                str(DM.summary): update_data.get('summary', '')
            }
        })
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
    async def _handle_complex_query(self, message: AgentMessage) -> AgentMessage:
        # Delegate to consultant for modeling advice
        consultant_agents = await self.registry.find_agents_for_capability("consulting")
        engineer_agents = await self.registry.find_agents_for_capability("engineering")
        if not consultant_agents or not engineer_agents:
            return await self._handle_unknown_message(message)
        consulting_request = AgentMessage(
            sender=self.agent_id,
            recipient=consultant_agents[0],
            content={"problem": message.content["problem"]},
            timestamp=message.timestamp,
            message_type="consulting_request"
        )
        consulting_response = await self.registry.route_message(consulting_request)
        engineering_request = AgentMessage(
            sender=self.agent_id,
            recipient=engineer_agents[0],
            content={"requirement": message.content["problem"]},
            timestamp=message.timestamp,
            message_type="engineering_request"
        )
        engineering_response = await self.registry.route_message(engineering_request)
        # Assemble final answer
        summary = (
            f"Consulting Advice: {consulting_response.content['advice']}\n"
            f"SPARQL Query Example: {engineering_response.content['sparql']}"
        )
        await self.update_knowledge_graph({'summary': summary})
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={
                "consulting": consulting_response.content['advice'],
                "sparql": engineering_response.content['sparql'],
                "summary": summary
            },
            timestamp=message.timestamp,
            message_type="complex_query_response"
        )

class OntologyDesignerAgent(BaseAgent):
    """
    Layer 1: Ontology Designer Agent
    -------------------------------
    - Specializes in high-level ontology design and architecture
    - Creates foundational class hierarchies and property definitions
    - Capability: 'ontology_design'
    """
    def __init__(self, agent_id: str = "ontology_designer_agent"):
        super().__init__(agent_id, "ontology_designer")
        
    async def initialize(self) -> None:
        self.logger.info("Ontology Designer Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "ontology_design_request":
            return await self._handle_ontology_design_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"ontology_design:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.OntologyDesign),
                str(DM.class_hierarchy): update_data.get('class_hierarchy', ''),
                str(DM.property_definitions): update_data.get('property_definitions', '')
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_ontology_design_request(self, message: AgentMessage) -> AgentMessage:
        design = {
            'class_hierarchy': """
                :Disease rdf:type owl:Class ;
                    rdfs:subClassOf :MedicalCondition .
                :Symptom rdf:type owl:Class ;
                    rdfs:subClassOf :ClinicalFeature .
            """,
            'property_definitions': """
                :hasSymptom rdf:type owl:ObjectProperty ;
                    rdfs:domain :Disease ;
                    rdfs:range :Symptom .
            """
        }
        await self.update_knowledge_graph(design)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=design,
            timestamp=message.timestamp,
            message_type="ontology_design_response"
        )

class SemanticAlignmentAgent(BaseAgent):
    """
    Layer 2: Semantic Alignment Agent
    -------------------------------
    - Specializes in aligning ontologies with external standards
    - Maps concepts to existing biomedical ontologies
    - Capability: 'semantic_alignment'
    """
    def __init__(self, agent_id: str = "semantic_alignment_agent"):
        super().__init__(agent_id, "semantic_alignment")
        
    async def initialize(self) -> None:
        self.logger.info("Semantic Alignment Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "alignment_request":
            return await self._handle_alignment_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"alignment:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Alignment),
                str(DM.mappings): update_data.get('mappings', ''),
                str(DM.equivalences): update_data.get('equivalences', '')
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_alignment_request(self, message: AgentMessage) -> AgentMessage:
        mappings = {
            'mappings': """
                :Disease owl:equivalentClass mondo:Disease .
                :Symptom owl:equivalentClass hpo:Phenotype .
            """,
            'equivalences': """
                :Fever owl:equivalentClass hpo:0001945 .
                :Diabetes owl:equivalentClass mondo:0005148 .
            """
        }
        await self.update_knowledge_graph(mappings)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=mappings,
            timestamp=message.timestamp,
            message_type="alignment_response"
        )

class QueryOptimizationAgent(BaseAgent):
    """
    Layer 3: Query Optimization Agent
    -------------------------------
    - Specializes in optimizing SPARQL queries for performance
    - Analyzes and improves query patterns
    - Capability: 'query_optimization'
    """
    def __init__(self, agent_id: str = "query_optimization_agent"):
        super().__init__(agent_id, "query_optimizer")
        
    async def initialize(self) -> None:
        self.logger.info("Query Optimization Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "optimization_request":
            return await self._handle_optimization_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"optimization:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Optimization),
                str(DM.original_query): update_data.get('original_query', ''),
                str(DM.optimized_query): update_data.get('optimized_query', ''),
                str(DM.improvements): update_data.get('improvements', '')
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_optimization_request(self, message: AgentMessage) -> AgentMessage:
        optimization = {
            'original_query': message.content.get('query', ''),
            'optimized_query': """
                SELECT ?disease WHERE {
                    ?disease rdf:type :Disease ;
                            :hasSymptom ?symptom .
                    ?symptom rdf:type :Fever .
                }
            """,
            'improvements': [
                "Added type constraint for better index usage",
                "Simplified property path",
                "Added specific class filter"
            ]
        }
        await self.update_knowledge_graph(optimization)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=optimization,
            timestamp=message.timestamp,
            message_type="optimization_response"
        )

class DataIngestionAgent(BaseAgent):
    """
    Layer 5: Data Ingestion Agent
    ---------------------------
    - Handles data loading and transformation
    - Manages ETL pipelines
    - Capability: 'data_ingestion'
    """
    def __init__(self, agent_id: str = "data_ingestion_agent"):
        super().__init__(agent_id, "data_ingestion")
        
    async def initialize(self) -> None:
        self.logger.info("Data Ingestion Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "ingestion_request":
            return await self._handle_ingestion_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"ingestion:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Ingestion),
                str(DM.pipeline): update_data.get('pipeline', ''),
                str(DM.transformations): update_data.get('transformations', '')
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_ingestion_request(self, message: AgentMessage) -> AgentMessage:
        pipeline = {
            'pipeline': """
                LOAD <http://example.org/diseases.ttl>
                INTO GRAPH <http://example.org/medical>
            """,
            'transformations': [
                "Normalize disease names",
                "Map to standard codes",
                "Validate relationships"
            ]
        }
        await self.update_knowledge_graph(pipeline)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=pipeline,
            timestamp=message.timestamp,
            message_type="ingestion_response"
        )

class ValidationAgent(BaseAgent):
    """
    Layer 6: Validation Agent
    -----------------------
    - Ensures data quality and consistency
    - Performs integrity checks
    - Capability: 'validation'
    """
    def __init__(self, agent_id: str = "validation_agent"):
        super().__init__(agent_id, "validator")
        
    async def initialize(self) -> None:
        self.logger.info("Validation Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "validation_request":
            return await self._handle_validation_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"validation:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Validation),
                str(DM.checks): update_data.get('checks', ''),
                str(DM.results): update_data.get('results', '')
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_validation_request(self, message: AgentMessage) -> AgentMessage:
        validation = {
            'checks': [
                "Verify class hierarchy consistency",
                "Check property domain/range constraints",
                "Validate external ontology mappings"
            ],
            'results': {
                "status": "passed",
                "issues": [],
                "recommendations": ["Add more specific property constraints"]
            }
        }
        await self.update_knowledge_graph(validation)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=validation,
            timestamp=message.timestamp,
            message_type="validation_response"
        )

class ReasoningAgent(BaseAgent):
    """
    Layer 7: Reasoning Agent
    ----------------------
    - Manages OWL reasoning and inference
    - Handles complex logical operations
    - Capability: 'reasoning'
    """
    def __init__(self, agent_id: str = "reasoning_agent"):
        super().__init__(agent_id, "reasoner")
        
    async def initialize(self) -> None:
        self.logger.info("Reasoning Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "reasoning_request":
            return await self._handle_reasoning_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"reasoning:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Reasoning),
                str(DM.inferences): update_data.get('inferences', ''),
                str(DM.rules): update_data.get('rules', '')
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_reasoning_request(self, message: AgentMessage) -> AgentMessage:
        reasoning = {
            'rules': """
                :hasSymptom owl:propertyChainAxiom (:hasPart :hasSymptom) .
                :Disease owl:equivalentClass [
                    owl:intersectionOf (
                        :MedicalCondition
                        [ owl:onProperty :hasSymptom ;
                          owl:someValuesFrom :Fever ]
                    )
                ] .
            """,
            'inferences': [
                "All diseases with fever are medical conditions",
                "Symptoms are transitive through part-of relationships"
            ]
        }
        await self.update_knowledge_graph(reasoning)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=reasoning,
            timestamp=message.timestamp,
            message_type="reasoning_response"
        )

class PerformanceAgent(BaseAgent):
    """
    Layer 8: Performance Agent
    ------------------------
    - Optimizes graph database performance
    - Manages indexes and caching
    - Capability: 'performance'
    """
    def __init__(self, agent_id: str = "performance_agent"):
        super().__init__(agent_id, "performance")
        
    async def initialize(self) -> None:
        self.logger.info("Performance Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "performance_request":
            return await self._handle_performance_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"performance:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Performance),
                str(DM.indexes): update_data.get('indexes', ''),
                str(DM.optimizations): update_data.get('optimizations', '')
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_performance_request(self, message: AgentMessage) -> AgentMessage:
        performance = {
            'indexes': [
                "CREATE INDEX ON :Disease(hasSymptom)",
                "CREATE INDEX ON :Symptom(type)"
            ],
            'optimizations': [
                "Enable query caching",
                "Configure memory settings",
                "Optimize batch operations"
            ]
        }
        await self.update_knowledge_graph(performance)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=performance,
            timestamp=message.timestamp,
            message_type="performance_response"
        )

class SecurityAgent(BaseAgent):
    """
    Layer 9: Security Agent
    ---------------------
    - Manages access control and security
    - Handles data protection
    - Capability: 'security'
    """
    def __init__(self, agent_id: str = "security_agent"):
        super().__init__(agent_id, "security")
        
    async def initialize(self) -> None:
        self.logger.info("Security Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "security_request":
            return await self._handle_security_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"security:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Security),
                str(DM.policies): update_data.get('policies', ''),
                str(DM.permissions): update_data.get('permissions', '')
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_security_request(self, message: AgentMessage) -> AgentMessage:
        security = {
            'policies': [
                "Encrypt sensitive medical data",
                "Implement role-based access control",
                "Audit all data access"
            ],
            'permissions': {
                "researchers": ["read", "query"],
                "doctors": ["read", "write", "query"],
                "patients": ["read"]
            }
        }
        await self.update_knowledge_graph(security)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=security,
            timestamp=message.timestamp,
            message_type="security_response"
        )

class MonitoringAgent(BaseAgent):
    """
    Layer 10: Monitoring Agent
    ------------------------
    - Tracks system health and performance
    - Manages alerts and metrics
    - Capability: 'monitoring'
    """
    def __init__(self, agent_id: str = "monitoring_agent"):
        super().__init__(agent_id, "monitor")
        
    async def initialize(self) -> None:
        self.logger.info("Monitoring Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "monitoring_request":
            return await self._handle_monitoring_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"monitoring:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Monitoring),
                str(DM.metrics): update_data.get('metrics', ''),
                str(DM.alerts): update_data.get('alerts', '')
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_monitoring_request(self, message: AgentMessage) -> AgentMessage:
        monitoring = {
            'metrics': [
                "Query response time",
                "Memory usage",
                "Triple count",
                "Reasoning time"
            ],
            'alerts': {
                "thresholds": {
                    "response_time": "> 1s",
                    "memory_usage": "> 80%",
                    "error_rate": "> 1%"
                }
            }
        }
        await self.update_knowledge_graph(monitoring)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=monitoring,
            timestamp=message.timestamp,
            message_type="monitoring_response"
        )

class IntegrationAgent(BaseAgent):
    """
    Layer 11: Integration Agent
    -------------------------
    - Manages external system integration
    - Handles API and service connections
    - Capability: 'integration'
    """
    def __init__(self, agent_id: str = "integration_agent"):
        super().__init__(agent_id, "integration")
        
    async def initialize(self) -> None:
        self.logger.info("Integration Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "integration_request":
            return await self._handle_integration_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"integration:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Integration),
                str(DM.connections): update_data.get('connections', ''),
                str(DM.endpoints): update_data.get('endpoints', '')
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_integration_request(self, message: AgentMessage) -> AgentMessage:
        integration = {
            'connections': [
                "MONDO Disease Ontology API",
                "HPO Phenotype API",
                "SNOMED CT Terminology Service"
            ],
            'endpoints': {
                "mondo": "https://api.monarchinitiative.org/api/",
                "hpo": "https://hpo.jax.org/api/",
                "snomed": "https://browser.ihtsdotools.org/api/"
            }
        }
        await self.update_knowledge_graph(integration)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=integration,
            timestamp=message.timestamp,
            message_type="integration_response"
        )

class ProvenanceAgent(BaseAgent):
    """
    Layer 12: Provenance Agent
    - Tracks data and model provenance, evidence, and source.
    - Capability: 'provenance'
    """
    def __init__(self, agent_id="provenance_agent"):
        super().__init__(agent_id, "provenance")
    async def initialize(self): self.logger.info("Provenance Agent initialized")
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "provenance_request":
            return await self._handle_provenance_request(message)
        return await self._handle_unknown_message(message)
    async def update_knowledge_graph(self, update_data):
        await self.knowledge_graph.update_graph({
            f"provenance:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Provenance),
                str(DM.source): update_data.get('source', ''),
                str(DM.evidence): update_data.get('evidence', '')
            }
        })
    async def query_knowledge_graph(self, query): return await self.knowledge_graph.query(query)
    async def _handle_provenance_request(self, message: AgentMessage) -> AgentMessage:
        provenance = {'source': "MONDO API", 'evidence': "PMID:123456"}
        await self.update_knowledge_graph(provenance)
        return AgentMessage(sender_id=self.agent_id, recipient_id=message.sender_id, content=provenance, timestamp=message.timestamp, message_type="provenance_response")

class HardwareAgent(BaseAgent):
    """
    Layer 13: Hardware Agent
    - Monitors and manages hardware resources.
    - Capability: 'hardware'
    """
    def __init__(self, agent_id="hardware_agent"):
        super().__init__(agent_id, "hardware")
    async def initialize(self): self.logger.info("Hardware Agent initialized")
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "hardware_request":
            return await self._handle_hardware_request(message)
        return await self._handle_unknown_message(message)
    async def update_knowledge_graph(self, update_data):
        await self.knowledge_graph.update_graph({
            f"hardware:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Hardware),
                str(DM.cpu): update_data.get('cpu', ''),
                str(DM.memory): update_data.get('memory', ''),
                str(DM.disk): update_data.get('disk', '')
            }
        })
    async def query_knowledge_graph(self, query): return await self.knowledge_graph.query(query)
    async def _handle_hardware_request(self, message: AgentMessage) -> AgentMessage:
        hardware = {'cpu': "Intel Xeon", 'memory': "128GB", 'disk': "2TB SSD"}
        await self.update_knowledge_graph(hardware)
        return AgentMessage(sender_id=self.agent_id, recipient_id=message.sender_id, content=hardware, timestamp=message.timestamp, message_type="hardware_response")

class ComplianceAgent(BaseAgent):
    """
    Layer 14: Compliance Agent
    - Ensures regulatory compliance (e.g., HIPAA, GDPR).
    - Capability: 'compliance'
    """
    def __init__(self, agent_id="compliance_agent"):
        super().__init__(agent_id, "compliance")
    async def initialize(self): self.logger.info("Compliance Agent initialized")
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "compliance_request":
            return await self._handle_compliance_request(message)
        return await self._handle_unknown_message(message)
    async def update_knowledge_graph(self, update_data):
        await self.knowledge_graph.update_graph({
            f"compliance:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Compliance),
                str(DM.standards): update_data.get('standards', ''),
                str(DM.status): update_data.get('status', '')
            }
        })
    async def query_knowledge_graph(self, query): return await self.knowledge_graph.query(query)
    async def _handle_compliance_request(self, message: AgentMessage) -> AgentMessage:
        compliance = {'standards': ["HIPAA", "GDPR"], 'status': "compliant"}
        await self.update_knowledge_graph(compliance)
        return AgentMessage(sender_id=self.agent_id, recipient_id=message.sender_id, content=compliance, timestamp=message.timestamp, message_type="compliance_response")

class DiseaseOntologyAgent(BaseAgent):
    """
    Biomedical Domain: Disease Ontology Agent
    - Handles disease-specific ontology tasks.
    - Capability: 'disease_ontology'
    """
    def __init__(self, agent_id="disease_ontology_agent"):
        super().__init__(agent_id, "disease_ontology")
    async def initialize(self): self.logger.info("Disease Ontology Agent initialized")
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "disease_ontology_request":
            return await self._handle_disease_ontology_request(message)
        return await self._handle_unknown_message(message)
    async def update_knowledge_graph(self, update_data):
        await self.knowledge_graph.update_graph({
            f"disease_ontology:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.DiseaseOntology),
                str(DM.label): update_data.get('label', ''),
                str(DM.external_id): update_data.get('external_id', '')
            }
        })
    async def query_knowledge_graph(self, query): return await self.knowledge_graph.query(query)
    async def _handle_disease_ontology_request(self, message: AgentMessage) -> AgentMessage:
        # Stub: In real use, query MONDO or other API
        disease = {'label': "Type 2 Diabetes Mellitus", 'external_id': "MONDO:0005148"}
        await self.update_knowledge_graph(disease)
        return AgentMessage(sender_id=self.agent_id, recipient_id=message.sender_id, content=disease, timestamp=message.timestamp, message_type="disease_ontology_response")

class NewsIngestionAgent(BaseAgent):
    """
    News Ingestion Agent
    -------------------
    - Ingests daily news from various sources
    - Extracts entities, relationships, and sentiment
    - Capability: 'news_ingestion'
    """
    def __init__(self, agent_id="news_ingestion_agent"):
        super().__init__(agent_id, "news_ingestion")
        
    async def initialize(self):
        self.logger.info("News Ingestion Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "news_ingestion_request":
            return await self._handle_news_ingestion_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data):
        await self.knowledge_graph.update_graph({
            f"news:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.NewsArticle),
                str(DM.title): update_data.get('title', ''),
                str(DM.content): update_data.get('content', ''),
                str(DM.source): update_data.get('source', ''),
                str(DM.publication_date): update_data.get('publication_date', ''),
                str(DM.entities): update_data.get('entities', []),
                str(DM.sentiment): update_data.get('sentiment', '')
            }
        })
        
    async def query_knowledge_graph(self, query):
        return await self.knowledge_graph.query(query)
        
    async def _handle_news_ingestion_request(self, message: AgentMessage) -> AgentMessage:
        # Simulate news ingestion
        news_data = {
            'title': "Tech Giant Announces AI Breakthrough",
            'content': "Company X unveiled a new AI model that could revolutionize healthcare diagnostics.",
            'source': "Tech Daily",
            'publication_date': "2024-03-20",
            'entities': ["Company X", "AI", "healthcare"],
            'sentiment': "positive"
        }
        await self.update_knowledge_graph(news_data)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=news_data,
            timestamp=message.timestamp,
            message_type="news_ingestion_response"
        )

class StockImpactAgent(BaseAgent):
    """
    Stock Impact Agent
    ----------------
    - Analyzes news impact on stocks
    - Tracks market reactions and correlations
    - Capability: 'stock_impact'
    """
    def __init__(self, agent_id="stock_impact_agent"):
        super().__init__(agent_id, "stock_impact")
        
    async def initialize(self):
        self.logger.info("Stock Impact Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "stock_impact_request":
            return await self._handle_stock_impact_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data):
        await self.knowledge_graph.update_graph({
            f"stock_impact:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.StockImpact),
                str(DM.company): update_data.get('company', ''),
                str(DM.news_article): update_data.get('news_article', ''),
                str(DM.price_change): update_data.get('price_change', ''),
                str(DM.volume_change): update_data.get('volume_change', ''),
                str(DM.impact_score): update_data.get('impact_score', '')
            }
        })
        
    async def query_knowledge_graph(self, query):
        return await self.knowledge_graph.query(query)
        
    async def _handle_stock_impact_request(self, message: AgentMessage) -> AgentMessage:
        # Simulate stock impact analysis
        impact_data = {
            'company': "Company X",
            'news_article': "Tech Giant Announces AI Breakthrough",
            'price_change': "+5.2%",
            'volume_change': "+150%",
            'impact_score': "high"
        }
        await self.update_knowledge_graph(impact_data)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=impact_data,
            timestamp=message.timestamp,
            message_type="stock_impact_response"
        )

class ShortTermMemoryAgent(BaseAgent):
    """
    Short Term Memory Agent
    ---------------------
    - Maintains recent knowledge graph state
    - Manages temporal relationships and relevance
    - Capability: 'short_term_memory'
    """
    def __init__(self, agent_id="short_term_memory_agent"):
        super().__init__(agent_id, "short_term_memory")
        self.memory_window = 24  # hours
        
    async def initialize(self):
        self.logger.info("Short Term Memory Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "memory_request":
            return await self._handle_memory_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data):
        await self.knowledge_graph.update_graph({
            f"memory:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.MemoryEntry),
                str(DM.timestamp): update_data.get('timestamp', ''),
                str(DM.content): update_data.get('content', ''),
                str(DM.relevance_score): update_data.get('relevance_score', ''),
                str(DM.relationships): update_data.get('relationships', [])
            }
        })
        
    async def query_knowledge_graph(self, query):
        return await self.knowledge_graph.query(query)
        
    async def _handle_memory_request(self, message: AgentMessage) -> AgentMessage:
        # Simulate memory management
        memory_data = {
            'timestamp': "2024-03-20T10:00:00Z",
            'content': "Recent news about Company X's AI breakthrough",
            'relevance_score': 0.85,
            'relationships': [
                "Company X -> AI Development",
                "AI Development -> Healthcare Impact",
                "Healthcare Impact -> Stock Performance"
            ]
        }
        await self.update_knowledge_graph(memory_data)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=memory_data,
            timestamp=message.timestamp,
            message_type="memory_response"
        )

class KnowledgeGraphArchitectAgent(BaseAgent):
    """
    Layer 4: Knowledge Graph Architect Agent (Updated)
    -----------------------------------------------
    - Coordinates all layers of knowledge graph development
    - Capability: 'architecture'
    """
    def __init__(self, agent_id: str = "kg_architect_agent"):
        super().__init__(agent_id, "architect")
        self.registry = None
    async def initialize(self) -> None:
        self.logger.info("Knowledge Graph Architect Agent initialized")
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "architecture_request":
            return await self._handle_architecture_request(message)
        return await self._handle_unknown_message(message)
    async def update_knowledge_graph(self, update_data: dict) -> None:
        await self.knowledge_graph.update_graph({
            f"architecture:{update_data.get('id', 'latest')}": update_data
        })
    async def query_knowledge_graph(self, query: dict) -> dict:
        return await self.knowledge_graph.query(query)
    async def _handle_architecture_request(self, message: AgentMessage) -> AgentMessage:
        # Get responses from all layers
        layers = {
            "ontology_design": await self._get_layer_response("ontology_design", message),
            "semantic_alignment": await self._get_layer_response("semantic_alignment", message),
            "query_optimization": await self._get_layer_response("query_optimization", message),
            "data_ingestion": await self._get_layer_response("data_ingestion", message),
            "validation": await self._get_layer_response("validation", message),
            "reasoning": await self._get_layer_response("reasoning", message),
            "performance": await self._get_layer_response("performance", message),
            "security": await self._get_layer_response("security", message),
            "monitoring": await self._get_layer_response("monitoring", message),
            "integration": await self._get_layer_response("integration", message),
            "provenance": await self._get_layer_response("provenance", message),
            "hardware": await self._get_layer_response("hardware", message),
            "compliance": await self._get_layer_response("compliance", message),
            "disease_ontology": await self._get_layer_response("disease_ontology", message),
            "news_ingestion": await self._get_layer_response("news_ingestion", message),
            "stock_impact": await self._get_layer_response("stock_impact", message),
            "short_term_memory": await self._get_layer_response("short_term_memory", message)
        }
        await self.update_knowledge_graph(layers)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=layers,
            timestamp=message.timestamp,
            message_type="architecture_response"
        )
    async def _get_layer_response(self, capability: str, original_message: AgentMessage) -> AgentMessage:
        agents = await self.registry.find_agents_for_capability(capability)
        if not agents:
            return await self._handle_unknown_message(original_message)
        request = AgentMessage(
            sender=self.agent_id,
            recipient=agents[0],
            content=original_message.content,
            timestamp=original_message.timestamp,
            message_type=f"{capability}_request"
        )
        return await self.registry.route_message(request)

class TavilyWebSearchAgent(BaseAgent):
    """
    Tavily Web Search Agent
    ----------------------
    - Performs web search for news and information
    - Extracts entities and facts from search results
    - Capability: 'web_search'
    """
    def __init__(self, agent_id="tavily_web_search_agent"):
        super().__init__(agent_id, "web_search")

    async def initialize(self):
        self.logger.info("Tavily Web Search Agent initialized")

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "web_search_request":
            return await self._handle_web_search_request(message)
        return await self._handle_unknown_message(message)

    async def update_knowledge_graph(self, update_data):
        await self.knowledge_graph.update_graph({
            f"web_search:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.WebSearchResult),
                str(DM.query): update_data.get('query', ''),
                str(DM.results): str(update_data.get('results', []))
            }
        })

    async def query_knowledge_graph(self, query):
        return await self.knowledge_graph.query(query)

    async def _handle_web_search_request(self, message: AgentMessage) -> AgentMessage:
        query = message.content.get("query", "")
        # Simulate web search results
        results = [
            {
                "title": "AI Revolutionizes Healthcare Diagnostics",
                "snippet": "A new AI model is helping doctors diagnose rare diseases more accurately.",
                "url": "https://news.example.com/ai-healthcare"
            },
            {
                "title": "Tech Giant Announces AI Breakthrough",
                "snippet": "Company X unveiled a new AI model that could revolutionize healthcare diagnostics.",
                "url": "https://news.example.com/ai-breakthrough"
            },
            {
                "title": "Stock Markets React to AI News",
                "snippet": "Shares of Company X surged after the AI announcement.",
                "url": "https://news.example.com/stock-ai"
            }
        ]
        await self.update_knowledge_graph({"query": query, "results": results})
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"results": results},
            timestamp=message.timestamp,
            message_type="web_search_response"
        )

class DeepWebResearchAgent(BaseAgent):
    """
    Deep Web Research Agent
    ----------------------
    - Performs in-depth web research, aggregates and synthesizes information
    - Updates the knowledge graph with synthesized findings
    - Capability: 'deep_web_research'
    """
    def __init__(self, agent_id="deep_web_research_agent"):
        super().__init__(agent_id, "deep_web_research")

    async def initialize(self):
        self.logger.info("Deep Web Research Agent initialized")

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "deep_web_research_request":
            return await self._handle_deep_web_research_request(message)
        return await self._handle_unknown_message(message)

    async def update_knowledge_graph(self, update_data):
        await self.knowledge_graph.update_graph({
            f"deep_web_research:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.DeepWebResearch),
                str(DM.query): update_data.get('query', ''),
                str(DM.synthesis): update_data.get('synthesis', '')
            }
        })

    async def query_knowledge_graph(self, query):
        return await self.knowledge_graph.query(query)

    async def _handle_deep_web_research_request(self, message: AgentMessage) -> AgentMessage:
        query = message.content.get("query", "")
        # Simulate deep research synthesis
        synthesis = (
            "Synthesized findings from 10+ sources: "
            "AI is rapidly transforming healthcare diagnostics, with recent breakthroughs "
            "in rare disease detection, imaging, and patient data analysis. Key players include Company X, "
            "OpenAI, and Google Health."
        )
        await self.update_knowledge_graph({"query": query, "synthesis": synthesis})
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"synthesis": synthesis},
            timestamp=message.timestamp,
            message_type="deep_web_research_response"
        )

class DirectorAgent(BaseAgent):
    """
    Director Agent
    --------------
    - Orchestrates research, consults with knowledge graph experts, and coordinates agent teams
    - Capability: 'director'
    """
    def __init__(self, agent_id="director_agent"):
        super().__init__(agent_id, "director")
        self.registry = None

    async def initialize(self):
        self.logger.info("Director Agent initialized")

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "director_request":
            return await self._handle_director_request(message)
        return await self._handle_unknown_message(message)

    async def update_knowledge_graph(self, update_data):
        await self.knowledge_graph.update_graph({
            f"director:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.Director),
                str(DM.summary): update_data.get('summary', '')
            }
        })

    async def query_knowledge_graph(self, query):
        return await self.knowledge_graph.query(query)

    async def _handle_director_request(self, message: AgentMessage) -> AgentMessage:
        # Consult with knowledge graph experts (consultant, engineer, vp)
        consultant_agents = await self.registry.find_agents_for_capability("consulting")
        engineer_agents = await self.registry.find_agents_for_capability("engineering")
        vp_agents = await self.registry.find_agents_for_capability("leadership")
        responses = []
        if consultant_agents:
            consulting_request = AgentMessage(
                sender=self.agent_id,
                recipient=consultant_agents[0],
                content={"problem": message.content.get("problem", "")},
                timestamp=message.timestamp,
                message_type="consulting_request"
            )
            consulting_response = await self.registry.route_message(consulting_request)
            responses.append(f"Consultant: {consulting_response.content.get('advice', '')}")
        if engineer_agents:
            engineering_request = AgentMessage(
                sender=self.agent_id,
                recipient=engineer_agents[0],
                content={"requirement": message.content.get("problem", "")},
                timestamp=message.timestamp,
                message_type="engineering_request"
            )
            engineering_response = await self.registry.route_message(engineering_request)
            responses.append(f"Engineer: {engineering_response.content.get('sparql', '')}")
        if vp_agents:
            vp_request = AgentMessage(
                sender=self.agent_id,
                recipient=vp_agents[0],
                content={"problem": message.content.get("problem", "")},
                timestamp=message.timestamp,
                message_type="complex_query"
            )
            vp_response = await self.registry.route_message(vp_request)
            responses.append(f"VP: {vp_response.content.get('summary', '')}")
        summary = " | ".join(responses)
        await self.update_knowledge_graph({"summary": summary})
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"summary": summary},
            timestamp=message.timestamp,
            message_type="director_response"
        )

class SoftwareEngineeringTeamAgent(BaseAgent):
    """
    Software Engineering Team Agent
    ------------------------------
    - Simulates a team of engineers with profiles from Google, OpenAI, and Mira Murati
    - Capability: 'software_engineering_team'
    """
    def __init__(self, agent_id="software_engineering_team_agent"):
        super().__init__(agent_id, "software_engineering_team")
        self.team_profiles = [
            {"name": "Alice", "role": "Senior Software Engineer", "company": "Google", "skills": ["Python", "Distributed Systems", "Knowledge Graphs"]},
            {"name": "Bob", "role": "AI Research Engineer", "company": "OpenAI", "skills": ["Machine Learning", "NLP", "SPARQL"]},
            {"name": "Mira Murati", "role": "CTO", "company": "OpenAI", "skills": ["Leadership", "AI Strategy", "Product"]}
        ]

    async def initialize(self):
        self.logger.info("Software Engineering Team Agent initialized")

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "software_engineering_team_request":
            return await self._handle_team_request(message)
        return await self._handle_unknown_message(message)

    async def update_knowledge_graph(self, update_data):
        await self.knowledge_graph.update_graph({
            f"software_engineering_team:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.SoftwareEngineeringTeam),
                str(DM.team_profiles): str(self.team_profiles)
            }
        })

    async def query_knowledge_graph(self, query):
        return await self.knowledge_graph.query(query)

    async def _handle_team_request(self, message: AgentMessage) -> AgentMessage:
        await self.update_knowledge_graph({})
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"team_profiles": self.team_profiles},
            timestamp=message.timestamp,
            message_type="software_engineering_team_response"
        )

async def run_self_assembly_demo():
    """
    Demonstrate agent self-assembly and coordination with all layers.
    """
    # Create registry
    registry = AgentRegistry()
    
    # Create all agents
    agents = {
        "ontology_designer": OntologyDesignerAgent(),
        "semantic_aligner": SemanticAlignmentAgent(),
        "query_optimizer": QueryOptimizationAgent(),
        "kg_architect": KnowledgeGraphArchitectAgent(),
        "data_ingestion": DataIngestionAgent(),
        "validator": ValidationAgent(),
        "reasoner": ReasoningAgent(),
        "performance": PerformanceAgent(),
        "security": SecurityAgent(),
        "monitor": MonitoringAgent(),
        "integration": IntegrationAgent(),
        "provenance": ProvenanceAgent(),
        "hardware": HardwareAgent(),
        "compliance": ComplianceAgent(),
        "disease_ontology": DiseaseOntologyAgent(),
        "news_ingestion": NewsIngestionAgent(),
        "stock_impact": StockImpactAgent(),
        "short_term_memory": ShortTermMemoryAgent(),
        "tavily_web_search": TavilyWebSearchAgent(),
        "deep_web_research": DeepWebResearchAgent(),
        "director": DirectorAgent(),
        "software_engineering_team": SoftwareEngineeringTeamAgent()
    }
    
    # Set registry references
    agents["kg_architect"].registry = registry
    agents["director"].registry = registry
    
    # Register all agents with their capabilities
    capabilities = {
        "ontology_designer": ["ontology_design"],
        "semantic_aligner": ["semantic_alignment"],
        "query_optimizer": ["query_optimization"],
        "kg_architect": ["architecture"],
        "data_ingestion": ["data_ingestion"],
        "validator": ["validation"],
        "reasoner": ["reasoning"],
        "performance": ["performance"],
        "security": ["security"],
        "monitor": ["monitoring"],
        "integration": ["integration"],
        "provenance": ["provenance"],
        "hardware": ["hardware"],
        "compliance": ["compliance"],
        "disease_ontology": ["disease_ontology"],
        "news_ingestion": ["news_ingestion"],
        "stock_impact": ["stock_impact"],
        "short_term_memory": ["short_term_memory"],
        "tavily_web_search": ["web_search"],
        "deep_web_research": ["deep_web_research"],
        "director": ["director"],
        "software_engineering_team": ["software_engineering_team"]
    }
    
    for agent_id, agent in agents.items():
        await registry.register_agent(agent, capabilities[agent_id])
        await agent.initialize()
    
    # Create a complex architecture request
    architecture_request = AgentMessage(
        sender="user",
        recipient="kg_architect_agent",
        content={
            "domain": "Financial News Analysis",
            "query": "Analyze impact of tech news on stock market",
            "requirements": {
                "news_sources": ["Tech Daily", "Financial Times"],
                "stock_data": "Real-time market data",
                "memory_window": "24 hours"
            }
        },
        timestamp=0.0,
        message_type="architecture_request"
    )
    
    # Process the architecture request
    response = await registry.route_message(architecture_request)
    
    print("\nKnowledge Graph Architecture Response:")
    for layer, content in response.content.items():
        print(f"\n{layer.upper()}:")
        print(content)
    
    # Test TavilyWebSearchAgent
    print("\nTavily Web Search Agent Demo:")
    web_search_request = AgentMessage(
        sender="user",
        recipient="tavily_web_search_agent",
        content={"query": "AI in healthcare"},
        timestamp=0.0,
        message_type="web_search_request"
    )
    web_search_response = await registry.route_message(web_search_request)
    print(web_search_response.content)

    # Test DeepWebResearchAgent
    print("\nDeep Web Research Agent Demo:")
    deep_research_request = AgentMessage(
        sender="user",
        recipient="deep_web_research_agent",
        content={"query": "AI in healthcare"},
        timestamp=0.0,
        message_type="deep_web_research_request"
    )
    deep_research_response = await registry.route_message(deep_research_request)
    print(deep_research_response.content)

    # Test DirectorAgent
    print("\nDirector Agent Demo:")
    director_request = AgentMessage(
        sender="user",
        recipient="director_agent",
        content={"problem": "How should we model AI impact on healthcare in the knowledge graph?"},
        timestamp=0.0,
        message_type="director_request"
    )
    director_response = await registry.route_message(director_request)
    print(director_response.content)

    # Test SoftwareEngineeringTeamAgent
    print("\nSoftware Engineering Team Agent Demo:")
    team_request = AgentMessage(
        sender="user",
        recipient="software_engineering_team_agent",
        content={},
        timestamp=0.0,
        message_type="software_engineering_team_request"
    )
    team_response = await registry.route_message(team_request)
    print(team_response.content)
    
    # Print knowledge graph contents
    print("\nKnowledge Graph Contents:")
    for s, p, o in registry.knowledge_graph.graph:
        print(f"{s} {p} {o}")

if __name__ == "__main__":
    asyncio.run(run_self_assembly_demo()) 