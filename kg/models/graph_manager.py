from typing import Any, Dict, List, Optional
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
from loguru import logger
import json

class KnowledgeGraphManager:
    """Manages the central knowledge graph for the multi-agent system."""
    
    def __init__(self):
        self.graph = Graph()
        self.namespaces = {}
        self.initialize_namespaces()
        self.logger = logger.bind(component="KnowledgeGraphManager")
        
    def initialize_namespaces(self) -> None:
        """Initialize standard and custom namespaces."""
        # Standard namespaces
        self.namespaces.update({
            'rdf': RDF,
            'rdfs': RDFS,
            'xsd': XSD
        })
        
        # Custom namespaces
        self.namespaces.update({
            'agent': Namespace('http://example.org/agent/'),
            'event': Namespace('http://example.org/event/'),
            'domain': Namespace('http://example.org/domain/'),
            'system': Namespace('http://example.org/system/')
        })
        
        # Bind namespaces to graph
        for prefix, namespace in self.namespaces.items():
            self.graph.bind(prefix, namespace)
            
    async def add_triple(self, subject: str, predicate: str, 
                        object_value: Any, context: Optional[str] = None) -> None:
        """Add a triple to the knowledge graph."""
        try:
            s = URIRef(subject)
            p = URIRef(predicate)
            o = Literal(object_value) if isinstance(object_value, (str, int, float, bool)) else URIRef(object_value)
            
            self.graph.add((s, p, o))
            self.logger.debug(f"Added triple: {s} {p} {o}")
        except Exception as e:
            self.logger.error(f"Error adding triple: {str(e)}")
            raise
            
    async def query_graph(self, sparql_query: str) -> List[Dict[str, Any]]:
        """Execute a SPARQL query on the graph and return results as a list of dictionaries with string keys."""
        try:
            results = self.graph.query(sparql_query)
            # Convert each row to a dict with string keys
            return [
                {str(var): val for var, val in zip(results.vars, row)}
                for row in results
            ]
        except Exception as e:
            self.logger.error(f"Error executing SPARQL query: {e}")
            raise
            
    async def update_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with new information."""
        try:
            for subject, predicates in update_data.items():
                for predicate, objects in predicates.items():
                    if isinstance(objects, list):
                        for obj in objects:
                            await self.add_triple(subject, predicate, obj)
                    else:
                        await self.add_triple(subject, predicate, objects)
        except Exception as e:
            self.logger.error(f"Error updating graph: {str(e)}")
            raise
            
    async def export_graph(self, format: str = 'turtle') -> str:
        """Export the knowledge graph in the specified format."""
        try:
            return self.graph.serialize(format=format)
        except Exception as e:
            self.logger.error(f"Error exporting graph: {str(e)}")
            raise
            
    async def import_graph(self, data: str, format: str = 'turtle') -> None:
        """Import data into the knowledge graph."""
        try:
            self.graph.parse(data=data, format=format)
        except Exception as e:
            self.logger.error(f"Error importing graph: {str(e)}")
            raise
            
    async def validate_graph(self) -> Dict[str, Any]:
        """Validate the knowledge graph structure and content."""
        try:
            # Basic validation checks
            validation_results = {
                'triple_count': len(self.graph),
                'namespaces': list(self.graph.namespaces()),
                'subjects': len(set(self.graph.subjects())),
                'predicates': len(set(self.graph.predicates())),
                'objects': len(set(self.graph.objects()))
            }
            
            return validation_results
        except Exception as e:
            self.logger.error(f"Error validating graph: {str(e)}")
            raise 