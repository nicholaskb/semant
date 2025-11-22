import os
import sys
import json
import asyncio
import argparse
from typing import Any, Dict


SPARQL_LATEST = """
PREFIX core: <http://example.org/core#>
PREFIX mj: <http://example.org/midjourney#>
PREFIX schema: <http://schema.org/>

SELECT ?call ?ts ?input ?task ?media ?url WHERE {
  ?call core:type mj:ToolCall .
  OPTIONAL { ?call core:timestamp ?ts }
  OPTIONAL { ?call mj:input ?input }
  OPTIONAL { ?call core:relatedTo ?task }
  OPTIONAL {
    ?call schema:associatedMedia ?media .
    ?media schema:contentUrl ?url .
  }
}
ORDER BY DESC(?ts)
LIMIT 20
"""


def extract_prompt(input_json: str) -> str:
    try:
        data = json.loads(input_json or "{}")
        return str(data.get("prompt", ""))
    except Exception:
        return ""


async def run_and_log(prompt: str, version: str, interval: float, timeout: int) -> None:
    from kg.models.graph_manager import KnowledgeGraphManager
    from semant.agent_tools.midjourney.kg_logging import KGLogger
    from semant.agent_tools.midjourney.tools.imagine_tool import ImagineTool
    from semant.agent_tools.midjourney.tools.get_task_tool import GetTaskTool

    kg = KnowledgeGraphManager()
    await kg.initialize()
    logger = KGLogger(kg=kg, agent_id="agent/LatestDemo")

    imagine = ImagineTool(logger=logger)
    res = await imagine.run(prompt=prompt, model_version=version)
    data = res.get("data", res)
    task_id = (data or {}).get("task_id") or (data or {}).get("id")
    if task_id:
        get_task = GetTaskTool(logger=logger)
        # simple poll loop inline
        elapsed = 0.0
        while elapsed < timeout:
            status = await get_task.run(task_id=task_id)
            sd = status.get("data", status) or {}
            if sd.get("status") in {"completed", "finished"}:
                break
            await asyncio.sleep(interval)
            elapsed += interval

    # Get recent ToolCalls; pick the most recent one with a non-empty prompt if possible.
    rows = await kg.query_graph(SPARQL_LATEST)
    if not rows:
        print("No ToolCalls found")
        return
    chosen = None
    for r in rows:
        pr = extract_prompt(r.get("input", "") or "")
        chosen = r if pr else (chosen or r)
        if pr:
            break
    # If no url present on that ToolCall, try to find any associatedMedia for the same task
    image_url = chosen.get("url")
    if (not image_url) and chosen.get("task"):
        task_uri = chosen["task"]
        # secondary query to fetch media for same task
        q = f"""
PREFIX core: <http://example.org/core#>
PREFIX schema: <http://schema.org/>

SELECT ?url WHERE {{
  ?c core:relatedTo <{task_uri}> .
  ?c schema:associatedMedia ?m .
  ?m schema:contentUrl ?url .
}} LIMIT 1
"""
        extra = await kg.query_graph(q)
        if extra:
            image_url = extra[0].get("url", image_url)
    print(json.dumps({
        "timestamp": chosen.get("ts", ""),
        "prompt": extract_prompt(chosen.get("input", "") or ""),
        "image_url": image_url or ""
    }))


async def query_only() -> None:
    from kg.models.graph_manager import KnowledgeGraphManager
    kg = KnowledgeGraphManager()
    await kg.initialize()
    rows = await kg.query_graph(SPARQL_LATEST)
    if not rows:
        print("No ToolCalls found")
        return
    chosen = None
    for r in rows:
        pr = extract_prompt(r.get("input", "") or "")
        chosen = r if pr else (chosen or r)
        if pr:
            break
    image_url = chosen.get("url")
    if (not image_url) and chosen.get("task"):
        task_uri = chosen["task"]
        q = f"""
PREFIX core: <http://example.org/core#>
PREFIX schema: <http://schema.org/>

SELECT ?url WHERE {{
  ?c core:relatedTo <{task_uri}> .
  ?c schema:associatedMedia ?m .
  ?m schema:contentUrl ?url .
}} LIMIT 1
"""
        extra = await kg.query_graph(q)
        if extra:
            image_url = extra[0].get("url", image_url)
    print(json.dumps({
        "timestamp": chosen.get("ts", ""),
        "prompt": extract_prompt(chosen.get("input", "") or ""),
        "image_url": image_url or ""
    }))


async def main():
    parser = argparse.ArgumentParser(description="Print latest prompt+image URL from the knowledge graph. Optionally run a new imagine first.")
    parser.add_argument("--run", action="store_true", help="Run a live imagine and poll first, then print the latest entry")
    parser.add_argument("--prompt", default="a minimalist watercolor fox, soft palette")
    parser.add_argument("--version", choices=["v6", "v7"], default="v7")
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    if args.run and not os.getenv("MIDJOURNEY_API_TOKEN"):
        print("ERROR: MIDJOURNEY_API_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    if args.run:
        await run_and_log(args.prompt, args.version, args.interval, args.timeout)
    else:
        await query_only()


if __name__ == "__main__":
    asyncio.run(main())


