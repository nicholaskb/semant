from typing import Any, Dict, List, Optional
from rdflib import Graph
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
from loguru import logger
from SPARQLWrapper import SPARQLWrapper, JSON
import ssl
import asyncio
from .cache import AsyncLRUCache

class RemoteKnowledgeGraphManager:
    """
    Manages a remote knowledge graph via a SPARQL endpoint.
    """
    def __init__(self, query_endpoint: str, update_endpoint: Optional[str] = None, verify_ssl: bool = True):
        self.query_endpoint = query_endpoint
        self.update_endpoint = update_endpoint or query_endpoint
        self.logger = logger.bind(component="RemoteKnowledgeGraphManager")
        self.store = SPARQLUpdateStore()
        self._lock = asyncio.Lock()
        self.cache = AsyncLRUCache(maxsize=1000)
        self._is_initialized = False
        self.verify_ssl = verify_ssl
        
    async def initialize(self) -> None:
        """Initialize the remote graph connection."""
        if self._is_initialized:
            return
            
        async with self._lock:
            if not self._is_initialized:
                try:
                    # Initialize store and graph
                    self.store.open((self.query_endpoint, self.update_endpoint))
                    self.graph = Graph(store=self.store)
                    self._is_initialized = True
                    self.logger.info("Remote graph manager initialized")
                except Exception as e:
                    self.logger.error(f"Failed to initialize remote graph: {str(e)}")
                    raise

    async def query_graph(self, sparql_query: str) -> List[Dict[str, str]]:
        """Execute a SPARQL query on the remote knowledge graph using SPARQLWrapper."""
        if not self._is_initialized:
            await self.initialize()
            
        # Check cache first
        cache_key = f"query:{sparql_query}"
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
            
        try:
            sparql = SPARQLWrapper(self.query_endpoint)
            sparql.setQuery(sparql_query)
            sparql.setReturnFormat(JSON)
            sparql.setMethod('POST')
            sparql.addCustomHttpHeader('User-Agent', 'Mozilla/5.0 (compatible; dMasterBot/1.0)')
            
            # Configure SSL context based on settings
            if not self.verify_ssl:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                sparql._SPARQLWrapper__custom_context = ctx
                
            results = sparql.query().convert()
            bindings = results.get('results', {}).get('bindings', [])
            
            # Convert bindings to a list of dicts with string keys and values
            output = []
            for row in bindings:
                result = {}
                for key, value in row.items():
                    # Ensure key is string
                    str_key = str(key)
                    # Convert value to string, handling None and missing values
                    if value is None or 'value' not in value:
                        result[str_key] = ""
                    else:
                        result[str_key] = str(value['value'])
                output.append(result)
                
            # Cache the results
            await self.cache.set(cache_key, output)
            return output
            
        except Exception as e:
            self.logger.error(f"Error executing SPARQL query: {str(e)}")
            raise

    async def update_graph(self, update_query: str) -> None:
        """Execute a SPARQL UPDATE query on the remote knowledge graph."""
        if not self._is_initialized:
            await self.initialize()
            
        try:
            async with self._lock:
                self.graph.update(update_query)
                # Clear cache after update
                await self.cache.clear()
        except Exception as e:
            self.logger.error(f"Error executing SPARQL update: {str(e)}")
            raise

    async def import_graph(self, data: str, format: str = 'turtle') -> None:
        """Import data into the remote knowledge graph (via SPARQL UPDATE)."""
        if not self._is_initialized:
            await self.initialize()
            
        try:
            # Parse the data into a temporary graph, then upload triples
            temp_graph = Graph()
            temp_graph.parse(data=data, format=format)
            
            async with self._lock:
                for s, p, o in temp_graph:
                    insert_query = f"""
                    INSERT DATA {{ <{s}> <{p}> {o.n3()} }}
                    """
                    await self.update_graph(insert_query)
                    
                # Clear cache after import
                await self.cache.clear()
        except Exception as e:
            self.logger.error(f"Error importing graph: {str(e)}")
            raise
            
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            await self.cache.clear()
            self.store.close()
            self._is_initialized = False
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            raise 