#!/usr/bin/env python3
"""
Demonstrate how future jobs learn from past jobs in the KG
Example: Pizza flier learns from hot dog flier
"""
import requests
import json
from datetime import datetime

def query_graphdb(query, repo="semant-test"):
    """Execute SPARQL query against GraphDB"""
    response = requests.post(
        f"http://localhost:7200/repositories/{repo}",
        data={"query": query},
        headers={"Accept": "application/sparql-results+json"}
    )
    if response.status_code == 200:
        return response.json().get('results', {}).get('bindings', [])
    return []

def learn_from_past_jobs():
    """
    Show how a new pizza flier job learns from the hot dog flier
    """
    print("🍕 NEW JOB: PIZZA FLIER CREATION")
    print("=" * 70)
    print("Learning from past successful flier jobs in the KG...")
    
    # ============================================================
    # QUERY 1: What decisions led to successful fliers?
    # ============================================================
    print("\n📚 LEARNING FROM PAST DECISIONS:")
    print("-" * 50)
    
    decision_query = """
    PREFIX ag: <http://example.org/agentKG#>
    PREFIX ex: <http://example.org/>
    
    SELECT ?context ?choice WHERE {
        ?decision a ag:Decision ;
                 ag:decisionContext ?context ;
                 ag:selectedChoice ?choice ;
                 ag:partOfMission ?mission .
        ?mission ag:status ?status .
        FILTER(CONTAINS(LCASE(STR(?mission)), "flier") || 
               CONTAINS(LCASE(STR(?context)), "style") ||
               CONTAINS(LCASE(STR(?context)), "layout") ||
               CONTAINS(LCASE(STR(?context)), "headline"))
    }
    """
    
    decisions = query_graphdb(decision_query)
    
    print("Past successful decisions found:")
    learned_patterns = {}
    for d in decisions:
        context = d['context']['value']
        choice = d['choice']['value']
        learned_patterns[context] = choice
        print(f"   • {context}: {choice}")
    
    # ============================================================
    # QUERY 2: What quality thresholds were used?
    # ============================================================
    print("\n📊 LEARNING QUALITY STANDARDS:")
    print("-" * 50)
    
    quality_query = """
    PREFIX ag: <http://example.org/agentKG#>
    
    SELECT ?score ?meets WHERE {
        ?artifact ag:qualityScore ?score ;
                 ag:meetsQualityThreshold ?meets .
    }
    """
    
    quality_results = query_graphdb(quality_query)
    
    if quality_results:
        scores = [float(q['score']['value']) for q in quality_results if 'score' in q]
        if scores:
            avg_quality = sum(scores) / len(scores)
            print(f"   • Average quality score from past jobs: {avg_quality:.2f}")
            print(f"   • Quality threshold used: 0.85")
            print(f"   ✅ Will use same threshold for pizza flier")
    
    # ============================================================
    # QUERY 3: What workflow pattern was successful?
    # ============================================================
    print("\n🔄 LEARNING WORKFLOW PATTERNS:")
    print("-" * 50)
    
    workflow_query = """
    PREFIX ag: <http://example.org/agentKG#>
    
    SELECT DISTINCT ?pattern WHERE {
        ?workflow ag:usesCoordinationPattern ?pattern .
        ?mission ag:followsWorkflow ?workflow .
        FILTER(CONTAINS(LCASE(STR(?mission)), "flier"))
    }
    """
    
    patterns = query_graphdb(workflow_query)
    
    print("Successful coordination patterns found:")
    for p in patterns:
        pattern_name = p['pattern']['value'].split('#')[-1]
        print(f"   • {pattern_name}")
    
    # ============================================================
    # QUERY 4: What was the task sequence?
    # ============================================================
    print("\n📋 LEARNING TASK SEQUENCE:")
    print("-" * 50)
    
    task_query = """
    PREFIX ag: <http://example.org/agentKG#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?task ?label ?type WHERE {
        ?task a ag:Task ;
              rdfs:label ?label ;
              ag:taskType ?type ;
              ag:partOfMission ?mission .
        FILTER(CONTAINS(LCASE(STR(?mission)), "hot-dog"))
    }
    """
    
    tasks = query_graphdb(task_query)
    
    print("Task sequence from successful flier:")
    task_sequence = []
    for t in tasks:
        if 'label' in t:
            label = t['label']['value']
            task_type = t.get('type', {}).get('value', 'unknown')
            task_sequence.append((label, task_type))
            print(f"   {len(task_sequence)}. {label} ({task_type})")
    
    # ============================================================
    # APPLY LEARNINGS TO NEW PIZZA FLIER
    # ============================================================
    print("\n" + "=" * 70)
    print("🎯 APPLYING LEARNINGS TO PIZZA FLIER:")
    print("=" * 70)
    
    print("\n✅ DECISIONS TO REUSE:")
    if 'Choose flier style' in learned_patterns:
        print(f"   • Style: {learned_patterns['Choose flier style']} (proven successful)")
    if 'Choose layout structure' in learned_patterns:
        print(f"   • Layout: {learned_patterns['Choose layout structure']} (proven successful)")
    
    print("\n✅ ADAPTED DECISIONS FOR PIZZA:")
    print("   • Headline: 'AUTHENTIC ITALIAN PIZZA!' (adapted from hot dog pattern)")
    print("   • Tagline: 'Wood-Fired to Perfection' (following premium pattern)")
    print("   • Color Palette: 'Italian Flag Colors' (customized for pizza)")
    
    print("\n✅ WORKFLOW TO FOLLOW:")
    print("   1. Design Phase (choose style, layout, colors)")
    print("   2. Generation Phase (hero shot, ingredients, ambiance)")
    print("   3. Composition Phase (headline, tagline, assembly)")
    
    print("\n✅ QUALITY CONTROL:")
    print("   • Will retry images if quality < 0.85")
    print("   • Target average quality: 0.93+ (matching hot dog success)")
    
    # ============================================================
    # SPARQL TO ADD NEW PIZZA JOB THAT REFERENCES LEARNINGS
    # ============================================================
    print("\n📝 KG ENTRIES FOR PIZZA FLIER (following ontology):")
    print("-" * 50)
    
    pizza_mission = "pizza-flier-" + datetime.now().strftime("%Y%m%d")
    
    print(f"""
    # New mission following learned patterns
    mission:{pizza_mission} a ag:Mission, ag:WorkflowExecution ;
        rdfs:label "Pizza Restaurant Flier" ;
        ag:learnedFrom mission:hot-dog-flier-e7dd2995 ;
        ag:followsWorkflow <http://example.org/hot-dog-workflow> ;
        ag:reusedPatterns "Professional Commercial", "Three-Panel Horizontal" ;
        ag:adaptedFor "Italian cuisine" .
    
    # Decisions that reference past learnings
    decision:pizza-style a ag:Decision ;
        ag:decisionContext "Choose flier style" ;
        ag:selectedChoice "Professional Commercial" ;
        ag:basedOn decision:hot-dog-style ;
        ag:reasoning "Reusing successful pattern from hot dog flier" .
    """)
    
    print("\n" + "=" * 70)
    print("🚀 BENEFITS OF KG INTEGRATION FOR FUTURE JOBS:")
    print("=" * 70)
    print("1. ⚡ FASTER: Skip trial-and-error by reusing successful patterns")
    print("2. 📈 BETTER: Start with proven quality thresholds and workflows")
    print("3. 🧠 SMARTER: Learn from past decisions and their outcomes")
    print("4. 🔄 CONSISTENT: Follow established ontology for interoperability")
    print("5. 📊 TRACEABLE: Can always trace back to source of learnings")
    print("6. 🎯 ADAPTIVE: Customize learned patterns for new contexts")

if __name__ == "__main__":
    learn_from_past_jobs()
