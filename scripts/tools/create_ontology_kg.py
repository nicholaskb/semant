#!/usr/bin/env python3
"""
Create a properly interconnected Knowledge Graph with ontology for the Hot Dog Mission
This creates rich semantic relationships using the agentic ontology
"""
import requests
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, OWL, XSD
from datetime import datetime
import uuid

# Namespaces
AG = Namespace("http://example.org/agentKG#")
EX = Namespace("http://example.org/")
MISSION = Namespace("http://example.org/mission/")
AGENT = Namespace("http://example.org/agent/")
TASK = Namespace("http://example.org/task/")
DECISION = Namespace("http://example.org/decision/")
IMAGE = Namespace("http://example.org/image/")
WORKFLOW = Namespace("http://example.org/workflow/")
PROV = Namespace("http://www.w3.org/ns/prov#")
DCT = Namespace("http://purl.org/dc/terms/")

def create_ontology_based_kg():
    """Create a rich, interconnected KG using proper ontology"""
    g = Graph()
    
    # Bind namespaces for cleaner output
    g.bind("ag", AG)
    g.bind("ex", EX)
    g.bind("mission", MISSION)
    g.bind("agent", AGENT)
    g.bind("task", TASK)
    g.bind("decision", DECISION)
    g.bind("image", IMAGE)
    g.bind("workflow", WORKFLOW)
    g.bind("prov", PROV)
    g.bind("dct", DCT)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)
    
    print("🔨 Building Ontology-Based Knowledge Graph")
    print("=" * 60)
    
    # ============================================================
    # 1. DEFINE THE MISSION
    # ============================================================
    mission_uri = MISSION["hot-dog-flier-e7dd2995"]
    g.add((mission_uri, RDF.type, AG.Mission))
    g.add((mission_uri, RDF.type, AG.WorkflowExecution))
    g.add((mission_uri, RDFS.label, Literal("Hot Dog Flier Generation Mission")))
    g.add((mission_uri, AG.hasObjective, Literal("Create promotional flier for hot dog business")))
    g.add((mission_uri, AG.status, Literal("completed")))
    g.add((mission_uri, DCT.created, Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))
    
    # ============================================================
    # 2. DEFINE THE AGENT WITH RICH PROPERTIES
    # ============================================================
    commander = AGENT["supreme-hot-dog-commander"]
    g.add((commander, RDF.type, AG.Agent))
    g.add((commander, RDF.type, AG.AutonomousAgent))
    g.add((commander, RDFS.label, Literal("Supreme Hot Dog Commander")))
    g.add((commander, AG.hasRole, AG.Orchestrator))
    g.add((commander, AG.hasRole, AG.DecisionMaker))
    g.add((commander, AG.hasCapability, AG.ImageGeneration))
    g.add((commander, AG.hasCapability, AG.QualityAssessment))
    g.add((commander, AG.hasCapability, AG.AutonomousDecisionMaking))
    g.add((commander, AG.executedMission, mission_uri))
    g.add((commander, AG.autonomyLevel, Literal(10, datatype=XSD.integer)))
    
    # ============================================================
    # 3. DEFINE THE WORKFLOW
    # ============================================================
    workflow = WORKFLOW["hot-dog-flier-workflow"]
    g.add((workflow, RDF.type, AG.Workflow))
    g.add((workflow, RDF.type, AG.SelfAssemblingPattern))
    g.add((workflow, RDFS.label, Literal("Hot Dog Flier Creation Workflow")))
    g.add((workflow, AG.hasPhase, WORKFLOW["design-phase"]))
    g.add((workflow, AG.hasPhase, WORKFLOW["generation-phase"]))
    g.add((workflow, AG.hasPhase, WORKFLOW["composition-phase"]))
    g.add((mission_uri, AG.followsWorkflow, workflow))
    
    # ============================================================
    # 4. CREATE INTERCONNECTED DECISIONS
    # ============================================================
    decisions = [
        ("d1", "Choose Flier Style", "Professional Commercial", WORKFLOW["design-phase"]),
        ("d2", "Choose Layout", "Three-Panel Horizontal", WORKFLOW["design-phase"]),
        ("d3", "Choose Color Palette", "Vibrant and Appetizing", WORKFLOW["design-phase"]),
        ("d4", "Retry Hero Image", "Quality below threshold", WORKFLOW["generation-phase"]),
        ("d5", "Retry Hero Image", "Quality below threshold", WORKFLOW["generation-phase"]),
        ("d6", "Retry Hero Image", "Quality below threshold", WORKFLOW["generation-phase"]),
        ("d7", "Retry Hero Image", "Quality below threshold", WORKFLOW["generation-phase"]),
        ("d8", "Retry Ingredients", "Quality below threshold", WORKFLOW["generation-phase"]),
        ("d9", "Retry Atmosphere", "Quality below threshold", WORKFLOW["generation-phase"]),
        ("d10", "Choose Headline", "FRESH HOT DOGS DAILY!", WORKFLOW["composition-phase"]),
        ("d11", "Choose Tagline", "Made with Premium Ingredients", WORKFLOW["composition-phase"])
    ]
    
    prev_decision = None
    for dec_id, context, choice, phase in decisions:
        dec_uri = DECISION[dec_id]
        g.add((dec_uri, RDF.type, AG.Decision))
        g.add((dec_uri, RDF.type, PROV.Activity))
        g.add((dec_uri, RDFS.label, Literal(context)))
        g.add((dec_uri, AG.decisionContext, Literal(context)))
        g.add((dec_uri, AG.selectedChoice, Literal(choice)))
        g.add((dec_uri, PROV.wasAttributedTo, commander))
        g.add((dec_uri, AG.madeBy, commander))
        g.add((dec_uri, AG.partOfMission, mission_uri))
        g.add((dec_uri, AG.inPhase, phase))
        g.add((mission_uri, AG.hasDecision, dec_uri))
        
        # Chain decisions
        if prev_decision:
            g.add((dec_uri, AG.follows, prev_decision))
            g.add((prev_decision, AG.precedes, dec_uri))
        prev_decision = dec_uri
    
    # ============================================================
    # 5. CREATE TASKS WITH RELATIONSHIPS
    # ============================================================
    tasks = [
        ("t1", "Generate Hero Shot", "hero_shot", WORKFLOW["generation-phase"]),
        ("t2", "Generate Ingredients Image", "ingredients", WORKFLOW["generation-phase"]),
        ("t3", "Generate Atmosphere Image", "atmosphere", WORKFLOW["generation-phase"]),
        ("t4", "Compose Final Flier", "composition", WORKFLOW["composition-phase"])
    ]
    
    task_uris = {}
    for task_id, label, task_type, phase in tasks:
        task_uri = TASK[task_id]
        task_uris[task_id] = task_uri
        g.add((task_uri, RDF.type, AG.Task))
        g.add((task_uri, RDF.type, PROV.Activity))
        g.add((task_uri, RDFS.label, Literal(label)))
        g.add((task_uri, AG.taskType, Literal(task_type)))
        g.add((task_uri, AG.executedBy, commander))
        g.add((task_uri, AG.partOfWorkflow, workflow))
        g.add((task_uri, AG.inPhase, phase))
        g.add((task_uri, AG.status, Literal("completed")))
        g.add((mission_uri, AG.hasTask, task_uri))
        g.add((commander, AG.executed, task_uri))
    
    # Task dependencies
    g.add((task_uris["t2"], AG.dependsOn, task_uris["t1"]))
    g.add((task_uris["t3"], AG.dependsOn, task_uris["t2"]))
    g.add((task_uris["t4"], AG.dependsOn, task_uris["t3"]))
    
    # ============================================================
    # 6. CREATE IMAGES WITH QUALITY METRICS
    # ============================================================
    images = [
        ("img1", "Hero Shot Image", 0.95, task_uris["t1"]),
        ("img2", "Ingredients Image", 0.92, task_uris["t2"]),
        ("img3", "Atmosphere Image", 0.93, task_uris["t3"])
    ]
    
    image_uris = []
    for img_id, label, quality, task in images:
        img_uri = IMAGE[img_id]
        image_uris.append(img_uri)
        g.add((img_uri, RDF.type, AG.Artifact))
        g.add((img_uri, RDF.type, PROV.Entity))
        g.add((img_uri, RDFS.label, Literal(label)))
        g.add((img_uri, AG.qualityScore, Literal(quality, datatype=XSD.float)))
        g.add((img_uri, PROV.wasGeneratedBy, task))
        g.add((img_uri, PROV.wasAttributedTo, commander))
        g.add((task, PROV.generated, img_uri))
        g.add((img_uri, AG.meetsQualityThreshold, Literal(quality >= 0.85, datatype=XSD.boolean)))
    
    # ============================================================
    # 7. CREATE FINAL ARTIFACT
    # ============================================================
    flier = IMAGE["hot-dog-flier"]
    g.add((flier, RDF.type, AG.Artifact))
    g.add((flier, RDF.type, AG.FinalDeliverable))
    g.add((flier, RDFS.label, Literal("Hot Dog Promotional Flier")))
    g.add((flier, DCT["format"], Literal("image/png")))
    g.add((flier, AG.location, Literal("midjourney_integration/jobs/hot-dog-flier-e7dd2995/hot_dog_flier.png")))
    g.add((flier, PROV.wasGeneratedBy, task_uris["t4"]))
    g.add((flier, PROV.wasAttributedTo, commander))
    g.add((mission_uri, AG.produced, flier))
    
    # Connect images to final flier
    for img_uri in image_uris:
        g.add((flier, PROV.wasDerivedFrom, img_uri))
        g.add((img_uri, AG.usedIn, flier))
    
    # ============================================================
    # 8. ADD COORDINATION PATTERNS
    # ============================================================
    g.add((mission_uri, AG.usesCoordinationPattern, AG.BlackboardCoordination))
    g.add((mission_uri, AG.usesCoordinationPattern, AG.SelfAssemblingPattern))
    g.add((commander, AG.participatesIn, AG.BlackboardCoordination))
    
    # ============================================================
    # 9. ADD METRICS AND PERFORMANCE
    # ============================================================
    performance = MISSION["performance-metrics"]
    g.add((performance, RDF.type, AG.PerformanceMetrics))
    g.add((performance, AG.totalDecisions, Literal(11, datatype=XSD.integer)))
    g.add((performance, AG.totalRetries, Literal(6, datatype=XSD.integer)))
    g.add((performance, AG.averageQuality, Literal(0.93, datatype=XSD.float)))
    g.add((performance, AG.missionDuration, Literal("PT5M", datatype=XSD.duration)))
    g.add((mission_uri, AG.hasPerformanceMetrics, performance))
    
    print(f"✅ Created {len(g)} interconnected triples")
    return g

def upload_to_graphdb(graph):
    """Upload the ontology-based KG to GraphDB"""
    GRAPHDB_URL = "http://localhost:7200"
    repo_name = "semant-test"
    
    print(f"\n📤 Uploading to GraphDB repository: {repo_name}")
    
    # Clear existing data
    requests.delete(
        f"{GRAPHDB_URL}/repositories/{repo_name}/statements",
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    # Upload new data
    turtle_data = graph.serialize(format='turtle')
    response = requests.post(
        f"{GRAPHDB_URL}/repositories/{repo_name}/statements",
        data=turtle_data,
        headers={"Content-Type": "text/turtle"}
    )
    
    if response.status_code in [200, 201, 204]:
        print(f"✅ Successfully uploaded!")
        
        # Run test query
        test_query = """
        PREFIX ag: <http://example.org/agentKG#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?subject ?predicate ?object WHERE {
            ?subject ?predicate ?object .
            ?subject rdfs:label ?label .
        }
        LIMIT 10
        """
        
        response = requests.post(
            f"{GRAPHDB_URL}/repositories/{repo_name}",
            data={"query": test_query},
            headers={"Accept": "application/sparql-results+json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            bindings = result.get('results', {}).get('bindings', [])
            print(f"\n🔍 Sample of interconnected data:")
            for b in bindings[:5]:
                s = str(b['subject']['value']).split('/')[-1][:20]
                p = str(b['predicate']['value']).split('#')[-1][:20]
                o = str(b['object']['value'])[:30]
                print(f"   {s} -- {p} --> {o}")
        
        print(f"\n🎉 Ontology-based KG ready in GraphDB!")
        print(f"\n📊 To explore:")
        print(f"1. Open: http://localhost:7200")
        print(f"2. Select: {repo_name}")
        print(f"3. Visual Graph: Search for 'supreme-hot-dog-commander'")
        print(f"4. The graph now has:")
        print(f"   • Proper class hierarchies (Agent, Task, Decision, Artifact)")
        print(f"   • Rich relationships (follows, precedes, dependsOn, wasDerivedFrom)")
        print(f"   • Workflow phases and coordination patterns")
        print(f"   • Performance metrics and quality scores")
        print(f"   • Full provenance tracking")
        
        return True
    else:
        print(f"❌ Upload failed: {response.status_code}")
        return False

if __name__ == "__main__":
    # Create the ontology-based KG
    kg = create_ontology_based_kg()
    
    # Upload to GraphDB
    upload_to_graphdb(kg)
    
    # Also save locally
    kg.serialize("hot_dog_mission_ontology.ttl", format="turtle")
    print(f"\n📁 Also saved to: hot_dog_mission_ontology.ttl")
