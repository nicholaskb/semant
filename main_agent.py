import logging
import os
from agents.core.reasoner import KnowledgeGraphReasoner
from rdflib import Graph, Namespace, Literal, URIRef
from uuid import uuid4
from kg.models import Artifact, ARTIFACT
from typing import List, Dict, Any
from datetime import datetime
from tavily import TavilyClient
from dotenv import load_dotenv
import pathlib

# Load environment variables from .env file
env_path = pathlib.Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class MainAgent:
    def __init__(self):
        self.graph = Graph()
        self.dMaster = Namespace("http://example.org/dMaster/")
        self.graph.bind("dMaster", self.dMaster)
        self.reasoner = KnowledgeGraphReasoner(graph=self.graph)
        self.feedback_log = []
        self.artifacts = []  # Store Artifact objects
        
        # Initialize Tavily client if API key is available
        api_key = os.getenv('TAVILY_API_KEY')
        if api_key:
            self.tavily = TavilyClient(api_key=api_key)
            logger.info("Tavily client initialized with API key")
        else:
            self.tavily = None
            logger.warning("Tavily API key not found. Research capabilities will be limited.")
        
        logger.info("MainAgent initialized.")

    def store_artifact(self, content, author):
        artifact_id = str(uuid4())
        artifact = Artifact(artifact_id, content, author)
        self.artifacts.append(artifact)
        for triple in artifact.to_triples():
            self.graph.add(triple)
        logger.info(f"Artifact stored: {artifact_id} by {author}")
        return artifact_id

    async def handle_investigate(self, topic: str):
        """Enhanced investigation with Tavily integration."""
        logger.info(f"Investigate called with topic: {topic}")
        
        if not self.tavily:
            logger.warning("Tavily client not initialized. Using basic investigation.")
            return await self.reasoner.investigate_research_topic(topic)
        
        try:
            # 1. Query Tavily for research papers
            tavily_results = await self.tavily.search(topic)
            
            # 2. Process results and update knowledge graph
            processed_data = self._process_tavily_results(tavily_results)
            self._update_knowledge_graph(processed_data)
            
            # 3. Get insights from reasoner
            analysis = await self.reasoner.investigate_research_topic(topic)
            
            # 4. Store investigation as artifact
            self.store_artifact(
                f"Investigation of topic: {topic}",
                "MainAgent"
            )
            
            return {
                'confidence': analysis['confidence'],
                'key_insights': analysis['key_insights'],
                'sources': processed_data['papers'],
                'related_concepts': analysis['related_concepts']
            }
        except Exception as e:
            logger.error(f"Error during investigation: {e}")
            return await self.reasoner.investigate_research_topic(topic)

    def _process_tavily_results(self, results):
        """Process Tavily search results into structured data."""
        processed = {
            'papers': [],
            'concepts': set(),
            'relationships': []
        }
        
        for result in results:
            paper = {
                'id': str(uuid4()),
                'title': result.get('title', ''),
                'author': result.get('author', ''),
                'year': result.get('year', ''),
                'topic': result.get('topic', ''),
                'insights': result.get('insights', '')
            }
            processed['papers'].append(paper)
            
            # Extract concepts and relationships
            if 'concepts' in result:
                processed['concepts'].update(result['concepts'])
            if 'relationships' in result:
                processed['relationships'].extend(result['relationships'])
        
        return processed

    def _update_knowledge_graph(self, data):
        """Update knowledge graph with processed research data."""
        for paper in data['papers']:
            paper_uri = self.dMaster[paper['id']]
            self.graph.add((paper_uri, self.dMaster.title, Literal(paper['title'])))
            self.graph.add((paper_uri, self.dMaster.author, Literal(paper['author'])))
            self.graph.add((paper_uri, self.dMaster.year, Literal(paper['year'])))
            self.graph.add((paper_uri, self.dMaster.topic, Literal(paper['topic'])))
            self.graph.add((paper_uri, self.dMaster.insights, Literal(paper['insights'])))
        
        # Add semantic relationships
        for rel in data['relationships']:
            source = self.dMaster[rel['source']]
            target = self.dMaster[rel['target']]
            self.graph.add((source, self.dMaster[rel['type']], target))

    async def handle_traverse(self, start_node: str, max_depth: int = 2):
        logger.info(f"Traverse called with start_node: {start_node}, max_depth: {max_depth}")
        return await self.reasoner.traverse_knowledge_graph(start_node, max_depth)

    def handle_feedback(self, feedback: str):
        self.feedback_log.append(feedback)
        logger.info(f"Feedback received: {feedback}")
        return {"status": "received", "feedback": feedback}

    async def handle_chat(self, message: str, history: list) -> dict:
        logger.info(f"Chat received: {message} | history: {history}")

        chain_of_thought = [
            "Received a new message.",
            "Analyzing the message content.",
            "Considering the conversation history.",
            "Planning multi-agent interaction strategy."
        ]

        artifact_id = str(uuid4())
        self.artifacts.append(Artifact(
            artifact_id=artifact_id,
            content=message,
            author="User",
            timestamp=datetime.now().isoformat()
        ))
        logger.info(f"Artifact stored: {artifact_id} by User")

        response_components = []
        research_topics = []
        traversal_results = None

        if message.lower() == "help":
            response = (
                "I'm here to assist you! I can help with:\n"
                "1. Research and investigation\n"
                "2. Knowledge graph traversal\n"
                "3. Answering questions\n"
                "4. Providing insights\n\n"
                "Just let me know what you'd like to explore!"
            )
        else:
            if len(message.split()) > 3:
                research_topics.append(message)
                chain_of_thought.append("Identified potential research topic.")

            if research_topics:
                try:
                    research_results = await self.handle_investigate(research_topics[0])
                    response_components.append(f"Research findings: {research_results['key_insights']}")
                    chain_of_thought.append("Conducted research investigation.")
                except Exception as e:
                    logger.error(f"Research error: {e}")

            try:
                traversal_results = await self.handle_traverse(message, max_depth=2)
                if traversal_results:
                    response_components.append(f"Related concepts: {traversal_results}")
                    chain_of_thought.append("Traversed knowledge graph for related concepts.")
            except Exception as e:
                logger.error(f"Traversal error: {e}")

            if response_components:
                response = "I've been busy analyzing your message! Here's what I found:\n\n" + "\n".join(response_components)
            else:
                response = "I'm processing your request and consulting with my knowledge base. Let me know if you'd like me to investigate any specific aspects further."

        response_artifact_id = str(uuid4())
        self.artifacts.append(Artifact(
            artifact_id=response_artifact_id,
            content=response,
            author="MainAgent",
            timestamp=datetime.now().isoformat()
        ))
        logger.info(f"Artifact stored: {response_artifact_id} by MainAgent")

        # Update conversation history as a list of strings
        updated_history = history + [message]

        logger.info(f"Chat response: {response}")

        return {
            "response": response,
            "history": updated_history,
            "agent": "MainAgent",
            "chain_of_thought": chain_of_thought,
            "activities": {
                "research_conducted": bool(research_topics),
                "graph_traversed": bool(traversal_results),
                "artifacts_created": 2
            }
        } 