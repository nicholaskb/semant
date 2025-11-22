#!/usr/bin/env python3
"""
Test REAL Midjourney + KG Integration
This demonstrates the KG tools working with actual Midjourney generation
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

async def test_kg_midjourney_integration():
    """Test real Midjourney with KG orchestration"""
    
    print("🎯 REAL MIDJOURNEY + KG INTEGRATION TEST")
    print("=" * 60)
    
    # Check environment
    api_token = os.getenv('MIDJOURNEY_API_TOKEN')
    if not api_token or api_token == 'YOUR_ACTUAL_MIDJOURNEY_TOKEN_HERE':
        print("❌ MIDJOURNEY_API_TOKEN not configured")
        print("Please set it in your .env file")
        return
    
    print(f"✅ API Token found: {api_token[:10]}...")
    
    # Initialize KG
    from kg.models.graph_manager import KnowledgeGraphManager
    from agents.tools.kg_tools import KGTools
    
    print("\n📊 Initializing Knowledge Graph...")
    kg = KnowledgeGraphManager(persistent_storage=True)
    await kg.initialize()
    kg_tools = KGTools(kg, "test_agent")
    print("✅ Knowledge Graph initialized")
    
    # Initialize Midjourney client
    from midjourney_integration.client import MidjourneyClient
    
    print("\n🎨 Initializing Midjourney client...")
    mj_client = MidjourneyClient(api_token=api_token)
    print("✅ Midjourney client ready")
    
    # Create an image generation task in the KG
    print("\n📝 Creating image generation task in KG...")
    
    task_id = await kg_tools.create_task_node(
        task_name="Generate Product Hero Image",
        task_type="image_generation",
        description="Generate a hero image for our product",
        priority="high",
        metadata={
            "prompt": "modern smartphone floating in air, dramatic lighting, product photography, clean background --ar 16:9 --v 6",
            "version": "v6",
            "aspect_ratio": "16:9",
            "process_mode": "fast"
        }
    )
    
    print(f"✅ Created task: {task_id}")
    
    # Claim the task
    print("\n🔒 Claiming task...")
    claimed = await kg_tools.claim_task(task_id)
    if not claimed:
        print("❌ Could not claim task")
        return
    print("✅ Task claimed")
    
    # Get task details from KG
    print("\n📖 Reading task details from KG...")
    query = f"""
    PREFIX core: <http://example.org/core#>
    SELECT ?name ?description ?metadata WHERE {{
        <{task_id}> core:taskName ?name ;
                   core:description ?description ;
                   core:metadata ?metadata .
    }}
    """
    
    results = await kg.query_graph(query)
    if not results:
        print("❌ Task not found in KG")
        return
        
    task_data = results[0]
    metadata = json.loads(task_data['metadata'])
    
    print(f"   Task: {task_data['name']}")
    print(f"   Prompt: {metadata['prompt'][:50]}...")
    
    # Submit to Midjourney
    print("\n🚀 Submitting to Midjourney...")
    
    try:
        result = await mj_client.submit_imagine(
            prompt=metadata['prompt'],
            model_version=metadata.get('version', 'v6'),
            aspect_ratio=metadata.get('aspect_ratio', '16:9'),
            process_mode=metadata.get('process_mode', 'fast')
        )
        
        if not result:
            print("❌ Failed to submit to Midjourney")
            await kg_tools.update_task_status(task_id, "failed", error="Submission failed")
            return
            
        mj_task_id = result.get('task_id')
        print(f"✅ Submitted! Midjourney task ID: {mj_task_id}")
        
        # Store initial result in KG
        await kg_tools.update_task_status(
            task_id,
            "in_progress",
            result={"midjourney_task_id": mj_task_id, "status": "processing"}
        )
        
        # Poll for completion
        print("\n⏳ Waiting for image generation...")
        max_attempts = 60  # 5 minutes
        
        for i in range(max_attempts):
            await asyncio.sleep(5)
            
            status = await mj_client.poll_task(mj_task_id)
            current_status = status.get('status', 'unknown')
            
            if current_status == 'completed':
                print(f"✅ Image generation completed!")
                
                # Get image URL
                output = status.get('output', {})
                image_url = output.get('image_url')
                
                if image_url:
                    print(f"   Image URL: {image_url}")
                    
                    # Update task in KG as completed
                    await kg_tools.update_task_status(
                        task_id,
                        "completed",
                        result={
                            "midjourney_task_id": mj_task_id,
                            "image_url": image_url,
                            "completed_at": datetime.utcnow().isoformat()
                        }
                    )
                    
                    # Save metadata
                    job_dir = Path(f"midjourney_integration/jobs/{mj_task_id}")
                    job_dir.mkdir(parents=True, exist_ok=True)
                    
                    with open(job_dir / "metadata.json", "w") as f:
                        json.dump({
                            "kg_task_id": task_id,
                            "midjourney_task_id": mj_task_id,
                            "prompt": metadata['prompt'],
                            "image_url": image_url,
                            "status": "completed"
                        }, f, indent=2)
                    
                    print(f"   Saved to: {job_dir}")
                    
                    # Query KG to verify storage
                    print("\n🔍 Verifying in Knowledge Graph...")
                    
                    verify_query = f"""
                    PREFIX core: <http://example.org/core#>
                    SELECT ?status ?result WHERE {{
                        <{task_id}> core:status ?status ;
                                   core:result ?result .
                    }}
                    """
                    
                    verify_results = await kg.query_graph(verify_query)
                    if verify_results:
                        print(f"   KG Status: {verify_results[0]['status']}")
                        result_data = json.loads(verify_results[0]['result'])
                        print(f"   Stored URL: {result_data.get('image_url', 'N/A')}")
                    
                    print("\n🎉 SUCCESS! Image generated and stored in KG!")
                    print(f"   Open image: {image_url}")
                    
                break
                
            elif current_status == 'failed':
                error = status.get('error', 'Unknown error')
                print(f"❌ Generation failed: {error}")
                
                await kg_tools.update_task_status(
                    task_id,
                    "failed",
                    error=error
                )
                break
                
            else:
                print(f"   Status: {current_status} ({i+1}/{max_attempts})")
                
        else:
            # Timeout
            print("⏱️ Timeout waiting for completion")
            await kg_tools.update_task_status(
                task_id,
                "failed",
                error="Timeout after 5 minutes"
            )
            
    except Exception as e:
        print(f"❌ Error: {e}")
        await kg_tools.update_task_status(
            task_id,
            "failed",
            error=str(e)
        )
        
    # Query all image tasks from KG
    print("\n📊 Querying all image tasks from KG...")
    
    all_tasks_query = """
    PREFIX core: <http://example.org/core#>
    SELECT ?task ?name ?status WHERE {
        ?task a core:Task ;
              core:taskType "image_generation" ;
              core:taskName ?name ;
              core:status ?status .
    }
    ORDER BY DESC(?task)
    LIMIT 5
    """
    
    all_results = await kg.query_graph(all_tasks_query)
    
    print(f"Found {len(all_results)} recent image tasks:")
    for r in all_results:
        task_uri = r['task'].split('/')[-1]
        print(f"   {task_uri}: {r['name']} - {r['status']}")
    
    print("\n✨ Integration test complete!")
    print("The KG now contains the task, its status, and the generated image URL")


if __name__ == "__main__":
    asyncio.run(test_kg_midjourney_integration())
