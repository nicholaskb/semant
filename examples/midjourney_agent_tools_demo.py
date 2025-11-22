import os
import asyncio
import json


async def main():
    # Ensure token is present (demo uses mocked HTTP)
    os.environ.setdefault("MIDJOURNEY_API_TOKEN", "demo-token")

    # Mock httpx.AsyncClient used by the GoAPI client
    import httpx

    class DummyResponse:
        def __init__(self, status_code: int, json_data):
            self.status_code = status_code
            self._json_data = json_data
            self.text = json.dumps(json_data)

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP error {self.status_code}")

        def json(self):
            return self._json_data

    async def dummy_post(url, headers=None, **kwargs):
        payload = kwargs.get("json", {})
        task_type = payload.get("task_type")
        if task_type == "imagine":
            return DummyResponse(200, {"data": {"task_id": "demo123", "output": {"image_url": "https://demo/image.png"}}})
        elif task_type in {"blend", "seed", "inpaint", "outpaint", "pan", "zoom", "cancel", "reroll", "upscale", "variation"}:
            return DummyResponse(200, {"data": {"task_id": f"{task_type}-ok"}})
        return DummyResponse(200, {"status": "ok"})

    async def dummy_get(url, headers=None, **kwargs):
        # Simulate a completed task fetch
        return DummyResponse(200, {"data": {"id": url.rsplit("/", 1)[-1], "status": "completed"}})

    class DummyClient:
        def __init__(self, timeout=None):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, **kwargs):
            return await dummy_post(url, headers=headers, **kwargs)

        async def get(self, url, headers=None, **kwargs):
            return await dummy_get(url, headers=headers, **kwargs)

    # Patch httpx.AsyncClient to avoid real network calls
    httpx.AsyncClient = DummyClient  # type: ignore

    # Use the registry to get tools
    from semant.agent_tools.midjourney import REGISTRY

    imagine = REGISTRY["mj.imagine"]()
    result_imagine = await imagine.run(prompt="A demo castle at sunset", model_version="v7", oref="https://ref", ow=5)
    print("Imagine result:", json.dumps(result_imagine))

    get_task = REGISTRY["mj.get_task"]()
    result_status = await get_task.run(task_id="demo123")
    print("Get task status:", json.dumps(result_status))


if __name__ == "__main__":
    asyncio.run(main())


