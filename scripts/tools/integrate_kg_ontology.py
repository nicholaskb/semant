#!/usr/bin/env python3
"""
Integrate existing KG triples with proper ontology structure
Maps existing unstructured data to ontology classes and relationships
"""
import requests
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, OWL, XSD, BNode
from datetime import datetime
import re

# Namespaces
AG = Namespace("http://example.org/agentKG#")
EX = Namespace("http://example.org/")
MISSION = Namespace("http://example.org/mission/")
AGENT = Namespace("http://example.org/agent/")
TASK = Namespace("http://example.org/task/")
DECISION = Namespace("http://example.org/decision/")
IMAGE = Namespace("http://example.org/image/")
MJ = Namespace("http://example.org/midjourney#")
PROV = Namespace("http://www.w3.org/ns/prov#")
DCT = Namespace("http://purl.org/dc/terms/")

def load_and_analyze_existing():
    """Load existing KG and analyze its structure"""
    print("📊 ANALYZING EXISTING KNOWLEDGE GRAPH")
    print("=" * 60)
    
    # Load existing persistent KG
    g_existing = Graph()
    g_existing.parse("knowledge_graph_persistent.n3", format="n3")
    
    print(f"📁 Loaded {len(g_existing)} existing triples")
    
    # Analyze what we have
    stats = {
        'decisions': [],
        'agents': [],
        'tasks': [],
        'images': [],
        'other': []
    }
    
    for s, p, o in g_existing:
        s_str = str(s)
        
        if 'decision' in s_str.lower():
            stats['decisions'].append((s, p, o))
        elif 'agent' in s_str.lower() or 'commander' in s_str.lower():
            stats['agents'].append((s, p, o))
        elif 'task' in s_str.lower() or 'midjourney' in s_str.lower():
            stats['tasks'].append((s, p, o))
        elif 'image' in s_str.lower() or '.png' in str(o).lower() or '.jpg' in str(o).lower():
            stats['images'].append((s, p, o))
        else:
            stats['other'].append((s, p, o))
    
    print(f"\n📈 Current structure:")
    print(f"   • Decisions: {len(stats['decisions'])} triples")
    print(f"   • Agents: {len(stats['agents'])} triples")
    print(f"   • Tasks: {len(stats['tasks'])} triples")
    print(f"   • Images: {len(stats['images'])} triples")
    print(f"   • Other: {len(stats['other'])} triples")
    
    return g_existing, stats

def integrate_with_ontology(g_existing, stats):
    """Map existing triples to ontology structure"""
    print("\n🔄 INTEGRATING WITH ONTOLOGY")
    print("=" * 60)
    
    # Create new integrated graph
    g_integrated = Graph()
    
    # Bind namespaces
    g_integrated.bind("ag", AG)
    g_integrated.bind("ex", EX)
    g_integrated.bind("agent", AGENT)
    g_integrated.bind("task", TASK)
    g_integrated.bind("decision", DECISION)
    g_integrated.bind("mj", MJ)
    g_integrated.bind("prov", PROV)
    g_integrated.bind("dct", DCT)
    
    # First, add all original triples
    for s, p, o in g_existing:
        g_integrated.add((s, p, o))
    
    print(f"✅ Preserved {len(g_existing)} original triples")
    
    # ============================================================
    # MAP EXISTING ENTITIES TO ONTOLOGY CLASSES
    # ============================================================
    
    # 1. Find and type the commander agent
    commander_uri = None
    for s, p, o in stats['agents']:
        if 'commander' in str(s).lower():
            commander_uri = s
            g_integrated.add((s, RDF.type, AG.Agent))
            g_integrated.add((s, RDF.type, AG.AutonomousAgent))
            g_integrated.add((s, RDFS.label, Literal("Supreme Hot Dog Commander")))
            g_integrated.add((s, AG.hasRole, AG.Orchestrator))
            g_integrated.add((s, AG.hasCapability, AG.ImageGeneration))
            g_integrated.add((s, AG.hasCapability, AG.AutonomousDecisionMaking))
            print(f"   ✓ Typed agent: {str(s).split('/')[-1]}")
            break
    
    # 2. Map decisions to ontology
    decision_uris = []
    for s, p, o in stats['decisions']:
        if 'decision' in str(s).lower():
            if (s, RDF.type, AG.Decision) not in g_integrated:
                g_integrated.add((s, RDF.type, AG.Decision))
                g_integrated.add((s, RDF.type, PROV.Activity))
                decision_uris.append(s)
                
                # Link to commander if found
                if commander_uri:
                    g_integrated.add((s, PROV.wasAttributedTo, commander_uri))
                    g_integrated.add((s, AG.madeBy, commander_uri))
    
    print(f"   ✓ Typed {len(decision_uris)} decisions")
    
    # Chain decisions together based on timestamps
    decisions_with_time = []
    for dec_uri in decision_uris:
        # Find timestamp
        for s, p, o in g_integrated:
            if s == dec_uri and 'timestamp' in str(p).lower():
                decisions_with_time.append((dec_uri, str(o)))
                break
    
    # Sort by timestamp and create chain
    decisions_with_time.sort(key=lambda x: x[1])
    for i in range(len(decisions_with_time) - 1):
        current = decisions_with_time[i][0]
        next_dec = decisions_with_time[i + 1][0]
        g_integrated.add((next_dec, AG.follows, current))
        g_integrated.add((current, AG.precedes, next_dec))
    
    print(f"   ✓ Created decision chain with {len(decisions_with_time)} decisions")
    
    # 3. Map Midjourney tasks
    mj_tasks = []
    for s, p, o in g_integrated:
        if 'midjourney' in str(s).lower() and 'occurrence' in str(s).lower():
            g_integrated.add((s, RDF.type, AG.Task))
            g_integrated.add((s, RDF.type, MJ.ImageGenerationTask))
            mj_tasks.append(s)
            
            # Link to commander
            if commander_uri:
                g_integrated.add((s, AG.executedBy, commander_uri))
    
    print(f"   ✓ Typed {len(mj_tasks)} Midjourney tasks")
    
    # 4. Identify and type images/artifacts
    artifacts = []
    for s, p, o in g_integrated:
        if str(p).endswith('hasResult') or str(p).endswith('hasImage'):
            if str(o).startswith('http'):
                g_integrated.add((URIRef(o), RDF.type, AG.Artifact))
                g_integrated.add((URIRef(o), RDF.type, PROV.Entity))
                g_integrated.add((s, PROV.generated, URIRef(o)))
                artifacts.append(URIRef(o))
    
    print(f"   ✓ Typed {len(artifacts)} artifacts")
    
    # 5. Find and type the mission
    mission_uri = None
    for s, p, o in g_integrated:
        if 'hot-dog-flier' in str(s).lower() and 'e7dd2995' in str(s):
            mission_uri = s
            g_integrated.add((s, RDF.type, AG.Mission))
            g_integrated.add((s, RDF.type, AG.WorkflowExecution))
            g_integrated.add((s, RDFS.label, Literal("Hot Dog Flier Generation Mission")))
            
            # Link commander to mission
            if commander_uri:
                g_integrated.add((commander_uri, AG.executedMission, s))
                g_integrated.add((s, AG.executedBy, commander_uri))
            
            # Link decisions to mission
            for dec in decision_uris:
                g_integrated.add((dec, AG.partOfMission, s))
                g_integrated.add((s, AG.hasDecision, dec))
            
            print(f"   ✓ Typed mission: {str(s).split('/')[-1]}")
            break
    
    # ============================================================
    # ADD SEMANTIC RELATIONSHIPS
    # ============================================================
    
    # Find quality scores and link them
    for s, p, o in g_integrated:
        if 'qualityScore' in str(p):
            g_integrated.add((s, AG.qualityScore, o))
            try:
                score = float(str(o))
                g_integrated.add((s, AG.meetsQualityThreshold, Literal(score >= 0.85, datatype=XSD.boolean)))
            except:
                pass
    
    # Link prompts to tasks
    for s, p, o in g_integrated:
        if str(p).endswith('hasPrompt'):
            g_integrated.add((s, AG.taskDescription, o))
    
    # ============================================================
    # ADD WORKFLOW STRUCTURE
    # ============================================================
    
    workflow_uri = EX["hot-dog-workflow"]
    g_integrated.add((workflow_uri, RDF.type, AG.Workflow))
    g_integrated.add((workflow_uri, RDF.type, AG.SelfAssemblingPattern))
    g_integrated.add((workflow_uri, RDFS.label, Literal("Hot Dog Flier Workflow")))
    
    if mission_uri:
        g_integrated.add((mission_uri, AG.followsWorkflow, workflow_uri))
    
    # Add coordination patterns
    g_integrated.add((workflow_uri, AG.usesCoordinationPattern, AG.BlackboardCoordination))
    if commander_uri:
        g_integrated.add((commander_uri, AG.participatesIn, AG.BlackboardCoordination))
    
    print(f"\n✅ Integrated graph has {len(g_integrated)} triples")
    print(f"   (Original {len(g_existing)} + Ontology mappings {len(g_integrated) - len(g_existing)})")
    
    return g_integrated

def upload_integrated_kg(g_integrated):
    """Upload the integrated KG to GraphDB"""
    print("\n📤 UPLOADING INTEGRATED KG TO GRAPHDB")
    print("=" * 60)
    
    GRAPHDB_URL = "http://localhost:7200"
    repo_name = "semant-test"
    
    # Clear and upload
    requests.delete(
        f"{GRAPHDB_URL}/repositories/{repo_name}/statements",
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    turtle_data = g_integrated.serialize(format='turtle')
    response = requests.post(
        f"{GRAPHDB_URL}/repositories/{repo_name}/statements",
        data=turtle_data,
        headers={"Content-Type": "text/turtle"}
    )
    
    if response.status_code in [200, 201, 204]:
        print(f"✅ Successfully uploaded integrated KG!")
        
        # Test queries to show integration
        queries = [
            ("Typed Entities", """
                PREFIX ag: <http://example.org/agentKG#>
                PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                
                SELECT ?type (COUNT(?s) as ?count) WHERE {
                    ?s rdf:type ?type .
                    FILTER(STRSTARTS(STR(?type), STR(ag:)))
                }
                GROUP BY ?type
            """),
            ("Decision Chain", """
                PREFIX ag: <http://example.org/agentKG#>
                
                SELECT ?decision ?follows WHERE {
                    ?decision ag:follows ?follows .
                }
                LIMIT 5
            """),
            ("Agent Capabilities", """
                PREFIX ag: <http://example.org/agentKG#>
                
                SELECT ?agent ?capability WHERE {
                    ?agent ag:hasCapability ?capability .
                }
            """)
        ]
        
        for title, query in queries:
            response = requests.post(
                f"{GRAPHDB_URL}/repositories/{repo_name}",
                data={"query": query},
                headers={"Accept": "application/sparql-results+json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                bindings = result.get('results', {}).get('bindings', [])
                print(f"\n📊 {title}:")
                for b in bindings[:5]:
                    print(f"   • {b}")
        
        print(f"\n🎉 INTEGRATION COMPLETE!")
        print(f"\n📊 The integrated KG now has:")
        print(f"   • All original triples preserved")
        print(f"   • Entities typed with ontology classes")
        print(f"   • Semantic relationships added")
        print(f"   • Decision chains linked")
        print(f"   • Workflow structure defined")
        print(f"\n🔍 View in GraphDB:")
        print(f"   http://localhost:7200")
        print(f"   Repository: {repo_name}")
        print(f"   Visual Graph: Search for 'commander' or 'Decision'")
        
        return True
    else:
        print(f"❌ Upload failed: {response.status_code}")
        return False

if __name__ == "__main__":
    # Load existing KG
    g_existing, stats = load_and_analyze_existing()
    
    # Integrate with ontology
    g_integrated = integrate_with_ontology(g_existing, stats)
    
    # Upload to GraphDB
    upload_integrated_kg(g_integrated)
    
    # Save locally
    g_integrated.serialize("integrated_kg_with_ontology.ttl", format="turtle")
    print(f"\n📁 Saved integrated KG to: integrated_kg_with_ontology.ttl")
