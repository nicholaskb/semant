from typing import Any, Dict, List, Optional
from rdflib import Graph
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
from loguru import logger
from SPARQLWrapper import SPARQLWrapper, JSON
import ssl

class RemoteKnowledgeGraphManager:
    """
    Manages a remote knowledge graph via a SPARQL endpoint.
    """
    def __init__(self, query_endpoint: str, update_endpoint: Optional[str] = None):
        self.query_endpoint = query_endpoint
        self.update_endpoint = update_endpoint or query_endpoint
        self.logger = logger.bind(component="RemoteKnowledgeGraphManager")
        self.store = SPARQLUpdateStore()
        self.store.open((self.query_endpoint, self.update_endpoint))
        self.graph = Graph(store=self.store)

    async def query_graph(self, sparql_query: str) -> List[Dict[str, Any]]:
        """Execute a SPARQL query on the remote knowledge graph using SPARQLWrapper for better compatibility. SSL verification is disabled for testing purposes."""
        try:
            sparql = SPARQLWrapper(self.query_endpoint)
            sparql.setQuery(sparql_query)
            sparql.setReturnFormat(JSON)
            sparql.setMethod('POST')
            sparql.addCustomHttpHeader('User-Agent', 'Mozilla/5.0 (compatible; dMasterBot/1.0)')
            # Disable SSL verification for testing
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            sparql._SPARQLWrapper__custom_context = ctx
            results = sparql.query().convert()
            bindings = results.get('results', {}).get('bindings', [])
            # Convert bindings to a list of dicts with variable names as keys
            output = []
            for row in bindings:
                output.append({k: v['value'] for k, v in row.items()})
            return output
        except Exception as e:
            self.logger.error(f"Error executing SPARQL query: {str(e)}")
            raise

    async def update_graph(self, update_query: str) -> None:
        """Execute a SPARQL UPDATE query on the remote knowledge graph."""
        try:
            self.graph.update(update_query)
        except Exception as e:
            self.logger.error(f"Error executing SPARQL update: {str(e)}")
            raise

    async def import_graph(self, data: str, format: str = 'turtle') -> None:
        """Import data into the remote knowledge graph (via SPARQL UPDATE)."""
        try:
            # Parse the data into a temporary graph, then upload triples
            temp_graph = Graph()
            temp_graph.parse(data=data, format=format)
            for s, p, o in temp_graph:
                insert_query = f"""
                INSERT DATA {{ <{s}> <{p}> {o.n3()} }}
                """
                await self.update_graph(insert_query)
        except Exception as e:
            self.logger.error(f"Error importing graph: {str(e)}")
            raise 