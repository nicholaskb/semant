#!/usr/bin/env python3
"""
Connect to local GraphDB and upload hot dog mission data
GraphDB is running on port 7200 (default)
"""
import requests
import rdflib
from rdflib import Graph, Namespace
import json

# GraphDB connection settings
GRAPHDB_URL = "http://localhost:7200"
REPOSITORY = "semant"  # Change this to your repository name

def check_graphdb_connection():
    """Check if GraphDB is accessible"""
    try:
        response = requests.get(f"{GRAPHDB_URL}/rest/repositories")
        if response.status_code == 200:
            repos = response.json()
            print(f"✅ Connected to GraphDB at {GRAPHDB_URL}")
            print(f"📚 Available repositories: {[r['id'] for r in repos]}")
            return True
        else:
            print(f"❌ GraphDB returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Could not connect to GraphDB: {e}")
        return False

def create_repository(repo_name="kg-hotdog"):
    """Create a new repository if it doesn't exist"""
    config = {
        "id": repo_name,
        "title": "Hot Dog Mission KG",
        "type": "free",
        "params": {
            "ruleset": "rdfsplus-optimized"
        }
    }
    
    try:
        # Check if repo exists
        response = requests.get(f"{GRAPHDB_URL}/rest/repositories/{repo_name}")
        if response.status_code == 200:
            print(f"📦 Repository '{repo_name}' already exists")
            return True
        
        # Create new repository
        response = requests.post(
            f"{GRAPHDB_URL}/rest/repositories",
            json=config,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code in [200, 201]:
            print(f"✅ Created repository: {repo_name}")
            return True
        else:
            print(f"❌ Failed to create repository: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error managing repository: {e}")
        return False

def upload_to_graphdb(repo_name="kg-hotdog"):
    """Upload the hot dog KG data to GraphDB"""
    
    # Load the local RDF file
    g = Graph()
    try:
        g.parse("knowledge_graph_persistent.n3", format="n3")
        print(f"📊 Loaded {len(g)} triples from local KG")
    except Exception as e:
        print(f"❌ Could not load local KG file: {e}")
        return False
    
    # Filter for hot dog related triples
    hot_dog_graph = Graph()
    hot_dog_count = 0
    
    for s, p, o in g:
        s_str = str(s).lower()
        o_str = str(o).lower()
        if 'hot-dog' in s_str or 'hot dog' in s_str or 'hot-dog' in o_str or 'hot dog' in o_str:
            hot_dog_graph.add((s, p, o))
            hot_dog_count += 1
    
    print(f"🌭 Found {hot_dog_count} hot dog related triples")
    
    # Serialize to Turtle format
    turtle_data = hot_dog_graph.serialize(format='turtle')
    
    # Upload to GraphDB
    sparql_endpoint = f"{GRAPHDB_URL}/repositories/{repo_name}/statements"
    
    try:
        response = requests.post(
            sparql_endpoint,
            data=turtle_data,
            headers={"Content-Type": "text/turtle"}
        )
        
        if response.status_code in [200, 201, 204]:
            print(f"✅ Successfully uploaded {hot_dog_count} triples to GraphDB!")
            return True
        else:
            print(f"❌ Upload failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error uploading to GraphDB: {e}")
        return False

def query_graphdb(repo_name="kg-hotdog"):
    """Query GraphDB to verify the data"""
    
    sparql_query = """
    PREFIX ex: <http://example.org/>
    
    SELECT ?s ?p ?o WHERE {
        ?s ?p ?o .
        FILTER(CONTAINS(LCASE(STR(?s)), "hot-dog") || 
               CONTAINS(LCASE(STR(?o)), "hot-dog"))
    }
    LIMIT 10
    """
    
    endpoint = f"{GRAPHDB_URL}/repositories/{repo_name}"
    
    try:
        response = requests.post(
            endpoint,
            data={"query": sparql_query},
            headers={"Accept": "application/sparql-results+json"}
        )
        
        if response.status_code == 200:
            results = response.json()
            bindings = results.get('results', {}).get('bindings', [])
            print(f"\n🔍 Sample query results ({len(bindings)} triples):")
            for b in bindings[:5]:
                s = b['s']['value'].split('/')[-1] if '/' in b['s']['value'] else b['s']['value']
                p = b['p']['value'].split('#')[-1] if '#' in b['p']['value'] else b['p']['value'].split('/')[-1]
                o = b['o']['value'][:50] if len(b['o']['value']) > 50 else b['o']['value']
                print(f"  • {s} -- {p} --> {o}")
            return True
        else:
            print(f"❌ Query failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error querying GraphDB: {e}")
        return False

def main():
    print("🔗 CONNECTING TO LOCAL GRAPHDB")
    print("=" * 60)
    
    # Check connection
    if not check_graphdb_connection():
        print("\n💡 Make sure GraphDB is running on http://localhost:7200")
        print("   You can download it from: https://graphdb.ontotext.com/")
        return
    
    # Create or use repository
    repo = input("\nEnter repository name (or press Enter for 'kg-hotdog'): ").strip()
    if not repo:
        repo = "kg-hotdog"
    
    if create_repository(repo):
        print(f"\n📤 Uploading hot dog mission data to repository '{repo}'...")
        if upload_to_graphdb(repo):
            print("\n✨ Success! Data is now in GraphDB")
            print(f"\n🌐 View in GraphDB Workbench:")
            print(f"   http://localhost:7200/repository/{repo}/query")
            
            # Run sample query
            query_graphdb(repo)
            
            print(f"\n📊 You can now:")
            print(f"   1. Open GraphDB Workbench at http://localhost:7200")
            print(f"   2. Select repository '{repo}'")
            print(f"   3. Use the Visual Graph to explore the hot dog mission")
            print(f"   4. Run SPARQL queries to analyze the data")

if __name__ == "__main__":
    main()
