"""Script to create and configure the GraphDB repository."""

import requests
from config.graphdb_config import (
    GRAPHDB_HOST,
    GRAPHDB_PORT,
    GRAPHDB_USERNAME,
    GRAPHDB_PASSWORD,
    GRAPHDB_REPOSITORY
)

def create_repository():
    """Create a new repository in GraphDB."""
    # GraphDB REST API endpoint for repository management
    base_url = f"http://{GRAPHDB_HOST}:{GRAPHDB_PORT}"
    auth = (GRAPHDB_USERNAME, GRAPHDB_PASSWORD)
    
    # Repository configuration for GraphDB Free
    repo_config = {
        "id": GRAPHDB_REPOSITORY,
        "title": "Semant Knowledge Graph",
        "type": "free",
        "params": {
            "repositoryType": "file-repository",
            "ruleset": "rdfsplus-optimized",
            "storage-folder": "storage"
        }
    }
    
    # Create repository
    response = requests.post(
        f"{base_url}/rest/repositories",
        json=repo_config,
        auth=auth
    )
    
    if response.status_code == 201:
        print(f"Repository '{GRAPHDB_REPOSITORY}' created successfully!")
    else:
        print(f"Error creating repository: {response.text}")

if __name__ == "__main__":
    create_repository() 