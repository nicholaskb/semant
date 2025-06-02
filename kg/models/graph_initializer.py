from typing import Optional
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD
from loguru import logger
from .graph_manager import KnowledgeGraphManager

class GraphInitializer:
    """Handles initialization of the knowledge graph with ontology and sample data."""
    
    def __init__(self, graph_manager: Optional[KnowledgeGraphManager] = None):
        self.graph_manager = graph_manager or KnowledgeGraphManager()
        self.logger = logger.bind(component="GraphInitializer")
        
    async def load_ontology(self, ontology_path: str) -> None:
        """Load the core ontology into the graph."""
        try:
            ontology_file = Path(ontology_path)
            if not ontology_file.exists():
                raise FileNotFoundError(f"Ontology file not found: {ontology_path}")
                
            self.logger.info(f"Loading ontology from {ontology_path}")
            await self.graph_manager.import_graph(ontology_file.read_text(), format='turtle')
            self.logger.info("Ontology loaded successfully")
            
            # Load design ontology if core ontology is loaded
            if "core.ttl" in ontology_path:
                design_ontology_path = Path("kg/schemas/design_ontology.ttl")
                if design_ontology_path.exists():
                    self.logger.info("Loading design ontology")
                    await self.graph_manager.import_graph(design_ontology_path.read_text(), format='turtle')
                    self.logger.info("Design ontology loaded successfully")
                    
                # Load agentic ontology
                agentic_ontology_path = Path("kg/schemas/agentic_ontology.ttl")
                if agentic_ontology_path.exists():
                    self.logger.info("Loading agentic ontology")
                    await self.graph_manager.import_graph(agentic_ontology_path.read_text(), format='turtle')
                    self.logger.info("Agentic ontology loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading ontology: {str(e)}")
            raise
            
    async def load_sample_data(self, data_path: str) -> None:
        """Load sample domain data into the graph."""
        try:
            data_file = Path(data_path)
            if not data_file.exists():
                raise FileNotFoundError(f"Sample data file not found: {data_path}")
                
            self.logger.info(f"Loading sample data from {data_path}")
            await self.graph_manager.import_graph(data_file.read_text(), format='turtle')
            self.logger.info("Sample data loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading sample data: {str(e)}")
            raise
            
    async def initialize_graph(self, ontology_path: str, sample_data_path: Optional[str] = None) -> None:
        """Initialize the graph with ontology and optional sample data."""
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