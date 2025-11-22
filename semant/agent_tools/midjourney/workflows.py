from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from semant.agent_tools.midjourney import REGISTRY


async def imagine_then_mirror(
    *,
    prompt: str,
    version: str = "v7",
    aspect_ratio: Optional[str] = None,
    process_mode: Optional[str] = None,
    cref: Optional[str] = None,
    cw: Optional[int] = None,
    oref: Optional[str] = None,
    ow: Optional[int] = None,
    poll_interval: float = 5.0,
    poll_timeout: int = 900,
) -> Dict[str, Any]:
    """Run imagine → poll → mirror using tool registry. Returns task_id, image_url, gcs_url."""
    imagine_tool = REGISTRY["mj.imagine"]()
    res = await imagine_tool.run(
        prompt=prompt,
        model_version=version,
        aspect_ratio=aspect_ratio,
        process_mode=process_mode,
        cref=cref,
        cw=cw,
        oref=oref,
        ow=ow,
    )
    data = res.get("data", res)
    task_id = (data or {}).get("task_id") or (data or {}).get("id")
    if not task_id:
        return {"error": "no_task_id", "raw": res}

    get_task_tool = REGISTRY["mj.get_task"]()
    elapsed = 0.0
    final: Dict[str, Any] = {}
    while elapsed < poll_timeout:
        status = await get_task_tool.run(task_id=task_id)
        d = status.get("data", status) or {}
        if d.get("status") in {"completed", "finished"}:
            final = d
            break
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
    if not final:
        return {"error": "timeout", "task_id": task_id}

    output = (final or {}).get("output", {})
    image_url = output.get("image_url") or output.get("url")
    gcs_url = None
    if image_url:
        mirror_tool = REGISTRY["mj.gcs_mirror"]()
        mirrored = await mirror_tool.run(source_url=image_url, task_id=task_id, filename="image.png")
        gcs_url = mirrored.get("gcs_url")

    return {
        "task_id": task_id,
        "image_url": image_url,
        "gcs_url": gcs_url,
        "final": final,
    }


# New: Generate multiple themed portraits from reference images
async def generate_themed_portraits(
    *,
    theme: str,
    face_image_urls: list[str],
    count: int = 10,
    version: str = "v7",
    aspect_ratio: str | None = None,
    process_mode: str | None = None,
    cw: int | None = None,
    ow: int | None = None,
    poll_interval: float = 5.0,
    poll_timeout: int = 900,
) -> dict[str, object]:
    """Create N themed images leveraging a reference image depending on model version.

    - For V7, uses --oref/--ow
    - For V6, uses --cref/--cw
    Returns: { images: [ {task_id, image_url, gcs_url}... ], errors: [] }
    """
    results: list[dict[str, object]] = []
    errors: list[str] = []
    if not face_image_urls:
        return {"images": results, "errors": ["no_face_images"]}

    ref_url = face_image_urls[0]

    imagine_tool = REGISTRY["mj.imagine"]()
    get_task_tool = REGISTRY["mj.get_task"]()
    mirror_tool = REGISTRY["mj.gcs_mirror"]()
    action_tool = REGISTRY.get("mj.action")()

    # Build prompt
    base_prompt = theme.strip()
    if not base_prompt:
        base_prompt = "portrait photography"

    # Kick off first imagine with reference mode
    try:
        kwargs = {
            "prompt": base_prompt,
            "model_version": version,
            "aspect_ratio": aspect_ratio,
            "process_mode": process_mode,
        }
        if str(version).lower().startswith("7") or version == "v7":
            kwargs["oref"] = ref_url
            if ow is not None:
                kwargs["ow"] = ow
        else:
            kwargs["cref"] = ref_url
            if cw is not None:
                kwargs["cw"] = cw

        res = await imagine_tool.run(**kwargs)
        data = res.get("data", res)
        task_id = (data or {}).get("task_id") or (data or {}).get("id")
        if not task_id:
            raise RuntimeError("no_task_id_from_imagine")

        # Poll
        elapsed = 0.0
        final: dict[str, object] = {}
        while elapsed < poll_timeout:
            status = await get_task_tool.run(task_id=task_id)
            d = status.get("data", status) or {}
            if d.get("status") in {"completed", "finished"}:
                final = d
                break
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        if not final:
            raise RuntimeError("imagine_timeout")

        # Mirror
        output = (final or {}).get("output", {})
        image_url = output.get("image_url") or output.get("url")
        gcs_url = None
        if image_url:
            mirrored = await mirror_tool.run(source_url=image_url, task_id=task_id, filename="image.png")
            gcs_url = mirrored.get("gcs_url")
        results.append({"task_id": task_id, "image_url": image_url, "gcs_url": gcs_url})
    except Exception as e:
        errors.append(f"imagine_error:{e}")

    # Derive variations/upscales until count is reached
    idx = 1
    while len(results) < max(1, count) and idx < 100:
        try:
            base_task = results[-1]["task_id"]  # type: ignore[index]
            # Cycle through variation1..4, then reroll
            if (idx % 5) != 0:
                action = f"variation{(idx % 4) or 4}"
            else:
                action = "reroll"
            act_res = await action_tool.run(origin_task_id=str(base_task), action=action)
            d = act_res.get("data", act_res)
            new_task = (d or {}).get("task_id") or (d or {}).get("id")
            if not new_task:
                idx += 1
                continue

            # Poll new task
            elapsed = 0.0
            final2: dict[str, object] = {}
            while elapsed < poll_timeout:
                status2 = await get_task_tool.run(task_id=new_task)
                d2 = status2.get("data", status2) or {}
                if d2.get("status") in {"completed", "finished"}:
                    final2 = d2
                    break
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
            if not final2:
                idx += 1
                continue

            out2 = (final2 or {}).get("output", {})
            image2 = out2.get("image_url") or out2.get("url")
            gcs2 = None
            if image2:
                mirrored2 = await mirror_tool.run(source_url=image2, task_id=new_task, filename="image.png")
                gcs2 = mirrored2.get("gcs_url")
            results.append({"task_id": new_task, "image_url": image2, "gcs_url": gcs2})
        except Exception as e:
            errors.append(f"action_error:{e}")
        finally:
            idx += 1

    return {"images": results[:count], "errors": errors}

