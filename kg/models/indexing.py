from typing import Dict, Set, Tuple, Any
from rdflib import RDF

class TripleIndex:
    """Efficient indexing for triple patterns."""
    
    def __init__(self):
        # Index by predicate
        self.predicate_index: Dict[str, Set[Tuple[str, str]]] = {}
        # Index by type
        self.type_index: Dict[str, Set[str]] = {}
        # Index by relationship
        self.relationship_index: Dict[str, Dict[str, Set[str]]] = {}
        
    def index_triple(self, subject: str, predicate: str, object: str):
        """Index a triple using multiple indexing strategies."""
        # Index by predicate
        if predicate not in self.predicate_index:
            self.predicate_index[predicate] = set()
        self.predicate_index[predicate].add((subject, object))
        
        # Index by type
        if predicate == str(RDF.type):
            if object not in self.type_index:
                self.type_index[object] = set()
            self.type_index[object].add(subject)
            
        # Index by relationship
        if predicate not in self.relationship_index:
            self.relationship_index[predicate] = {}
        if object not in self.relationship_index[predicate]:
            self.relationship_index[predicate][object] = set()
        self.relationship_index[predicate][object].add(subject)
        
    def get_by_predicate(self, predicate: str) -> Set[Tuple[str, str]]:
        """Get all (subject, object) pairs for a predicate."""
        return self.predicate_index.get(predicate, set())
        
    def get_by_type(self, type_uri: str) -> Set[str]:
        """Get all subjects of a specific type."""
        return self.type_index.get(type_uri, set())
        
    def get_by_relationship(self, predicate: str, object: str) -> Set[str]:
        """Get all subjects related to an object through a predicate."""
        return self.relationship_index.get(predicate, {}).get(object, set())
        
    def clear(self):
        """Clear all indices."""
        self.predicate_index.clear()
        self.type_index.clear()
        self.relationship_index.clear()
        
    def get_stats(self) -> Dict[str, int]:
        """Get index statistics."""
        return {
            'predicate_count': len(self.predicate_index),
            'type_count': len(self.type_index),
            'relationship_count': len(self.relationship_index),
            'total_triples': sum(len(pairs) for pairs in self.predicate_index.values())
        } 