from typing import Any, Dict, List, Optional, Union, TypeVar, cast
from rdflib import Graph, Namespace, URIRef, Literal, Variable
from rdflib.namespace import RDF, RDFS, XSD, OWL
from loguru import logger
import json
import asyncio
from datetime import datetime
import time
from .cache import AsyncLRUCache
from .indexing import TripleIndex

T = TypeVar('T')

class TimestampTracker:
    """Tracks timestamps for entity updates."""
    
    def __init__(self):
        self.timestamps: Dict[str, List[str]] = {}
        
    def add_timestamp(self, entity: str) -> None:
        """Add a timestamp for an entity update."""
        if entity not in self.timestamps:
            self.timestamps[entity] = []
        self.timestamps[entity].append(datetime.utcnow().isoformat())
        
    def get_timestamps(self, entity: str) -> List[str]:
        """Get all timestamps for an entity."""
        return self.timestamps.get(entity, [])
        
    def clear(self) -> None:
        """Clear all timestamps."""
        self.timestamps.clear()

class GraphVersion:
    """Tracks versions of the knowledge graph."""
    
    def __init__(self):
        self.versions = []
        self.current_version = 0
        
    def add_version(self, graph_state: str) -> int:
        """Add a new version of the graph."""
        self.versions.append(graph_state)
        self.current_version = len(self.versions) - 1
        return self.current_version
        
    def get_version(self, version_id: int) -> Optional[str]:
        """Get a specific version of the graph."""
        if 0 <= version_id < len(self.versions):
            return self.versions[version_id]
        return None
        
    def get_current_version(self) -> int:
        """Get the current version ID."""
        return self.current_version
        
    def clear(self) -> None:
        """Clear all versions."""
        self.versions.clear()
        self.current_version = 0

class GraphSecurity:
    """Manages security settings for the knowledge graph."""
    
    def __init__(self):
        self.access_rules = {}
        self.audit_log = []
        
    def add_access_rule(self, subject: str, predicate: str, object: str, allowed_roles: List[str]) -> None:
        """Add an access control rule."""
        key = (subject, predicate, object)
        self.access_rules[key] = allowed_roles
        
    def check_access(self, subject: str, predicate: str, object: str, role: str) -> bool:
        """Check if a role has access to a triple."""
        key = (subject, predicate, object)
        if key in self.access_rules:
            return role in self.access_rules[key]
        return True  # Default to allow if no rule exists
        
    def log_access(self, operation: str, subject: str, predicate: str, object: str, role: str, success: bool) -> None:
        """Log an access attempt."""
        self.audit_log.append({
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            'subject': subject,
            'predicate': predicate,
            'object': object,
            'role': role,
            'success': success
        })
        
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get the audit log."""
        return self.audit_log
        
    def clear(self) -> None:
        """Clear security settings and audit log."""
        self.access_rules.clear()
        self.audit_log.clear()

class KnowledgeGraphManager:
    """Enhanced knowledge graph manager with caching and indexing."""
    
    def __init__(self):
        self.graph = Graph()
        self.namespaces = {}
        self.initialize_namespaces()
        self.logger = logger.bind(component="KnowledgeGraphManager")
        self.cache = AsyncLRUCache(maxsize=1000)
        self.index = TripleIndex()
        self.timestamp_tracker = TimestampTracker()
        self.version_tracker = GraphVersion()
        self.security = GraphSecurity()
        self.lock = asyncio.Lock()
        self.metrics = {
            'query_count': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'key_conversion_time': 0.0,
            'total_query_time': 0.0,
            'validation_errors': 0,
            'security_violations': 0,
            'version_count': 0
        }
        self.validation_rules = []
        
    def initialize_namespaces(self) -> None:
        """Initialize standard and custom namespaces."""
        # Standard namespaces
        self.namespaces.update({
            'rdf': RDF,
            'rdfs': RDFS,
            'xsd': XSD,
            'owl': OWL
        })
        
        # Custom namespaces
        self.namespaces.update({
            'agent': Namespace('http://example.org/agent/'),
            'event': Namespace('http://example.org/event/'),
            'domain': Namespace('http://example.org/domain/'),
            'system': Namespace('http://example.org/system/'),
            'core': Namespace('http://example.org/core#'),
            '': Namespace('http://example.org/core#')  # Default namespace
        })
        
        # Bind namespaces to graph
        for prefix, namespace in self.namespaces.items():
            self.graph.bind(prefix, namespace)
            
        # Ensure default namespace is bound for SPARQL queries
        self.graph.bind('', self.namespaces[''])
            
    def add_validation_rule(self, rule: Dict[str, Any]) -> None:
        """Add a validation rule for the graph."""
        self.validation_rules.append(rule)
        
    async def add_triple(self, subject: str, predicate: str, object: Any, role: str = 'admin') -> None:
        """Add a triple to the graph with security checks."""
        async with self.lock:
            # Check security
            if not self.security.check_access(subject, predicate, str(object), role):
                self.metrics['security_violations'] += 1
                self.security.log_access('add', subject, predicate, str(object), role, False)
                raise PermissionError(f"Role {role} not authorized to add triple")
                
            # Add triple
            subj_ref = URIRef(subject)
            pred_ref = URIRef(predicate)
            self.graph.remove((subj_ref, pred_ref, None))
            
            if isinstance(object, dict):
                obj_node = Literal(json.dumps(object))
            elif isinstance(object, Literal):
                obj_node = object
            elif isinstance(object, str):
                if object.startswith('http://') or object.startswith('https://'):
                    obj_node = URIRef(object)
                else:
                    obj_node = Literal(object)
            else:
                obj_node = Literal(str(object))
                
            self.graph.add((subj_ref, pred_ref, obj_node))
            self.index.index_triple(subject, predicate, str(object))
            self.timestamp_tracker.add_timestamp(subject)
            
            # Create new version
            version_id = self.version_tracker.add_version(await self.export_graph())
            self.metrics['version_count'] = version_id + 1
            
            # Log access
            self.security.log_access('add', subject, predicate, str(object), role, True)
            
            # Invalidate cache selectively
            await self._invalidate_cache_selective(subject, predicate)
            
    async def _invalidate_cache_selective(self, subject: str, predicate: str) -> None:
        """Invalidate only cache entries affected by the update."""
        # Get all cached queries
        cached_queries = await self.cache.keys()
        
        # Check each query to see if it's affected
        for query in cached_queries:
            if subject in query or predicate in query:
                await self.cache.delete(query)
                
    async def rollback(self, version_id: int) -> None:
        """Rollback to a specific version of the graph."""
        async with self.lock:
            version_data = self.version_tracker.get_version(version_id)
            if version_data:
                self.graph = Graph()
                await self.import_graph(version_data)
                self.version_tracker.current_version = version_id
                await self.cache.clear()
            else:
                raise ValueError(f"Version {version_id} not found")
                
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the graph and its components."""
        return {
            'triple_count': len(self.graph),
            'cache_stats': self.cache.get_stats(),
            'index_stats': self.index.get_stats(),
            'timestamp_count': sum(len(timestamps) for timestamps in self.timestamp_tracker.timestamps.values()),
            'version_count': self.version_tracker.current_version + 1,
            'security_stats': {
                'access_rules': len(self.security.access_rules),
                'audit_log_entries': len(self.security.audit_log),
                'security_violations': self.metrics['security_violations']
            },
            'metrics': self.metrics
        }
        
    async def query_graph(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SPARQL query with caching and performance tracking."""
        start_time = time.time()
        self.metrics['query_count'] += 1
        
        try:
            # Check cache first
            cached_result = await self.cache.get(query)
            if cached_result is not None:
                self.metrics['cache_hits'] += 1
                return cached_result
            
            self.metrics['cache_misses'] += 1
            
            # Execute query
            results = []
            for row in self.graph.query(query):
                # Convert row to dict using row.labels for variable names
                result = {}
                for var in row.labels:
                    try:
                        value = row[var]
                        result[str(var)] = self._convert_value(value)
                    except Exception as e:
                        self.logger.warning(f"Error processing variable {var}: {str(e)}")
                        result[str(var)] = None
                results.append(result)
            
            # Cache result
            await self.cache.set(query, results)
            return results
        except Exception as e:
            self.logger.error(f"Error executing SPARQL query: {str(e)}")
            raise
        finally:
            self.metrics['total_query_time'] += time.time() - start_time
            
    async def _invalidate_cache(self, subject: str, predicate: str) -> None:
        """Invalidate all cache entries after an update for correctness."""
        await self.cache.clear()
        
    async def update_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with new information."""
        try:
            # Handle direct triple format
            if all(k in update_data for k in ['subject', 'predicate', 'object']):
                await self.add_triple(
                    update_data['subject'],
                    update_data['predicate'],
                    update_data['object']
                )
            # Handle nested format
            else:
                for subject, predicates in update_data.items():
                    if isinstance(predicates, dict):
                        for predicate, objects in predicates.items():
                            if isinstance(objects, list):
                                for obj in objects:
                                    await self.add_triple(subject, predicate, obj)
                            else:
                                await self.add_triple(subject, predicate, objects)
                    else:
                        # Handle case where predicates is a single value
                        await self.add_triple(subject, str(predicates), predicates)
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
            validation_results = {
                'triple_count': len(self.graph),
                'namespaces': list(self.graph.namespaces()),
                'subjects': len(set(self.graph.subjects())),
                'predicates': len(set(self.graph.predicates())),
                'objects': len(set(self.graph.objects())),
                'metrics': self.metrics,
                'validation_errors': [],
                'security_violations': []
            }
            
            # Apply validation rules
            for rule in self.validation_rules:
                try:
                    if not await self._apply_validation_rule(rule):
                        validation_results['validation_errors'].append(rule)
                        self.metrics['validation_errors'] += 1
                except Exception as e:
                    self.logger.error(f"Error applying validation rule: {str(e)}")
                    validation_results['validation_errors'].append({
                        'rule': rule,
                        'error': str(e)
                    })
                    
            return validation_results
        except Exception as e:
            self.logger.error(f"Error validating graph: {str(e)}")
            raise
            
    async def _apply_validation_rule(self, rule: Dict[str, Any]) -> bool:
        """Apply a validation rule to the graph."""
        if rule['type'] == 'sparql':
            results = await self.query_graph(rule['query'])
            return len(results) > 0
        elif rule['type'] == 'pattern':
            pattern = (URIRef(rule['subject']), URIRef(rule['predicate']), URIRef(rule['object']))
            return len(list(self.graph.triples(pattern))) > 0
        return True
        
    async def clear(self) -> None:
        """Clear the entire graph and all indices."""
        async with self.lock:
            self.graph = Graph()
            self.index.clear()
            self.timestamp_tracker.clear()
            await self.cache.clear()
            self.metrics = {
                'query_count': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'key_conversion_time': 0.0,
                'total_query_time': 0.0
            }
            
    def _convert_value(self, value: Any) -> Any:
        """Convert RDF value to appropriate Python type with timing."""
        start_time = time.time()
        try:
            if value is None:
                result = None
            elif isinstance(value, Literal):
                if value.datatype:
                    if value.datatype == XSD.string:
                        result = str(value)
                    elif value.datatype == XSD.integer:
                        result = int(value)
                    elif value.datatype == XSD.float:
                        result = float(value)
                    elif value.datatype == XSD.boolean:
                        result = bool(value)
                    else:
                        result = str(value)
                else:
                    result = str(value)
            elif isinstance(value, URIRef):
                result = str(value)
            else:
                result = str(value)
            return result
        finally:
            self.metrics['key_conversion_time'] += time.time() - start_time
            
    async def _invalidate_cache(self, subject: str, predicate: str) -> None:
        """Invalidate all cache entries after an update for correctness."""
        await self.cache.clear()
        
    async def update_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with new information."""
        try:
            # Handle direct triple format
            if all(k in update_data for k in ['subject', 'predicate', 'object']):
                await self.add_triple(
                    update_data['subject'],
                    update_data['predicate'],
                    update_data['object']
                )
            # Handle nested format
            else:
                for subject, predicates in update_data.items():
                    if isinstance(predicates, dict):
                        for predicate, objects in predicates.items():
                            if isinstance(objects, list):
                                for obj in objects:
                                    await self.add_triple(subject, predicate, obj)
                            else:
                                await self.add_triple(subject, predicate, objects)
                    else:
                        # Handle case where predicates is a single value
                        await self.add_triple(subject, str(predicates), predicates)
        except Exception as e:
            self.logger.error(f"Error updating graph: {str(e)}")
            raise 