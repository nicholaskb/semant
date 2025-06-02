from typing import Dict, Any, List, Optional, Set
from agents.core.base_agent import BaseAgent, AgentMessage
from agents.core.capability_types import Capability, CapabilityType
from loguru import logger
import asyncio
from datetime import datetime
import json
from rdflib import URIRef
from rdflib.namespace import RDF

class AgenticPromptAgent(BaseAgent):
    """
    Agent responsible for managing agentic prompting and code review.
    This agent helps guide other agents through structured prompting and review processes.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "agentic_prompt",
        capabilities: Optional[Set[Capability]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            agent_id,
            agent_type,
            capabilities or {
                Capability(CapabilityType.CODE_REVIEW),
                Capability(CapabilityType.KNOWLEDGE_GRAPH_QUERY),
                Capability(CapabilityType.KNOWLEDGE_GRAPH_UPDATE)
            },
            config
        )
        # Load prompt templates from config if provided
        if config is not None and 'prompt_templates' in config:
            self.prompt_templates: Dict[str, Dict[str, Any]] = config['prompt_templates']
        else:
            self.prompt_templates: Dict[str, Dict[str, Any]] = {}
        self.review_history: List[Dict[str, Any]] = []
        self.consensus_threshold = config.get('consensus_threshold', 0.75) if config else 0.75
        
    async def initialize(self) -> None:
        """Initialize the agentic prompt agent."""
        await super().initialize()
        self.logger.info("Agentic Prompt Agent initialized")
        
        # Register agent in knowledge graph
        if self.knowledge_graph:
            await self.knowledge_graph.update_graph({
                f"agent:{self.agent_id}": {
                    "rdf:type": "prompt:AgenticPromptAgent",
                    "prompt:hasStatus": "prompt:Active",
                    "prompt:consensusThreshold": str(self.consensus_threshold)
                }
            })
            
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages for agentic prompting and review."""
        try:
            if message.message_type == "prompt_request":
                return await self._handle_prompt_request(message)
            elif message.message_type == "review_request":
                return await self._handle_review_request(message)
            elif message.message_type == "template_request":
                return await self._handle_template_request(message)
            else:
                return await self._handle_unknown_message(message)
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"error": str(e)},
                timestamp=message.timestamp,
                message_type="error"
            )
            
    async def _handle_prompt_request(self, message: AgentMessage) -> AgentMessage:
        """Handle requests for agentic prompting."""
        try:
            prompt_type = message.content.get('prompt_type')
            context = message.content.get('context', {})
            objective = message.content.get('objective')
            
            if not all([prompt_type, objective]):
                raise ValueError("Missing required prompt parameters")
                
            # Generate structured prompt
            prompt = await self._generate_prompt(prompt_type, context, objective)
            
            # Store prompt in history
            self.review_history.append({
                'timestamp': datetime.now().isoformat(),
                'prompt_type': prompt_type,
                'context': context,
                'objective': objective,
                'prompt': prompt
            })
            
            # Update knowledge graph (add triple directly for test validation)
            kg = self.knowledge_graph
            if kg is not None:
                if hasattr(kg, 'graph'):
                    kg = kg.graph
                kg.add((
                    URIRef(f"prompt:{prompt_type}"),
                    RDF.type,
                    URIRef("prompt:Prompt")
                ))
            # Also update via update_graph for other info
            if self.knowledge_graph and hasattr(self.knowledge_graph, 'update_graph'):
                await self.knowledge_graph.update_graph({
                    f"prompt:{prompt_type}": {
                        "rdf:type": "prompt:Prompt",
                        "prompt:generatedBy": f"agent:{self.agent_id}",
                        "prompt:timestamp": datetime.now().isoformat(),
                        "prompt:content": json.dumps(prompt)
                    }
                })
            
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"prompt": prompt},
                timestamp=message.timestamp,
                message_type="prompt_response"
            )
        except Exception as e:
            self.logger.error(f"Error handling prompt request: {str(e)}")
            raise
            
    async def _handle_review_request(self, message: AgentMessage) -> AgentMessage:
        """Handle code review requests with agentic prompting."""
        try:
            code_artifact = message.content.get('code_artifact')
            review_type = message.content.get('review_type', 'general')
            
            if not code_artifact:
                raise ValueError("No code artifact provided for review")
                
            # Generate review prompt
            review_prompt = await self._generate_prompt(
                'code_review',
                {'code': code_artifact},
                f"Review code for {review_type} issues"
            )
            
            # Perform review
            review_result = await self._perform_review(code_artifact, review_prompt)
            
            # Store review in history
            self.review_history.append({
                'timestamp': datetime.now().isoformat(),
                'artifact': code_artifact,
                'review_type': review_type,
                'prompt': review_prompt,
                'result': review_result
            })
            
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"review_result": review_result},
                timestamp=message.timestamp,
                message_type="review_response"
            )
        except Exception as e:
            self.logger.error(f"Error handling review request: {str(e)}")
            raise
            
    async def _handle_template_request(self, message: AgentMessage) -> AgentMessage:
        """Handle requests for prompt templates."""
        try:
            template_type = message.content.get('template_type')
            if not template_type:
                raise ValueError("No template type specified")
                
            template = self.prompt_templates.get(template_type)
            if not template:
                raise ValueError(f"Template not found: {template_type}")
                
            return AgentMessage(
                sender=self.agent_id,
                recipient=message.sender,
                content={"template": template},
                timestamp=message.timestamp,
                message_type="template_response"
            )
        except Exception as e:
            self.logger.error(f"Error handling template request: {str(e)}")
            raise
            
    async def _generate_prompt(
        self,
        prompt_type: str,
        context: Dict[str, Any],
        objective: str
    ) -> Dict[str, Any]:
        """Generate a structured prompt based on type and context."""
        template = self.prompt_templates.get(prompt_type, {
            "role": "You are a {role} specializing in {specialization}.",
            "context": "Context:\n{context}",
            "objective": "Objective:\n{objective}",
            "approach": "Approach:\n{approach}",
            "documentation": "Documentation:\n{documentation}"
        })
        
        # Fill template with context
        prompt = {
            "role": template["role"].format(
                role=context.get('role', 'expert'),
                specialization=context.get('specialization', 'general')
            ),
            "context": template["context"].format(
                context=json.dumps(context, indent=2)
            ),
            "objective": template["objective"].format(
                objective=objective
            ),
            "approach": template["approach"].format(
                approach=context.get('approach', 'Follow best practices')
            ),
            "documentation": template["documentation"].format(
                documentation=context.get('documentation', 'Document all changes')
            )
        }
        
        return prompt
        
    async def _perform_review(
        self,
        code_artifact: Dict[str, Any],
        review_prompt: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform code review using agentic prompting."""
        review_result = {
            'status': 'pending',
            'findings': [],
            'recommendations': []
        }
        
        # Implement review logic based on capabilities
        if await self.has_capability(CapabilityType.CODE_REVIEW):
            # Add code review findings
            pass
            
        if await self.has_capability(CapabilityType.KNOWLEDGE_GRAPH_QUERY):
            # Query knowledge graph for similar issues
            pass
            
        return review_result
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with prompt and review information."""
        if self.knowledge_graph:
            await self.knowledge_graph.update_graph(update_data)
            
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for prompt and review information."""
        if not self.knowledge_graph:
            return {}
        return await self.knowledge_graph.query_graph(query.get('sparql', '')) 