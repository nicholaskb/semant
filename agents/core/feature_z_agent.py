from agents.core.base_agent import BaseAgent, AgentMessage
from typing import Dict, Any, List, Optional, Set
import uuid
from datetime import datetime
from loguru import logger

class FeatureZAgent(BaseAgent):
    """
    Agent that implements Feature Z functionality.
    
    This agent processes feature-specific data and can integrate with
    the knowledge graph when needed.
    
    Message content should include {'feature_data': ...}
    """
    
    def __init__(
        self,
        agent_id: str = "feature_z_agent",
        capabilities: Optional[Set[str]] = None,
        knowledge_graph: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Feature Z Agent.
        
        Args:
            agent_id: Unique identifier for this agent
            capabilities: Set of capabilities this agent provides
            knowledge_graph: Optional knowledge graph instance
            config: Optional configuration dictionary
        """
        # Define default capabilities
        default_capabilities = {"FEATURE_Z_PROCESSING", "DATA_VALIDATION"}
        if capabilities:
            capabilities = default_capabilities.union(capabilities)
        else:
            capabilities = default_capabilities

        # Convert string capabilities to proper Capability objects
        from agents.core.capability_types import Capability, CapabilityType
        capabilities_objects = set()
        for cap_str in capabilities:
            try:
                cap_type = CapabilityType(cap_str.lower())  # Convert to lowercase for enum matching
                capabilities_objects.add(Capability(type=cap_type, version="1.0"))
            except ValueError:
                logger.warning(f"Unknown capability type: {cap_str}, skipping")

        super().__init__(
            agent_id=agent_id,
            agent_type="feature_z",
            capabilities=capabilities_objects,
            knowledge_graph=knowledge_graph,
            config=config or {}
        )
        
        self.processed_count = 0
        self.error_count = 0

    async def initialize(self) -> None:
        """Initialize the agent and any required resources."""
        await super().initialize()
        caps = await self.get_capabilities()
        self.logger.info(f"Feature Z Agent '{self.agent_id}' initialized with capabilities: {caps}")

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """
        Process incoming messages for Feature Z functionality.
        
        Args:
            message: The incoming message to process
            
        Returns:
            Response message with processing results
        """
        # Extract feature data from message
        feature_data = message.content.get('feature_data')
        operation = message.content.get('operation', 'process')
        
        try:
            # Route to appropriate handler based on operation
            if operation == 'validate':
                result = await self._validate_feature_data(feature_data)
            elif operation == 'process':
                result = await self._process_feature_data(feature_data)
            elif operation == 'query':
                result = await self._query_feature_status()
            else:
                return self._create_error_response(
                    message,
                    f"Unknown operation: {operation}"
                )
            
            # Update metrics
            self.processed_count += 1
            
            # Log to knowledge graph if available
            if self.knowledge_graph:
                await self._log_to_knowledge_graph(operation, feature_data, result)
            
            # Create success response
            return AgentMessage(
                sender_id=self.agent_id,
                recipient_id=message.sender_id,
                content={
                    "status": "success",
                    "operation": operation,
                    "result": result,
                    "processed_count": self.processed_count
                },
                timestamp=datetime.now(),
                message_type="feature_z_response"
            )
            
        except ValueError as e:
            self.error_count += 1
            return self._create_error_response(message, f"Validation error: {e}")
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error processing feature data: {e}")
            return self._create_error_response(message, str(e))
    
    async def _validate_feature_data(self, feature_data: Any) -> Dict[str, Any]:
        """
        Validate feature data according to Feature Z requirements.
        
        Args:
            feature_data: Data to validate
            
        Returns:
            Validation results
            
        Raises:
            ValueError: If data is invalid
        """
        if not feature_data:
            raise ValueError("No feature data provided")
        
        # Perform validation checks
        validation_results = {
            "is_valid": True,
            "checks_performed": []
        }
        
        # Check data type
        if isinstance(feature_data, dict):
            validation_results["checks_performed"].append("type_check: dict")
        elif isinstance(feature_data, list):
            validation_results["checks_performed"].append("type_check: list")
        else:
            validation_results["checks_performed"].append(f"type_check: {type(feature_data).__name__}")
        
        # Check for required fields if dict
        if isinstance(feature_data, dict):
            required_fields = ['id', 'type', 'value']
            missing_fields = [f for f in required_fields if f not in feature_data]
            
            if missing_fields:
                validation_results["is_valid"] = False
                validation_results["missing_fields"] = missing_fields
            else:
                validation_results["checks_performed"].append("required_fields: present")
        
        self.logger.debug(f"Validation results: {validation_results}")
        return validation_results
    
    async def _process_feature_data(self, feature_data: Any) -> Dict[str, Any]:
        """
        Process feature data according to Feature Z logic.
        
        Args:
            feature_data: Data to process
            
        Returns:
            Processing results
        """
        # First validate the data
        validation = await self._validate_feature_data(feature_data)
        
        if not validation.get("is_valid", False):
            raise ValueError(f"Invalid feature data: {validation}")
        
        # Process the data
        self.logger.info(f"Processing feature data: {feature_data}")
        
        # Simulate processing logic
        result = {
            "processed": True,
            "timestamp": datetime.now().isoformat(),
            "data_type": type(feature_data).__name__
        }
        
        # Add specific processing based on data type
        if isinstance(feature_data, dict):
            result["item_count"] = len(feature_data)
            result["keys_processed"] = list(feature_data.keys())
        elif isinstance(feature_data, list):
            result["item_count"] = len(feature_data)
            result["items_processed"] = len(feature_data)
        else:
            result["value_processed"] = str(feature_data)[:100]  # First 100 chars
        
        return result
    
    async def _query_feature_status(self) -> Dict[str, Any]:
        """
        Query the current status of the Feature Z agent.
        
        Returns:
            Status information
        """
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "capabilities": [str(cap) for cap in await self.get_capabilities()],
            "uptime_seconds": (datetime.now() - self._initialized_at).total_seconds() if hasattr(self, '_initialized_at') else 0
        }
    
    async def _log_to_knowledge_graph(
        self,
        operation: str,
        feature_data: Any,
        result: Dict[str, Any]
    ) -> None:
        """
        Log operation to knowledge graph.
        
        Args:
            operation: The operation performed
            feature_data: The data that was processed
            result: The result of processing
        """
        if not self.knowledge_graph:
            return
        
        try:
            # Create unique operation ID
            operation_id = f"feature_z_op_{uuid.uuid4().hex[:8]}"
            operation_uri = f"http://example.org/operations/{operation_id}"
            
            # Add triples to knowledge graph
            await self.knowledge_graph.add_triple(
                operation_uri,
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                "http://example.org/FeatureZOperation"
            )
            
            await self.knowledge_graph.add_triple(
                operation_uri,
                "http://example.org/operationType",
                operation
            )
            
            await self.knowledge_graph.add_triple(
                operation_uri,
                "http://example.org/agentId",
                self.agent_id
            )
            
            await self.knowledge_graph.add_triple(
                operation_uri,
                "http://example.org/timestamp",
                datetime.now().isoformat()
            )
            
            await self.knowledge_graph.add_triple(
                operation_uri,
                "http://example.org/resultStatus",
                result.get("status", "unknown")
            )
            
            self.logger.debug(f"Logged operation {operation_id} to knowledge graph")
            
        except Exception as e:
            self.logger.warning(f"Failed to log to knowledge graph: {e}")
    
    def _create_error_response(
        self,
        original_message: AgentMessage,
        error: str
    ) -> AgentMessage:
        """
        Create a standardized error response.
        
        Args:
            original_message: The message that caused the error
            error: Error description
            
        Returns:
            Error response message
        """
        return AgentMessage(
            sender_id=self.agent_id,
            recipient_id=original_message.sender_id,
            content={
                "status": "error",
                "error": error,
                "original_request": original_message.content
            },
            timestamp=datetime.now(),
            message_type="feature_z_error"
        )
    
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query the knowledge graph for Feature Z related information.
        
        Args:
            query: Query parameters
            
        Returns:
            Query results
        """
        if not self.knowledge_graph:
            return {"error": "Knowledge graph not available"}
        
        try:
            # Extract query type
            query_type = query.get("type", "operations")
            
            if query_type == "operations":
                # Query for recent Feature Z operations
                sparql = """
                PREFIX ex: <http://example.org/>
                SELECT ?op ?type ?timestamp ?status
                WHERE {
                    ?op a ex:FeatureZOperation ;
                        ex:operationType ?type ;
                        ex:timestamp ?timestamp ;
                        ex:resultStatus ?status ;
                        ex:agentId "%s" .
                }
                ORDER BY DESC(?timestamp)
                LIMIT 10
                """ % self.agent_id
                
                results = await self.knowledge_graph.query_graph(sparql)
                return {"operations": results}
            
            elif query_type == "statistics":
                # Query for operation statistics
                sparql = """
                PREFIX ex: <http://example.org/>
                SELECT (COUNT(?op) as ?total) ?type
                WHERE {
                    ?op a ex:FeatureZOperation ;
                        ex:operationType ?type ;
                        ex:agentId "%s" .
                }
                GROUP BY ?type
                """ % self.agent_id
                
                results = await self.knowledge_graph.query_graph(sparql)
                return {"statistics": results}
            
            else:
                return {"error": f"Unknown query type: {query_type}"}
                
        except Exception as e:
            self.logger.error(f"Knowledge graph query failed: {e}")
            return {"error": str(e)}
    
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """
        Update the knowledge graph with Feature Z specific data.
        
        Args:
            update_data: Data to add to the knowledge graph
        """
        if not self.knowledge_graph:
            self.logger.debug("Knowledge graph not available for updates")
            return
        
        try:
            # Extract update type
            update_type = update_data.get("type", "general")
            
            # Create unique ID for this update
            update_id = f"feature_z_update_{uuid.uuid4().hex[:8]}"
            update_uri = f"http://example.org/updates/{update_id}"
            
            # Add base triples
            await self.knowledge_graph.add_triple(
                update_uri,
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
                "http://example.org/FeatureZUpdate"
            )
            
            await self.knowledge_graph.add_triple(
                update_uri,
                "http://example.org/updateType",
                update_type
            )
            
            await self.knowledge_graph.add_triple(
                update_uri,
                "http://example.org/agentId",
                self.agent_id
            )
            
            await self.knowledge_graph.add_triple(
                update_uri,
                "http://example.org/timestamp",
                datetime.now().isoformat()
            )
            
            # Add custom data fields
            for key, value in update_data.items():
                if key != "type" and value is not None:
                    await self.knowledge_graph.add_triple(
                        update_uri,
                        f"http://example.org/{key}",
                        str(value)
                    )
            
            self.logger.info(f"Knowledge graph updated with {update_type} data: {update_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to update knowledge graph: {e}")
            raise
    
    async def shutdown(self):
        """Clean shutdown of the agent."""
        self.logger.info(f"Shutting down Feature Z Agent '{self.agent_id}'")
        self.logger.info(f"Final stats - Processed: {self.processed_count}, Errors: {self.error_count}")
        await super().shutdown() 