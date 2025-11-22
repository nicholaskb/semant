from typing import Any, Dict, List, Optional
from agents.core.base_agent import BaseAgent, AgentMessage
from loguru import logger
import asyncio
import uuid
from datetime import datetime
from agents.core.message_types import AgentMessage

class CorporateKnowledgeAgent(BaseAgent):
    """Agent responsible for managing corporate knowledge and documents."""
    
    def __init__(self, agent_id: str = "corporate_knowledge_agent"):
        super().__init__(agent_id, "corporate_knowledge")
        self.document_store = {}
        self.embedding_model = None
        self.logger = logger.bind(agent_id=agent_id)
        
    async def initialize(self) -> None:
        """Initialize the agent with required resources."""
        try:
            # Call parent initialize first
            await super().initialize()
            
            # Initialize embedding model
            # self.embedding_model = await self._load_embedding_model()
            
            # Initialize document store
            self.document_store = {}
            
            # Register with knowledge graph if available
            if self.knowledge_graph:
                await self._register_agent()
            
            self.logger.info("Corporate Knowledge Agent initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing agent: {str(e)}")
            raise
            
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Process incoming messages and return appropriate responses."""
        try:
            if message.message_type == "document_ingest":
                return await self._handle_document_ingest(message)
            elif message.message_type == "knowledge_query":
                return await self._handle_knowledge_query(message)
            elif message.message_type == "document_update":
                return await self._handle_document_update(message)
            else:
                return await self._handle_unknown_message(message)
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            raise
            
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with new corporate knowledge."""
        try:
            # Add document metadata
            await self.knowledge_graph.update_graph({
                f"doc:{update_data['doc_id']}": {
                    "rdf:type": "Document",
                    "title": update_data['title'],
                    "content": update_data['content'],
                    "timestamp": update_data['timestamp'],
                    "source": update_data['source']
                }
            })
            
            # Add relationships
            if 'relationships' in update_data:
                for rel in update_data['relationships']:
                    await self.knowledge_graph.add_triple(
                        f"doc:{update_data['doc_id']}",
                        rel['predicate'],
                        rel['object']
                    )
                    
            self.logger.info(f"Updated knowledge graph with document {update_data['doc_id']}")
        except Exception as e:
            self.logger.error(f"Error updating knowledge graph: {str(e)}")
            raise
            
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for corporate knowledge."""
        try:
            if query['type'] == 'document_search':
                return await self._search_documents(query['criteria'])
            elif query['type'] == 'relationship_query':
                return await self._query_relationships(query['criteria'])
            else:
                raise ValueError(f"Unknown query type: {query['type']}")
        except Exception as e:
            self.logger.error(f"Error querying knowledge graph: {str(e)}")
            raise
            
    async def _handle_document_ingest(self, message: AgentMessage) -> AgentMessage:
        """Handle document ingestion requests."""
        try:
            doc_data = message.content
            doc_id = await self._generate_doc_id()
            
            # Store document
            self.document_store[doc_id] = doc_data
            
            # Update knowledge graph
            await self.update_knowledge_graph({
                'doc_id': doc_id,
                'title': doc_data['title'],
                'content': doc_data['content'],
                'timestamp': doc_data['timestamp'],
                'source': doc_data['source'],
                'relationships': doc_data.get('relationships', [])
            })
            
            # Send SMS notification for important document ingestion
            try:
                doc_title = doc_data.get('title', 'Untitled Document')
                if len(doc_title) > 40:
                    doc_title = doc_title[:37] + "..."
                sms_msg = f"Document ingested: {doc_title} | ID: {doc_id}"
                await self.send_sms_notification(sms_msg)
            except Exception as sms_err:
                self.logger.warning(f"SMS notification failed: {sms_err}")
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={'status': 'success', 'doc_id': doc_id},
                timestamp=message.timestamp,
                message_type='document_ingest_response'
            )
        except Exception as e:
            self.logger.error(f"Error handling document ingest: {str(e)}")
            raise
            
    async def _handle_knowledge_query(self, message: AgentMessage) -> AgentMessage:
        """Handle knowledge query requests."""
        try:
            query_result = await self.query_knowledge_graph(message.content)
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={'status': 'success', 'results': query_result},
                timestamp=message.timestamp,
                message_type='knowledge_query_response'
            )
        except Exception as e:
            self.logger.error(f"Error handling knowledge query: {str(e)}")
            raise
            
    async def _handle_document_update(self, message: AgentMessage) -> AgentMessage:
        """Handle document update requests."""
        try:
            update_data = message.content
            doc_id = update_data['doc_id']
            
            if doc_id not in self.document_store:
                raise ValueError(f"Document {doc_id} not found")
                
            # Update document store
            self.document_store[doc_id].update(update_data['changes'])
            
            # Update knowledge graph
            await self.update_knowledge_graph({
                'doc_id': doc_id,
                **update_data['changes']
            })
            
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={'status': 'success', 'doc_id': doc_id},
                timestamp=message.timestamp,
                message_type='document_update_response'
            )
        except Exception as e:
            self.logger.error(f"Error handling document update: {str(e)}")
            raise
            
    async def _handle_unknown_message(self, message: AgentMessage) -> AgentMessage:
        """Handle unknown message types."""
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=message.sender_id,
            content={'status': 'error', 'message': 'Unknown message type'},
            timestamp=message.timestamp,
            message_type='error_response'
        )
        
    async def _generate_doc_id(self) -> str:
        """Generate a unique document ID."""
        return f"doc_{len(self.document_store) + 1}"
        
    async def _register_agent(self) -> None:
        """Register the agent with the knowledge graph."""
        await self.knowledge_graph.add_triple(
            f"agent:{self.agent_id}",
            "rdf:type",
            "CorporateKnowledgeAgent"
        )
        
    async def _search_documents(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for documents based on criteria.
        
        Args:
            criteria: Search criteria dictionary containing:
                - title: Optional title substring to match
                - content: Optional content substring to match
                - source: Optional source filter
                - doc_ids: Optional list of specific document IDs
                
        Returns:
            Dictionary containing:
                - documents: List of matching documents with metadata
                - count: Number of matching documents
                
        Raises:
            ValueError: If criteria is empty or invalid
        """
        if not criteria:
            raise ValueError("Search criteria cannot be empty")
            
        matching_docs = []
        
        # Search by specific document IDs if provided
        if 'doc_ids' in criteria:
            for doc_id in criteria['doc_ids']:
                if doc_id in self.document_store:
                    matching_docs.append({
                        'doc_id': doc_id,
                        **self.document_store[doc_id]
                    })
            return {'documents': matching_docs, 'count': len(matching_docs)}
        
        # Search through all documents
        for doc_id, doc_data in self.document_store.items():
            matches = True
            
            # Title filter
            if 'title' in criteria:
                title_match = criteria['title'].lower() in doc_data.get('title', '').lower()
                matches = matches and title_match
            
            # Content filter
            if 'content' in criteria:
                content_match = criteria['content'].lower() in doc_data.get('content', '').lower()
                matches = matches and content_match
            
            # Source filter
            if 'source' in criteria:
                source_match = criteria['source'] == doc_data.get('source')
                matches = matches and source_match
            
            if matches:
                matching_docs.append({
                    'doc_id': doc_id,
                    **doc_data
                })
        
        self.logger.info(f"Document search found {len(matching_docs)} matching documents")
        return {'documents': matching_docs, 'count': len(matching_docs)}
        
    async def _query_relationships(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query document relationships from the knowledge graph.
        
        Args:
            criteria: Query criteria dictionary containing:
                - doc_id: Document ID to query relationships for
                - relationship_type: Optional specific relationship predicate to filter
                - direction: 'outgoing' (default), 'incoming', or 'both'
                
        Returns:
            Dictionary containing:
                - relationships: List of relationship triples
                - count: Number of relationships found
                
        Raises:
            ValueError: If required criteria missing or knowledge graph unavailable
        """
        if not criteria:
            raise ValueError("Query criteria cannot be empty")
            
        if 'doc_id' not in criteria:
            raise ValueError("doc_id is required in criteria")
            
        if not self.knowledge_graph:
            self.logger.warning("Knowledge graph not available for relationship query")
            return {'relationships': [], 'count': 0}
        
        doc_id = criteria['doc_id']
        relationship_type = criteria.get('relationship_type')
        direction = criteria.get('direction', 'outgoing')
        
        relationships = []
        
        try:
            # Query outgoing relationships (doc -> object)
            if direction in ('outgoing', 'both'):
                sparql_query = f"""
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                SELECT ?predicate ?object
                WHERE {{
                    <doc:{doc_id}> ?predicate ?object .
                    {f'FILTER (?predicate = <{relationship_type}>)' if relationship_type else ''}
                }}
                """
                
                results = await self.knowledge_graph.query_graph(sparql_query)
                for result in results:
                    relationships.append({
                        'subject': f'doc:{doc_id}',
                        'predicate': str(result.get('predicate', '')),
                        'object': str(result.get('object', '')),
                        'direction': 'outgoing'
                    })
            
            # Query incoming relationships (subject -> doc)
            if direction in ('incoming', 'both'):
                sparql_query = f"""
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                SELECT ?subject ?predicate
                WHERE {{
                    ?subject ?predicate <doc:{doc_id}> .
                    {f'FILTER (?predicate = <{relationship_type}>)' if relationship_type else ''}
                }}
                """
                
                results = await self.knowledge_graph.query_graph(sparql_query)
                for result in results:
                    relationships.append({
                        'subject': str(result.get('subject', '')),
                        'predicate': str(result.get('predicate', '')),
                        'object': f'doc:{doc_id}',
                        'direction': 'incoming'
                    })
            
            self.logger.info(f"Relationship query found {len(relationships)} relationships for doc:{doc_id}")
            return {'relationships': relationships, 'count': len(relationships)}
            
        except Exception as e:
            self.logger.error(f"Error querying relationships: {str(e)}")
            raise 