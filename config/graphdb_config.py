"""Configuration settings for GraphDB connection."""

# GraphDB connection settings
GRAPHDB_HOST = "localhost"
GRAPHDB_PORT = 7200
GRAPHDB_REPOSITORY = "knowledge-base"  # Updated repository name

# SPARQL endpoint URL
SPARQL_ENDPOINT = f"http://{GRAPHDB_HOST}:{GRAPHDB_PORT}/repositories/{GRAPHDB_REPOSITORY}"

# Default namespaces
NAMESPACES = {
    'dm': 'http://example.org/dMaster/',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'owl': 'http://www.w3.org/2002/07/owl#',
    'xsd': 'http://www.w3.org/2001/XMLSchema#',
    'skos': 'http://www.w3.org/2004/02/skos/core#',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dct': 'http://purl.org/dc/terms/'
}

# GraphDB credentials (if needed)
GRAPHDB_USERNAME = "admin"
GRAPHDB_PASSWORD = "root"  # Default password, should be changed in production 