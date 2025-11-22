import asyncio
from typing import Dict, Any, List, Set
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS
from agents.core.base_agent import BaseAgent, AgentMessage
from demo_self_assembly import AgentRegistry, KnowledgeGraph
import logging
from agents.core.ttl_validation_agent import TTLValidationAgent
from agents.core.remote_kg_agent import RemoteKGAgent

# Define namespaces
DM = Namespace("http://example.org/demo/")
AGENT = Namespace("http://example.org/demo/agent/")
CAPABILITY = Namespace("http://example.org/demo/capability/")

class VPEngineeringAgent(BaseAgent):
    """
    VP of Engineering Agent
    ----------------------
    - Senior engineering leader with startup mentality
    - Oversees technical strategy and team coordination
    - Capability: 'vp_engineering'
    """
    def __init__(self, agent_id: str = "vp_engineering_agent"):
        super().__init__(agent_id, "vp_engineering")
        self.registry = None
        
    async def initialize(self) -> None:
        self.logger.info("VP of Engineering Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "engineering_strategy_request":
            return await self._handle_strategy_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"engineering_strategy:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.EngineeringStrategy),
                str(DM.strategy): update_data.get('strategy', ''),
                str(DM.priorities): str(update_data.get('priorities', []))
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_strategy_request(self, message: AgentMessage) -> AgentMessage:
        strategy = {
            'strategy': "Focus on scalable, maintainable code with strong testing",
            'priorities': [
                "Implement CI/CD pipeline",
                "Establish code review process",
                "Set up monitoring and logging",
                "Define technical standards"
            ]
        }
        await self.update_knowledge_graph(strategy)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=strategy,
            timestamp=message.timestamp,
            message_type="engineering_strategy_response"
        )

class HeadOfMLAgent(BaseAgent):
    """
    Head of ML/AI Agent
    ------------------
    - Expert in machine learning and AI development
    - Leads AI strategy and implementation
    - Capability: 'head_ml'
    """
    def __init__(self, agent_id: str = "head_ml_agent"):
        super().__init__(agent_id, "head_ml")
        
    async def initialize(self) -> None:
        self.logger.info("Head of ML Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "ml_strategy_request":
            return await self._handle_ml_strategy_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"ml_strategy:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.MLStrategy),
                str(DM.approach): update_data.get('approach', ''),
                str(DM.models): str(update_data.get('models', []))
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_ml_strategy_request(self, message: AgentMessage) -> AgentMessage:
        strategy = {
            'approach': "Implement state-of-the-art ML models with focus on explainability",
            'models': [
                "Transformer-based language models",
                "Graph neural networks for knowledge graphs",
                "Reinforcement learning for optimization"
            ]
        }
        await self.update_knowledge_graph(strategy)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=strategy,
            timestamp=message.timestamp,
            message_type="ml_strategy_response"
        )

class SeniorOpenAIAgent(BaseAgent):
    """
    Senior OpenAI Engineer Agent
    --------------------------
    - Expert in OpenAI technologies and implementations
    - Specializes in GPT and other OpenAI models
    - Capability: 'openai_expert'
    """
    def __init__(self, agent_id: str = "senior_openai_agent"):
        super().__init__(agent_id, "openai_expert")
        
    async def initialize(self) -> None:
        self.logger.info("Senior OpenAI Engineer Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "openai_implementation_request":
            return await self._handle_implementation_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"openai_implementation:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.OpenAIImplementation),
                str(DM.model): update_data.get('model', ''),
                str(DM.implementation): update_data.get('implementation', '')
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_implementation_request(self, message: AgentMessage) -> AgentMessage:
        implementation = {
            'model': "GPT-4",
            'implementation': """
                - Fine-tune for specific domain
                - Implement proper error handling
                - Add rate limiting and caching
                - Set up monitoring and logging
            """
        }
        await self.update_knowledge_graph(implementation)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=implementation,
            timestamp=message.timestamp,
            message_type="openai_implementation_response"
        )

class MiraMuratiAgent(BaseAgent):
    """
    Mira Murati Agent
    ----------------
    - Expert in AI strategy and implementation
    - Specializes in cutting-edge AI technologies
    - Capability: 'ai_strategy'
    """
    def __init__(self, agent_id: str = "mira_murati_agent"):
        super().__init__(agent_id, "ai_strategy")
        
    async def initialize(self) -> None:
        self.logger.info("Mira Murati Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "ai_strategy_request":
            return await self._handle_ai_strategy_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"ai_strategy:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.AIStrategy),
                str(DM.vision): update_data.get('vision', ''),
                str(DM.recommendations): str(update_data.get('recommendations', []))
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_ai_strategy_request(self, message: AgentMessage) -> AgentMessage:
        strategy = {
            'vision': "Build scalable, ethical AI systems that solve real-world problems",
            'recommendations': [
                "Focus on model interpretability",
                "Implement robust testing frameworks",
                "Ensure ethical AI practices",
                "Build for scalability from day one"
            ]
        }
        await self.update_knowledge_graph(strategy)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=strategy,
            timestamp=message.timestamp,
            message_type="ai_strategy_response"
        )

class SamAltmanAgent(BaseAgent):
    """
    Sam Altman Agent
    ---------------
    - Expert in startup strategy and AI implementation
    - Specializes in scaling AI products
    - Capability: 'startup_strategy'
    """
    def __init__(self, agent_id: str = "sam_altman_agent"):
        super().__init__(agent_id, "startup_strategy")
        
    async def initialize(self) -> None:
        self.logger.info("Sam Altman Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "startup_strategy_request":
            return await self._handle_startup_strategy_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"startup_strategy:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.StartupStrategy),
                str(DM.advice): update_data.get('advice', ''),
                str(DM.priorities): str(update_data.get('priorities', []))
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_startup_strategy_request(self, message: AgentMessage) -> AgentMessage:
        strategy = {
            'advice': "Focus on building a great product that solves real problems",
            'priorities': [
                "Ship fast and iterate",
                "Build strong technical foundation",
                "Focus on user experience",
                "Scale efficiently"
            ]
        }
        await self.update_knowledge_graph(strategy)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=strategy,
            timestamp=message.timestamp,
            message_type="startup_strategy_response"
        )

class OntologySoftwareDeveloperAgent(BaseAgent):
    """
    Ontology Software Developer Agent
    -------------------------------
    - Expert in ontology and semantic web technologies
    - Specializes in knowledge graph implementation
    - Capability: 'ontology_development'
    """
    def __init__(self, agent_id: str = "ontology_developer_agent"):
        super().__init__(agent_id, "ontology_development")
        
    async def initialize(self) -> None:
        self.logger.info("Ontology Software Developer Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "ontology_development_request":
            return await self._handle_development_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"ontology_development:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.OntologyDevelopment),
                str(DM.implementation): update_data.get('implementation', ''),
                str(DM.best_practices): str(update_data.get('best_practices', []))
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_development_request(self, message: AgentMessage) -> AgentMessage:
        development = {
            'implementation': """
                - Use RDF/OWL for ontology modeling
                - Implement SPARQL endpoints
                - Set up reasoning capabilities
            """,
            'best_practices': [
                "Follow OBO Foundry principles",
                "Use standard vocabularies",
                "Implement proper versioning",
                "Document all classes and properties"
            ]
        }
        await self.update_knowledge_graph(development)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=development,
            timestamp=message.timestamp,
            message_type="ontology_development_response"
        )

class FullStackDeveloperAgent(BaseAgent):
    """
    Full Stack Developer Agent
    ------------------------
    - Expert in full stack development
    - Specializes in scalable web applications
    - Capability: 'full_stack_development'
    """
    def __init__(self, agent_id: str = "full_stack_developer_agent"):
        super().__init__(agent_id, "full_stack_development")
        
    async def initialize(self) -> None:
        self.logger.info("Full Stack Developer Agent initialized")
        
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        if message.message_type == "full_stack_development_request":
            return await self._handle_development_request(message)
        return await self._handle_unknown_message(message)
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        await self.knowledge_graph.update_graph({
            f"full_stack_development:{update_data.get('id', 'latest')}": {
                str(RDF.type): str(DM.FullStackDevelopment),
                str(DM.architecture): update_data.get('architecture', ''),
                str(DM.technologies): str(update_data.get('technologies', []))
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        return await self.knowledge_graph.query(query)
        
    async def _handle_development_request(self, message: AgentMessage) -> AgentMessage:
        development = {
            'architecture': "Microservices with event-driven design",
            'technologies': [
                "Python/FastAPI for backend",
                "React/TypeScript for frontend",
                "PostgreSQL for database",
                "Redis for caching",
                "Docker for containerization"
            ]
        }
        await self.update_knowledge_graph(development)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=development,
            timestamp=message.timestamp,
            message_type="full_stack_development_response"
        )

async def run_coding_team_demo():
    """
    Demonstrate the coding team agents working together, including TTL validation and remote KG access.
    """
    # Create registry
    registry = AgentRegistry()
    
    # Create all agents
    agents = {
        "vp_engineering": VPEngineeringAgent(),
        "head_ml": HeadOfMLAgent(),
        "senior_openai": SeniorOpenAIAgent(),
        "mira_murati": MiraMuratiAgent(),
        "sam_altman": SamAltmanAgent(),
        "ontology_developer": OntologySoftwareDeveloperAgent(),
        "full_stack_developer": FullStackDeveloperAgent(),
        "ttl_validator": TTLValidationAgent(),
        "remote_kg": RemoteKGAgent(query_endpoint="http://example.org/sparql")
    }
    
    # Register all agents with their capabilities
    capabilities = {
        "vp_engineering": ["vp_engineering"],
        "head_ml": ["head_ml"],
        "senior_openai": ["openai_expert"],
        "mira_murati": ["ai_strategy"],
        "sam_altman": ["startup_strategy"],
        "ontology_developer": ["ontology_development"],
        "full_stack_developer": ["full_stack_development"],
        "ttl_validator": ["ttl_validation"],
        "remote_kg": ["remote_kg"]
    }
    
    for agent_id, agent in agents.items():
        await registry.register_agent(agent, capabilities[agent_id])
        await agent.initialize()
    
    # Test VP Engineering
    print("\nVP Engineering Strategy:")
    vp_request = AgentMessage(
        sender="user",
        recipient="vp_engineering_agent",
        content={"request": "What's our engineering strategy?"},
        timestamp=0.0,
        message_type="engineering_strategy_request"
    )
    vp_response = await registry.route_message(vp_request)
    print(vp_response.content)
    
    # Test Head of ML
    print("\nML Strategy:")
    ml_request = AgentMessage(
        sender="user",
        recipient="head_ml_agent",
        content={"request": "What's our ML strategy?"},
        timestamp=0.0,
        message_type="ml_strategy_request"
    )
    ml_response = await registry.route_message(ml_request)
    print(ml_response.content)
    
    # Test Senior OpenAI Engineer
    print("\nOpenAI Implementation:")
    openai_request = AgentMessage(
        sender="user",
        recipient="senior_openai_agent",
        content={"request": "How should we implement OpenAI?"},
        timestamp=0.0,
        message_type="openai_implementation_request"
    )
    openai_response = await registry.route_message(openai_request)
    print(openai_response.content)
    
    # Test Mira Murati
    print("\nAI Strategy:")
    mira_request = AgentMessage(
        sender="user",
        recipient="mira_murati_agent",
        content={"request": "What's our AI strategy?"},
        timestamp=0.0,
        message_type="ai_strategy_request"
    )
    mira_response = await registry.route_message(mira_request)
    print(mira_response.content)
    
    # Test Sam Altman
    print("\nStartup Strategy:")
    sam_request = AgentMessage(
        sender="user",
        recipient="sam_altman_agent",
        content={"request": "What's our startup strategy?"},
        timestamp=0.0,
        message_type="startup_strategy_request"
    )
    sam_response = await registry.route_message(sam_request)
    print(sam_response.content)
    
    # Test Ontology Developer
    print("\nOntology Development:")
    ontology_request = AgentMessage(
        sender="user",
        recipient="ontology_developer_agent",
        content={"request": "How should we develop our ontology?"},
        timestamp=0.0,
        message_type="ontology_development_request"
    )
    ontology_response = await registry.route_message(ontology_request)
    print(ontology_response.content)
    
    # Test Full Stack Developer
    print("\nFull Stack Development:")
    full_stack_request = AgentMessage(
        sender="user",
        recipient="full_stack_developer_agent",
        content={"request": "What's our full stack architecture?"},
        timestamp=0.0,
        message_type="full_stack_development_request"
    )
    full_stack_response = await registry.route_message(full_stack_request)
    print(full_stack_response.content)

    # Test TTL Validation Agent
    print("\nTTL Validation:")
    ttl_request = AgentMessage(
        sender="user",
        recipient="ttl_validation_agent",
        content={"file_path": "a message to get you started (change here)"},
        timestamp=0.0,
        message_type="ttl_validation_request"
    )
    ttl_response = await registry.route_message(ttl_request)
    print(ttl_response.content)
    
    # Test Remote KG Agent (SPARQL query demo)
    print("\nRemote KG SPARQL Query:")
    sparql_query = "SELECT * WHERE { ?s ?p ?o } LIMIT 1"
    remote_kg_request = AgentMessage(
        sender="user",
        recipient="remote_kg_agent",
        content={"query": sparql_query},
        timestamp=0.0,
        message_type="sparql_query"
    )
    remote_kg_response = await registry.route_message(remote_kg_request)
    print(remote_kg_response.content)

if __name__ == "__main__":
    asyncio.run(run_coding_team_demo()) 