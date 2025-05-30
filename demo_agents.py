import asyncio
from typing import Dict, Any
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS
from agents.core.base_agent import BaseAgent, AgentMessage
from agents.domain.corporate_knowledge_agent import CorporateKnowledgeAgent

# Define namespaces
DM = Namespace("http://example.org/demo/")
TASK = Namespace("http://example.org/demo/task/")
AGENT = Namespace("http://example.org/demo/agent/")

class KnowledgeGraph:
    """Simple wrapper around RDFLib Graph for async operations."""
    
    def __init__(self):
        self.graph = Graph()
        self.graph.bind("dm", DM)
        self.graph.bind("task", TASK)
        self.graph.bind("agent", AGENT)
        
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
                    
    async def query(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Query the graph."""
        # Simple query implementation
        results = {}
        for s, p, o in self.graph:
            if str(s) not in results:
                results[str(s)] = {}
            results[str(s)][str(p)] = str(o)
        return results

class SimpleTaskAgent(BaseAgent):
    """A simple agent that can process tasks and communicate with other agents."""
    
    def __init__(self, agent_id: str = "task_agent"):
        super().__init__(agent_id, "task_processor")
        self.tasks = {}
        self.knowledge_graph = KnowledgeGraph()
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        self.logger.info("Task Agent initialized")
        # Register agent in knowledge graph
        await self.knowledge_graph.add_triple(
            f"agent:{self.agent_id}",
            str(RDF.type),
            str(DM.TaskAgent)
        )
        
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        if message.message_type == "task_request":
            return await self._handle_task_request(message)
        elif message.message_type == "knowledge_response":
            return await self._handle_knowledge_response(message)
        else:
            return await self._handle_unknown_message(message)
            
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with task information."""
        await self.knowledge_graph.update_graph({
            f"task:{update_data['task_id']}": {
                str(RDF.type): str(DM.Task),
                str(DM.status): update_data['status'],
                str(DM.description): update_data['description']
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for task information."""
        return await self.knowledge_graph.query(query)
        
    async def _handle_task_request(self, message: AgentMessage) -> AgentMessage:
        """Handle a new task request."""
        task_id = f"task_{len(self.tasks) + 1}"
        self.tasks[task_id] = message.content
        
        # Update knowledge graph
        await self.update_knowledge_graph({
            'task_id': task_id,
            'status': 'pending',
            'description': message.content['description']
        })
        
        # Request knowledge from corporate knowledge agent
        knowledge_request = AgentMessage(
            sender=self.agent_id,
            recipient="corporate_knowledge_agent",
            content={'type': 'knowledge_query', 'task_id': task_id},
            timestamp=message.timestamp,
            message_type="knowledge_query"
        )
        await self.send_message(knowledge_request.recipient, knowledge_request.content, knowledge_request.message_type)
        
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={'status': 'processing', 'task_id': task_id},
            timestamp=message.timestamp,
            message_type="task_response"
        )
        
    async def _handle_knowledge_response(self, message: AgentMessage) -> AgentMessage:
        """Handle response from knowledge agent."""
        task_id = message.content['task_id']
        if task_id in self.tasks:
            self.tasks[task_id]['knowledge'] = message.content['results']
            await self.update_knowledge_graph({
                'task_id': task_id,
                'status': 'completed',
                'description': self.tasks[task_id]['description']
            })
            
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={'status': 'success', 'task_id': task_id},
            timestamp=message.timestamp,
            message_type="task_complete"
        )
        
    async def _handle_unknown_message(self, message: AgentMessage) -> AgentMessage:
        """Handle unknown message types."""
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={'status': 'error', 'message': 'Unknown message type'},
            timestamp=message.timestamp,
            message_type="error_response"
        )

class CorporateKnowledgeAgent(BaseAgent):
    """A simple knowledge agent that manages documents and knowledge."""
    
    def __init__(self, agent_id: str = "corporate_knowledge_agent"):
        super().__init__(agent_id, "knowledge_manager")
        self.documents = {}
        self.knowledge_graph = KnowledgeGraph()
        
    async def initialize(self) -> None:
        """Initialize the agent."""
        self.logger.info("Knowledge Agent initialized")
        # Register agent in knowledge graph
        await self.knowledge_graph.add_triple(
            f"agent:{self.agent_id}",
            str(RDF.type),
            str(DM.KnowledgeAgent)
        )
        
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages."""
        if message.message_type == "knowledge_query":
            return await self._handle_knowledge_query(message)
        else:
            return await self._handle_unknown_message(message)
            
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with document information."""
        await self.knowledge_graph.update_graph({
            f"doc:{update_data['doc_id']}": {
                str(RDF.type): str(DM.Document),
                str(DM.title): update_data['title'],
                str(DM.content): update_data['content']
            }
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for document information."""
        return await self.knowledge_graph.query(query)
        
    async def _handle_knowledge_query(self, message: AgentMessage) -> AgentMessage:
        """Handle knowledge query requests."""
        # Simulate document retrieval
        documents = [
            {'title': 'AI in Healthcare', 'content': 'AI is transforming healthcare...'},
            {'title': 'Machine Learning in Medicine', 'content': 'ML applications in medicine...'}
        ]
        
        # Store documents in knowledge graph
        for i, doc in enumerate(documents):
            await self.update_knowledge_graph({
                'doc_id': f"doc_{i+1}",
                'title': doc['title'],
                'content': doc['content']
            })
            
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={
                'task_id': message.content['task_id'],
                'results': {'documents': documents}
            },
            timestamp=message.timestamp,
            message_type="knowledge_response"
        )
        
    async def _handle_unknown_message(self, message: AgentMessage) -> AgentMessage:
        """Handle unknown message types."""
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={'status': 'error', 'message': 'Unknown message type'},
            timestamp=message.timestamp,
            message_type="error_response"
        )

async def run_demo():
    """Run a demonstration of agent interaction."""
    # Create agents
    task_agent = SimpleTaskAgent()
    knowledge_agent = CorporateKnowledgeAgent()
    
    # Initialize agents
    await task_agent.initialize()
    await knowledge_agent.initialize()
    
    # Create a task request
    task_message = AgentMessage(
        sender="user",
        recipient="task_agent",
        content={
            'description': 'Research AI applications in healthcare',
            'priority': 'high'
        },
        timestamp=0.0,
        message_type="task_request"
    )
    
    # Process the task
    response = await task_agent.process_message(task_message)
    print(f"Task Agent Response: {response.content}")
    
    # Simulate knowledge agent response
    knowledge_response = AgentMessage(
        sender="corporate_knowledge_agent",
        recipient="task_agent",
        content={
            'task_id': response.content['task_id'],
            'results': {
                'documents': [
                    {'title': 'AI in Healthcare', 'content': 'AI is transforming healthcare...'},
                    {'title': 'Machine Learning in Medicine', 'content': 'ML applications in medicine...'}
                ]
            }
        },
        timestamp=0.0,
        message_type="knowledge_response"
    )
    
    # Process knowledge response
    final_response = await task_agent.process_message(knowledge_response)
    print(f"Final Response: {final_response.content}")
    
    # Print knowledge graph contents
    print("\nKnowledge Graph Contents:")
    for s, p, o in task_agent.knowledge_graph.graph:
        print(f"{s} {p} {o}")

if __name__ == "__main__":
    asyncio.run(run_demo()) 