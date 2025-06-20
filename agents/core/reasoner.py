from typing import List, Dict, Any, Optional
from rdflib import Graph, Namespace, RDF, RDFS, OWL
from SPARQLWrapper import SPARQLWrapper, JSON
from utils.graphdb_utils import GraphDBUtils
from config.graphdb_config import NAMESPACES
import logging
import rdflib
from rdflib.term import URIRef, Literal

logger = logging.getLogger(__name__)

class KnowledgeGraphReasoner:
    """A reasoner that can traverse the knowledge graph and perform research investigations."""
    
    def __init__(self, graph=None, sparql_endpoint=None):
        self.graph = graph
        self.graphdb = GraphDBUtils() if sparql_endpoint else None
        self.namespaces = {
            prefix: Namespace(uri) for prefix, uri in NAMESPACES.items()
        }
        # Bind namespaces to graph if using local mode
        if self.graph:
            for prefix, namespace in self.namespaces.items():
                self.graph.bind(prefix, namespace)
        
    def _get_prefixes(self) -> str:
        """Get SPARQL prefix declarations for all namespaces."""
        return "\n".join([
            f"PREFIX {prefix}: <{uri}>"
            for prefix, uri in NAMESPACES.items()
        ])
    
    async def investigate_research_topic(self, topic: str, depth: int = 2) -> Dict[str, Any]:
        """
        Investigate a research topic by traversing the knowledge graph.
        
        Args:
            topic: The research topic to investigate
            depth: How deep to traverse the graph (default: 2)
            
        Returns:
            Dict containing research findings and related information
        """
        findings = {
            'topic': topic,
            'related_concepts': [],
            'key_insights': [],
            'sources': [],
            'confidence': 0.0
        }
        topic_lc = topic.lower()
        
        # Find all diary entries related to the topic
        topic_entries = await self._find_topic_entries(topic_lc)
        findings['related_concepts'].extend(topic_entries)
        
        # Find related research papers
        papers = await self._find_related_papers(topic_lc)
        findings['sources'].extend(papers)
        
        # Find key insights from the research
        insights = await self._extract_key_insights(topic_lc)
        findings['key_insights'].extend(insights)
        
        # Calculate confidence based on evidence
        findings['confidence'] = await self._calculate_confidence(findings)
        
        return findings
    
    async def _find_topic_entries(self, topic_lc: str) -> List[Dict[str, Any]]:
        """Find all diary entries related to the topic."""
        prefixes = self._get_prefixes()
        query = f'''
            {prefixes}
            SELECT ?agent ?entry ?message ?timestamp
            WHERE {{
                ?agent dm:hasDiaryEntry ?entry .
                ?entry dm:message ?message ;
                       dm:timestamp ?timestamp .
                FILTER(CONTAINS(LCASE(STR(?message)), "{topic_lc}"))
            }}
        '''
        print(f"Debug - Topic entries query:\n{query}")
        results = []
        for row in self._query(query):
            results.append({
                'agent': str(row['agent']),
                'message': str(row['message']),
                'timestamp': str(row['timestamp'])
            })
        return results
    
    async def _find_related_papers(self, topic_lc: str) -> List[Dict[str, Any]]:
        """Find research papers related to the topic."""
        prefixes = self._get_prefixes()
        query = f'''
            {prefixes}
            SELECT ?paper ?topic ?insight
            WHERE {{
                ?paper dm:hasTopic ?topic ;
                       dm:hasInsight ?insight .
                FILTER(CONTAINS(LCASE(STR(?topic)), "{topic_lc}"))
            }}
        '''
        print(f"Debug - Related papers query:\n{query}")
        results = []
        for row in self._query(query):
            results.append({
                'paper': str(row['paper']),
                'topic': str(row['topic']),
                'insight': str(row['insight'])
            })
        return results
    
    async def _extract_key_insights(self, topic_lc: str) -> List[str]:
        """Extract key insights from research about the topic."""
        prefixes = self._get_prefixes()
        query = f'''
            {prefixes}
            SELECT DISTINCT ?insight
            WHERE {{
                {{
                    ?paper dm:hasTopic ?paper_topic ;
                          dm:hasInsight ?insight .
                    FILTER(CONTAINS(LCASE(STR(?paper_topic)), "{topic_lc}"))
                }} UNION {{
                    ?entry dm:message ?message ;
                          dm:hasInsight ?insight .
                    FILTER(CONTAINS(LCASE(STR(?message)), "{topic_lc}"))
                }}
            }}
        '''
        results = []
        for row in self._query(query):
            results.append(str(row['insight']))
        return results
    
    async def _calculate_confidence(self, findings: Dict[str, Any]) -> float:
        """Calculate confidence score based on evidence."""
        # Simple confidence calculation based on number of sources and insights
        num_sources = len(findings['sources'])
        num_insights = len(findings['key_insights'])
        num_entries = len(findings['related_concepts'])
        
        # Weight different factors
        source_weight = 0.4
        insight_weight = 0.4
        entry_weight = 0.2
        
        # Calculate weighted score
        confidence = (
            (num_sources * source_weight) +
            (num_insights * insight_weight) +
            (num_entries * entry_weight)
        ) / (source_weight + insight_weight + entry_weight)
        
        return min(confidence, 1.0)  # Cap at 1.0
    
    async def traverse_knowledge_graph(self, 
                                     start_node: str, 
                                     max_depth: int = 2,
                                     relationship_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Traverse the knowledge graph starting from a given node."""
        traversal = {
            'start_node': start_node,
            'depth': max_depth,
            'nodes': [],
            'relationships': [],
            'paths': []
        }
        
        # Build the SPARQL query based on parameters
        query_parts = []
        if relationship_types:
            rel_filter = " || ".join([f"?rel = {rel}" for rel in relationship_types])
            query_parts.append(f"FILTER({rel_filter})")
        
        prefixes = self._get_prefixes()
        # Remove angle brackets from start_node if they exist
        clean_node = start_node.strip('<>')
        query = f'''
            {prefixes}
            SELECT ?rel ?target
            WHERE {{
                <{clean_node}> ?rel ?target .
                {' '.join(query_parts)}
            }}
        '''
        print(f"Debug - Traversal query:\n{query}")
        
        # Execute query and build traversal results
        for row in self._query(query):
            # row['rel'] and row['target'] are always strings now
            traversal['relationships'].append(str(row['rel']))
            traversal['paths'].append({
                'from': start_node,
                'relationship': str(row['rel']),
                'to': str(row['target'])
            })
            
            # Add target to nodes if it's not already there
            if str(row['target']) not in traversal['nodes']:
                traversal['nodes'].append(str(row['target']))
        
        return traversal
    
    async def find_related_concepts(self, concept: str, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Find concepts related to the given concept based on similarity."""
        related = []
        # Example SPARQL query to find related concepts
        query = f"""
            {self._get_prefixes()}
            SELECT ?related ?score
            WHERE {{
                <{concept}> dm:similarTo ?related .
                ?related dm:similarityScore ?score .
            }}
        """
        for row in self._query(query):
            # Convert score to float if it's a string
            score = float(row['score']) if isinstance(row['score'], str) else row['score']
            if score >= similarity_threshold:
                related.append({
                    'concept': row['related'],
                    'similarity': score
                })
        return related
    
    def _query(self, sparql_query: str) -> List[Dict[str, str]]:
        """Execute a SPARQL query and return results."""
        if self.graphdb:
            return self.graphdb.query(sparql_query)
        else:
            # For rdflib, convert ResultRow to dict with string keys and values
            results = []
            qres = self.graph.query(sparql_query)
            for row in qres:
                # row.labels gives the variable names
                result = {}
                for var in row.labels:
                    # Convert variable name to string
                    key = str(var)
                    # Convert value to string, handling None and URIRef/Literal objects
                    value = row[var]
                    if value is None:
                        result[key] = ""
                    elif isinstance(value, (URIRef, Literal)):
                        result[key] = str(value)
                    else:
                        result[key] = str(value)
                results.append(result)
            return results 