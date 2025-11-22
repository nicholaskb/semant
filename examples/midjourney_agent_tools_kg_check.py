import os
import sys
import json
import asyncio
from typing import Any, Dict


async def main():
    token = os.getenv("MIDJOURNEY_API_TOKEN")
    if not token:
        print("ERROR: MIDJOURNEY_API_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    from kg.models.graph_manager import KnowledgeGraphManager
    from semant.agent_tools.midjourney.kg_logging import KGLogger, MJ_NS, SCHEMA_NS
    from semant.agent_tools.midjourney.tools.imagine_tool import ImagineTool
    from semant.agent_tools.midjourney.tools.get_task_tool import GetTaskTool

    # Shared KG across logger and this script so we can query after run
    kg = KnowledgeGraphManager()
    await kg.initialize()
    logger = KGLogger(kg=kg, agent_id="agent/LiveKGCheck")

    tool = ImagineTool(logger=logger)
    res = await tool.run(prompt="a minimalist watercolor fox, soft palette", model_version="v7")
    print("Imagine response (truncated):", json.dumps({k: res.get(k) for k in ("code","message")}))
    # Extract task id and poll once to capture image URLs in KG via get_task
    data = res.get("data", res)
    task_id = (data or {}).get("task_id") or (data or {}).get("id")
    if task_id:
        status_tool = GetTaskTool(logger=logger)
        await status_tool.run(task_id=task_id)

    # Query all triples and extract ToolCall inputs and ImageObjects
    all_data: Dict[str, Dict[str, Any]] = await kg.query({})
    tool_calls = [s for s in all_data.keys() if s.startswith(f"{MJ_NS}ToolCall/")]
    print(f"Found {len(tool_calls)} ToolCall node(s)")

    for s in tool_calls:
        pred_map = all_data[s]
        mj_input = pred_map.get(f"{MJ_NS}input")
        print("ToolCall inputs JSON:", mj_input)
        assoc = pred_map.get(f"{SCHEMA_NS}associatedMedia")
        if assoc:
            print("Associated media node:", assoc)
            media_map = all_data.get(assoc, {})
            print("Media contentUrl:", media_map.get(f"{SCHEMA_NS}contentUrl"))


if __name__ == "__main__":
    asyncio.run(main())


