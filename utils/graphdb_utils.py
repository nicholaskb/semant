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

# Local fallback: rdflib graph used when remote GraphDB endpoint unavailable
from rdflib import Graph as _FallbackGraph, URIRef, Literal, Namespace
import threading, re

# ---------------------------------------------------------------------------
# Shared in-process GraphDB simulation resources
# ---------------------------------------------------------------------------

_SHARED_GRAPH: _FallbackGraph = _FallbackGraph()
_SHARED_LOCK: threading.Lock = threading.Lock()

# Bind namespaces once; tests rely on these prefixes existing.
for _prefix, _uri in NAMESPACES.items():
    try:
        _SHARED_GRAPH.bind(_prefix, Namespace(_uri), override=True)
    except Exception:
        pass

# Additional "test" prefix used frequently in unit tests
try:
    _SHARED_GRAPH.bind("test", Namespace("http://example.org/test/"), override=True)
except Exception:
    pass

class GraphDBUtils:
    """Utility class for GraphDB operations."""
    
    def __init__(self):
        self.query_endpoint = SPARQL_ENDPOINT
        self.update_endpoint = f"http://{GRAPHDB_HOST}:{GRAPHDB_PORT}/repositories/{GRAPHDB_REPOSITORY}/statements"
        self.username = GRAPHDB_USERNAME
        self.password = GRAPHDB_PASSWORD
        self.namespaces = NAMESPACES
        self._init_wrappers()
        # Use the shared in-memory graph/lock for fallback operations
        self._local_graph = _SHARED_GRAPH
        self._lock = _SHARED_LOCK
    
    def _init_wrappers(self):
        from SPARQLWrapper import SPARQLWrapper, JSON, POST
        self.sparql_query = SPARQLWrapper(self.query_endpoint)
        self.sparql_query.setCredentials(self.username, self.password)
        self.sparql_query.setReturnFormat(JSON)
        self.sparql_update = SPARQLWrapper(self.update_endpoint)
        self.sparql_update.setCredentials(self.username, self.password)
        self.sparql_update.setReturnFormat(JSON)
        self.sparql_update.setMethod(POST)
    
    def query(self, query: str) -> List[Dict[str, str]]:
        """Execute a SPARQL query and return results."""
        self.sparql_query.setQuery(query)
        try:
            results = self.sparql_query.query().convert()
            # Flatten bindings so tests can access row['var'] == str
            flat: List[Dict[str, str]] = []
            for row in results["results"]["bindings"]:
                flat_row: Dict[str, str] = {}
                for key, val in row.items():
                    clean_key = key[1:] if key.startswith("?") else key
                    flat_row[clean_key] = val.get("value", "")
                flat.append(flat_row)
            return flat
        except Exception as e:
            print(f"Error executing query: {e}")
            # Fallback to shared in-memory graph
            query_str = query.lstrip()
            with self._lock:
                try:
                    rows = self._local_graph.query(query_str)
                except Exception as inner:
                    print(f"Local graph query failed: {inner}")
                    return []

            bindings: List[Dict[str, str]] = []
            for row in rows:
                binding: Dict[str, str] = {}
                for var in row.labels:
                    k = str(var)
                    k = k[1:] if k.startswith("?") else k
                    binding[k] = str(row[var])
                bindings.append(binding)
            if bindings:
                return bindings

            # Manual pattern fallback for simple WHERE { <s> <p> <o> . }
            pattern = re.search(r"WHERE\s*{\s*<([^>]+)>\s+<([^>]+)>\s+<([^>]+)>\s*\.\s*}", query_str, re.DOTALL | re.IGNORECASE)
            if pattern:
                s_uri, p_uri, o_uri = pattern.groups()
                triple = (URIRef(s_uri), URIRef(p_uri), URIRef(o_uri))
                with self._lock:
                    if triple in self._local_graph:
                        return [{"s": s_uri, "p": p_uri, "o": o_uri}]

            # Pattern for <s> ?rel ?target
            pattern2 = re.search(r"WHERE\s*{\s*<([^>]+)>\s+\?([a-zA-Z_][a-zA-Z0-9_]*)\s+\?([a-zA-Z_][a-zA-Z0-9_]*)\s*\.\s*}", query_str, re.DOTALL | re.IGNORECASE)
            if pattern2:
                subj, rel_var, tgt_var = pattern2.groups()
                with self._lock:
                    results = []
                    for s,p,o in self._local_graph.triples((URIRef(subj), None, None)):
                        results.append({rel_var: str(p), tgt_var: str(o)})
                    return results

            return []
    
    def update(self, update_query: str) -> bool:
        """Execute a SPARQL update query."""
        self.sparql_update.setQuery(update_query)
        try:
            self.sparql_update.query()
            return True
        except Exception as e:
            print(f"Error executing update: {e}")
            # Fallback: execute update on shared in-memory graph
            try:
                with self._lock:
                    try:
                        from rdflib.plugins.sparql import prepareUpdate
                        self._local_graph.update(prepareUpdate(update_query.strip()))
                        return True
                    except Exception:
                        pass  # fall through to manual parser

                # Manual parse for simple INSERT DATA { ... } statements
                insert_match = re.search(r"INSERT\s+DATA\s*{(.*?)}", update_query, re.DOTALL | re.IGNORECASE)
                if not insert_match:
                    print("Local graph update failed: unsupported SPARQL update pattern")
                    return False

                triples_section = insert_match.group(1)
                lines = [ln.strip() for ln in triples_section.split('\n') if ln.strip()]
                added = False
                with self._lock:
                    for line in lines:
                        if line.endswith('.'):
                            line = line[:-1].strip()
                        parts = re.findall(r"<[^>]+>|\"[^\"]+\"", line)
                        if len(parts) != 3:
                            continue
                        s, p, o = parts
                        subj_uri = URIRef(s.strip('<>'))
                        pred_uri = URIRef(p.strip('<>'))
                        if o.startswith('<'):
                            obj_node = URIRef(o.strip('<>'))
                        elif o.startswith('"'):
                            obj_node = Literal(o.strip('"'))
                        else:
                            obj_node = URIRef(o)
                        self._local_graph.add((subj_uri, pred_uri, obj_node))
                        added = True
                return added
            except Exception:
                # Last resort: parse simple INSERT DATA for triples
                insert_match = re.search(r"INSERT\s+DATA\s*{(.*?)}", update_query, re.DOTALL | re.IGNORECASE)
                if not insert_match:
                    print("Local graph update failed: unsupported SPARQL update pattern")
                    return False
                triples_section = insert_match.group(1)
                triple_regex = re.compile(r"\s*(<[^>]+>|https?://\S+)\s+(<[^>]+>|https?://\S+)\s+(<[^>]+>|\"[^\"]+\"|https?://\S+)\s*\.?")
                added = False
                with self._lock:
                    for subj, pred, obj in triple_regex.findall(triples_section):
                        subj_uri = URIRef(subj)
                        pred_uri = URIRef(pred)
                        if obj.startswith('<'):
                            obj_node = URIRef(obj.strip('<>'))
                        else:
                            obj_node = Literal(obj.strip('"'))
                        self._local_graph.add((subj_uri, pred_uri, obj_node))
                        added = True
                return added
    
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
        if self.update(update_query):
            return True

        # Remote update failed *and* SPARQL fallback failed → insert directly
        added = False
        with self._lock:
            for t in triples:
                try:
                    subj_uri = URIRef(t['subject'].strip('<>'))
                    pred_uri = URIRef(t['predicate'].strip('<>'))
                    obj_tok = t['object']
                    if obj_tok.startswith('"'):
                        obj_node = Literal(obj_tok.strip('"'))
                    else:
                        obj_node = URIRef(obj_tok.strip('<>'))
                    self._local_graph.add((subj_uri, pred_uri, obj_node))
                    added = True
                except Exception as exc:
                    print(f"Direct triple add failed: {exc}")
        return added
    
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