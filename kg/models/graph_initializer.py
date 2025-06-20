from typing import Optional, Dict
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
from loguru import logger
from .graph_manager import KnowledgeGraphManager
import aiofiles
import asyncio
from .cache import AsyncLRUCache

class GraphInitializer:
    """Handles initialization of the knowledge graph with ontology and sample data."""
    
    def __init__(self, graph_manager: Optional[KnowledgeGraphManager] = None):
        self.graph_manager = graph_manager or KnowledgeGraphManager()
        self.logger = logger.bind(component="GraphInitializer")
        self._lock = asyncio.Lock()
        self.cache = AsyncLRUCache(maxsize=100)  # Cache for loaded ontologies
        self._is_initialized = False
        
    async def initialize(self) -> None:
        """Initialize the graph initializer."""
        if self._is_initialized:
            return
            
        async with self._lock:
            if not self._is_initialized:
                await self.cache.clear()
                self._is_initialized = True
                
    async def _read_file_async(self, file_path: Path) -> str:
        """Read file contents asynchronously."""
        async with aiofiles.open(file_path, mode='r') as f:
            return await f.read()
            
    async def load_ontology(self, ontology_path: str) -> None:
        """Load the core ontology into the graph."""
        if not self._is_initialized:
            await self.initialize()
            
        try:
            ontology_file = Path(ontology_path)
            if not ontology_file.exists():
                raise FileNotFoundError(f"Ontology file not found: {ontology_path}")
                
            # Check cache first
            cache_key = f"ontology:{ontology_path}"
            cached_data = await self.cache.get(cache_key)
            if cached_data is not None:
                self.logger.info(f"Loading ontology from cache: {ontology_path}")
                await self.graph_manager.import_graph(cached_data, format='turtle')
                return
                
            self.logger.info(f"Loading ontology from {ontology_path}")
            ontology_data = await self._read_file_async(ontology_file)
            await self.graph_manager.import_graph(ontology_data, format='turtle')
            
            # Cache the ontology data
            await self.cache.set(cache_key, ontology_data)
            self.logger.info("Ontology loaded successfully")
            
            # Load related ontologies if core ontology is loaded
            if "core.ttl" in ontology_path:
                related_ontologies = [
                    ("design_ontology.ttl", "kg/schemas/design_ontology.ttl"),
                    ("agentic_ontology.ttl", "kg/schemas/agentic_ontology.ttl")
                ]
                
                for name, path in related_ontologies:
                    ontology_path = Path(path)
                    if ontology_path.exists():
                        self.logger.info(f"Loading {name}")
                        data = await self._read_file_async(ontology_path)
                        await self.graph_manager.import_graph(data, format='turtle')
                        # Cache related ontology
                        await self.cache.set(f"ontology:{path}", data)
                        self.logger.info(f"{name} loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading ontology: {str(e)}")
            raise
            
    async def load_sample_data(self, data_path: str) -> None:
        """Load sample domain data into the graph."""
        if not self._is_initialized:
            await self.initialize()
            
        try:
            data_file = Path(data_path)
            if not data_file.exists():
                raise FileNotFoundError(f"Sample data file not found: {data_path}")
                
            self.logger.info(f"Loading sample data from {data_path}")
            data = await self._read_file_async(data_file)
            await self.graph_manager.import_graph(data, format='turtle')
            self.logger.info("Sample data loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading sample data: {str(e)}")
            raise
            
    async def initialize_graph(self, ontology_path: str, sample_data_path: Optional[str] = None) -> None:
        """Initialize the graph with ontology and optional sample data."""
        if not self._is_initialized:
            await self.initialize()
            
        try:
            # Load core ontology
            await self.load_ontology(ontology_path)
            
            # Load sample data if provided
            if sample_data_path:
                await self.load_sample_data(sample_data_path)
                
            # Validate the graph
            validation_results = await self.graph_manager.validate_graph()
            self.logger.info(f"Graph validation results: {validation_results}")
            
        except Exception as e:
            self.logger.error(f"Error initializing graph: {str(e)}")
            raise
            
    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            await self.cache.clear()
            self._is_initialized = False
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            raise 