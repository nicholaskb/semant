"""Utility functions for working with GraphDB."""

from typing import List, Dict, Any, Optional
from SPARQLWrapper import SPARQLWrapper, JSON, POST, DIGEST
from config.graphdb_config import (
    SPARQL_ENDPOINT,
    GRAPHDB_USERNAME,
    GRAPHDB_PASSWORD,
    NAMESPACES,
    GRAPHDB_HOST,
    GRAPHDB_PORT,
    GRAPHDB_REPOSITORY
)

class GraphDBUtils:
    """Utility class for GraphDB operations."""
    
    def __init__(self):
        self.query_endpoint = SPARQL_ENDPOINT
        self.update_endpoint = f"http://{GRAPHDB_HOST}:{GRAPHDB_PORT}/repositories/{GRAPHDB_REPOSITORY}/statements"
        self.username = GRAPHDB_USERNAME
        self.password = GRAPHDB_PASSWORD
        self.namespaces = NAMESPACES
        self._init_wrappers()
    
    def _init_wrappers(self):
        from SPARQLWrapper import SPARQLWrapper, JSON, POST
        self.sparql_query = SPARQLWrapper(self.query_endpoint)
        self.sparql_query.setCredentials(self.username, self.password)
        self.sparql_query.setReturnFormat(JSON)
        self.sparql_update = SPARQLWrapper(self.update_endpoint)
        self.sparql_update.setCredentials(self.username, self.password)
        self.sparql_update.setReturnFormat(JSON)
        self.sparql_update.setMethod(POST)
    
    def query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SPARQL query and return results."""
        self.sparql_query.setQuery(query)
        try:
            results = self.sparql_query.query().convert()
            return results["results"]["bindings"]
        except Exception as e:
            print(f"Error executing query: {e}")
            return []
    
    def update(self, update_query: str) -> bool:
        """Execute a SPARQL update query."""
        self.sparql_update.setQuery(update_query)
        try:
            self.sparql_update.query()
            return True
        except Exception as e:
            print(f"Error executing update: {e}")
            return False
    
    def add_triple(self, subject: str, predicate: str, object_: str) -> bool:
        """Add a single triple to the graph."""
        update_query = f"""
        INSERT DATA {{
            {subject} {predicate} {object_} .
        }}
        """
        return self.update(update_query)
    
    def add_triples(self, triples: List[Dict[str, str]]) -> bool:
        """Add multiple triples to the graph."""
        triples_str = " .\n".join([
            f"{t['subject']} {t['predicate']} {t['object']}"
            for t in triples
        ])
        update_query = f"""
        INSERT DATA {{
            {triples_str} .
        }}
        """
        print(f"Debug - Update query:\n{update_query}")
        return self.update(update_query)
    
    def delete_triple(self, subject: str, predicate: str, object_: str) -> bool:
        """Delete a single triple from the graph."""
        update_query = f"""
        DELETE DATA {{
            {subject} {predicate} {object_} .
        }}
        """
        return self.update(update_query)
    
    def clear_graph(self) -> bool:
        """Clear all triples from the graph."""
        update_query = """
        DELETE {
            ?s ?p ?o
        }
        WHERE {
            ?s ?p ?o
        }
        """
        return self.update(update_query)
    
    def get_namespace_prefixes(self) -> str:
        """Get SPARQL prefix declarations for all namespaces."""
        return "\n".join([
            f"PREFIX {prefix}: <{uri}>"
            for prefix, uri in self.namespaces.items()
        ]) 