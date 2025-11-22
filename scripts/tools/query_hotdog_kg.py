#!/usr/bin/env python3
"""
Demonstrate SPARQL queries on the hot dog flier Knowledge Graph
Shows how agents can query and share information through the KG
"""
import asyncio
from kg.models.graph_manager import KnowledgeGraphManager
from datetime import datetime
import json

async def demonstrate_kg_queries():
    print("🔍 KNOWLEDGE GRAPH QUERY DEMONSTRATION")
    print("=" * 70)
    print("Showing how the hot dog flier mission data is stored and queryable\n")
    
    # Initialize KG
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    print("✅ Connected to Knowledge Graph\n")
    
    # ============================================================
    # QUERY 1: Find all autonomous decisions
    # ============================================================
    print("📊 QUERY 1: Autonomous Decisions Made")
    print("-" * 50)
    
    decisions_query = """
    PREFIX ex: <http://example.org/>
    
    SELECT ?decision ?choice ?context ?timestamp ?agent WHERE {
        ?decision ex:choice ?choice ;
                 ex:context ?context ;
                 ex:timestamp ?timestamp ;
                 ex:madeBy ?agent .
        FILTER(CONTAINS(STR(?agent), "hot-dog"))
    }
    ORDER BY ?timestamp
    LIMIT 15
    """
    
    decisions = await kg.query_graph(decisions_query)
    if decisions:
        print(f"Found {len(decisions)} decisions:")
        for i, d in enumerate(decisions[:5], 1):
            print(f"  {i}. {d['context']}: {d['choice']}")
        if len(decisions) > 5:
            print(f"  ... and {len(decisions) - 5} more decisions")
    else:
        print("  No decisions found")
    
    # ============================================================
    # QUERY 2: Find all Midjourney image generation tasks
    # ============================================================
    print("\n🎨 QUERY 2: Image Generation Tasks")
    print("-" * 50)
    
    images_query = """
    PREFIX mj: <http://example.org/midjourney#>
    PREFIX ex: <http://example.org/>
    
    SELECT DISTINCT ?task ?prompt ?status WHERE {
        ?task mj:prompt ?prompt .
        OPTIONAL { ?task mj:status ?status }
        FILTER(CONTAINS(LCASE(STR(?prompt)), "hot dog") || 
               CONTAINS(LCASE(STR(?task)), "hot-dog"))
    }
    ORDER BY DESC(?task)
    LIMIT 10
    """
    
    images = await kg.query_graph(images_query)
    if images:
        print(f"Found {len(images)} image tasks:")
        for img in images[:3]:
            task_id = str(img['task']).split('/')[-1][:12] if '/' in str(img['task']) else str(img['task'])[:12]
            prompt_preview = str(img['prompt'])[:60] + "..." if len(str(img['prompt'])) > 60 else str(img['prompt'])
            status = img.get('status', 'unknown')
            print(f"  • Task {task_id}...")
            print(f"    Prompt: {prompt_preview}")
            print(f"    Status: {status}")
    else:
        print("  No image tasks found")
    
    # ============================================================
    # QUERY 3: Find quality scores and retries
    # ============================================================
    print("\n📈 QUERY 3: Quality Tracking")
    print("-" * 50)
    
    quality_query = """
    PREFIX ex: <http://example.org/>
    
    SELECT ?item ?quality ?type WHERE {
        ?item ex:qualityScore ?quality .
        OPTIONAL { ?item ex:imageType ?type }
        FILTER(CONTAINS(STR(?item), "hot-dog"))
    }
    ORDER BY ?quality
    """
    
    quality = await kg.query_graph(quality_query)
    if quality:
        print(f"Found {len(quality)} quality scores:")
        for q in quality:
            item_id = str(q['item']).split('/')[-1][:20] if '/' in str(q['item']) else str(q['item'])[:20]
            score = float(q['quality']) if q['quality'] else 0
            img_type = q.get('type', 'unknown')
            status = "✅" if score >= 0.85 else "⚠️"
            print(f"  {status} {img_type}: {score:.2f}")
        
        # Calculate average
        scores = [float(q['quality']) for q in quality if q['quality']]
        if scores:
            avg = sum(scores) / len(scores)
            print(f"\n  Average Quality: {avg:.2f}")
    else:
        print("  No quality scores found")
    
    # ============================================================
    # QUERY 4: Find mission completion status
    # ============================================================
    print("\n🎯 QUERY 4: Mission Status")
    print("-" * 50)
    
    mission_query = """
    PREFIX ex: <http://example.org/>
    
    SELECT ?mission ?status ?decisions ?flier WHERE {
        ?mission ex:type "HotDogMission" ;
                ex:status ?status .
        OPTIONAL { ?mission ex:totalDecisions ?decisions }
        OPTIONAL { ?mission ex:flierLocation ?flier }
    }
    """
    
    missions = await kg.query_graph(mission_query)
    if missions:
        for m in missions:
            print(f"  Mission: {str(m['mission']).split('/')[-1] if '/' in str(m['mission']) else m['mission']}")
            print(f"  Status: {m['status']}")
            if m.get('decisions'):
                print(f"  Total Decisions: {m['decisions']}")
            if m.get('flier'):
                print(f"  Flier: {m['flier']}")
    else:
        print("  No mission data found")
    
    # ============================================================
    # QUERY 5: Agent collaboration through KG
    # ============================================================
    print("\n🤝 QUERY 5: Agent Collaboration")
    print("-" * 50)
    
    agents_query = """
    PREFIX ex: <http://example.org/>
    
    SELECT DISTINCT ?agent ?action ?object WHERE {
        ?agent ?action ?object .
        FILTER(CONTAINS(STR(?agent), "agent") || 
               CONTAINS(STR(?agent), "commander"))
        FILTER(CONTAINS(STR(?object), "hot-dog") ||
               CONTAINS(STR(?action), "decision"))
    }
    LIMIT 10
    """
    
    agents = await kg.query_graph(agents_query)
    if agents:
        print(f"Found {len(agents)} agent interactions:")
        for a in agents[:5]:
            agent = str(a['agent']).split('/')[-1] if '/' in str(a['agent']) else str(a['agent'])
            action = str(a['action']).split('#')[-1] if '#' in str(a['action']) else str(a['action']).split('/')[-1]
            obj = str(a['object'])[:40] + "..." if len(str(a['object'])) > 40 else str(a['object'])
            print(f"  • {agent} -> {action} -> {obj}")
    else:
        print("  No agent interactions found")
    
    # ============================================================
    # QUERY 6: Find the final flier artifact
    # ============================================================
    print("\n📄 QUERY 6: Final Deliverable")
    print("-" * 50)
    
    flier_query = """
    PREFIX ex: <http://example.org/>
    
    SELECT ?flier ?location ?timestamp WHERE {
        ?flier ex:type "HotDogFlier" ;
               ex:location ?location .
        OPTIONAL { ?flier ex:createdAt ?timestamp }
    }
    ORDER BY DESC(?timestamp)
    LIMIT 1
    """
    
    fliers = await kg.query_graph(flier_query)
    if fliers:
        for f in fliers:
            print(f"  ✅ Flier Created!")
            print(f"  📍 Location: {f['location']}")
            if f.get('timestamp'):
                print(f"  🕐 Created: {f['timestamp']}")
    else:
        print("  No flier artifact found")
    
    # ============================================================
    # QUERY 7: Count all hot dog related triples
    # ============================================================
    print("\n📊 QUERY 7: Knowledge Graph Statistics")
    print("-" * 50)
    
    stats_query = """
    SELECT (COUNT(*) as ?count) WHERE {
        ?s ?p ?o .
        FILTER(
            CONTAINS(LCASE(STR(?s)), "hot-dog") || 
            CONTAINS(LCASE(STR(?p)), "hot-dog") || 
            CONTAINS(LCASE(STR(?o)), "hot-dog") ||
            CONTAINS(LCASE(STR(?s)), "hot dog") || 
            CONTAINS(LCASE(STR(?o)), "hot dog")
        )
    }
    """
    
    stats = await kg.query_graph(stats_query)
    if stats and stats[0].get('count'):
        print(f"  Total hot dog related triples: {stats[0]['count']}")
    
    # Show total triples in graph
    total_query = "SELECT (COUNT(*) as ?total) WHERE { ?s ?p ?o }"
    total = await kg.query_graph(total_query)
    if total and total[0].get('total'):
        print(f"  Total triples in KG: {total[0]['total']}")
    
    print("\n" + "=" * 70)
    print("✨ Knowledge Graph Query Demonstration Complete!")
    print("\nThese queries show how agents can:")
    print("  1. Query past decisions for learning")
    print("  2. Find and claim available tasks")
    print("  3. Track quality metrics")
    print("  4. Monitor mission progress")
    print("  5. Discover other agents and their capabilities")
    print("  6. Locate generated artifacts")
    print("  7. Analyze system performance")
    
if __name__ == "__main__":
    asyncio.run(demonstrate_kg_queries())
