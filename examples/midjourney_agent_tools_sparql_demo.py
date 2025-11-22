import os
import sys
import json
import asyncio
from typing import Any, Dict


SPARQL = """
PREFIX core: <http://example.org/core#>
PREFIX mj: <http://example.org/midjourney#>
PREFIX schema: <http://schema.org/>

SELECT ?call ?ts ?input ?media ?url WHERE {
  ?call core:type mj:ToolCall .
  OPTIONAL { ?call core:timestamp ?ts }
  OPTIONAL { ?call mj:input ?input }
  OPTIONAL {
    ?call schema:associatedMedia ?media .
    ?media schema:contentUrl ?url .
  }
}
ORDER BY DESC(?ts)
LIMIT 20
"""


def extract_prompt_from_input(input_json: str) -> str:
    try:
        data = json.loads(input_json)
        return str(data.get("prompt", ""))
    except Exception:
        return ""


async def main():
    if not os.getenv("MIDJOURNEY_API_TOKEN"):
        print("ERROR: MIDJOURNEY_API_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    from kg.models.graph_manager import KnowledgeGraphManager
    from semant.agent_tools.midjourney.kg_logging import KGLogger
    from semant.agent_tools.midjourney.tools.imagine_tool import ImagineTool
    from semant.agent_tools.midjourney.tools.get_task_tool import GetTaskTool

    # Use a shared KG instance so we can query what we log
    kg = KnowledgeGraphManager()
    await kg.initialize()
    logger = KGLogger(kg=kg, agent_id="agent/SparqlDemo")

    imagine = ImagineTool(logger=logger)
    res = await imagine.run(prompt="a minimalist watercolor fox, soft palette", model_version="v7")
    data = res.get("data", res)
    task_id = (data or {}).get("task_id") or (data or {}).get("id")
    if task_id:
        get_task = GetTaskTool(logger=logger)
        await get_task.run(task_id=task_id)

    rows = await kg.query_graph(SPARQL)
    print("Recent ToolCalls (prompt and image URLs):")
    for r in rows:
        prompt = extract_prompt_from_input(r.get("input", "") or "")
        url = r.get("url")
        print(f"- ts={r.get('ts','')} prompt={prompt[:80]!r} url={url or ''}")


if __name__ == "__main__":
    asyncio.run(main())


