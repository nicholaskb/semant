import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from semant.workflows.childrens_book.orchestrator import ChildrensBookOrchestrator


class StubKGManager:
    async def initialize(self):
        return None

    async def shutdown(self):
        return None

    async def query_graph(self, query):
        return []


@pytest.mark.asyncio
async def test_generate_book_smoke(monkeypatch, tmp_path):
    """Ensure the orchestrator can run when core steps succeed."""
    kg_manager = StubKGManager()
    orchestrator = ChildrensBookOrchestrator(
        bucket_name="demo",
        input_prefix="input/",
        output_prefix="output/",
        kg_manager=kg_manager,
        max_concurrent_downloads=2,
    )
    orchestrator.output_dir = tmp_path

    ingestion_result = {
        "status": "success",
        "total_images": 4,
        "successful": 4,
        "input_images_count": 2,
        "output_images_count": 2,
    }
    pairing_result = {
        "status": "success",
        "pairs": [
            {
                "pair_uri": "urn:pair:1",
                "input_image_uri": "gs://demo/input.png",
                "output_image_uris": ["gs://demo/out1.png", "gs://demo/out2.png"],
            }
        ],
        "pairs_count": 1,
    }

    monkeypatch.setattr(
        orchestrator, "_run_ingestion", AsyncMock(return_value=ingestion_result)
    )
    monkeypatch.setattr(
        orchestrator, "_run_pairing", AsyncMock(return_value=pairing_result)
    )
    monkeypatch.setattr(
        orchestrator,
        "_analyze_images",
        AsyncMock(return_value={"analyses": [{"input_image_uri": "gs://demo/input.png"}]}),
    )
    monkeypatch.setattr(
        orchestrator,
        "_arrange_by_color",
        AsyncMock(
            return_value={
                "arrangements": [
                    {
                        "pair_uri": "urn:pair:1",
                        "color_harmony_score": 0.8,
                    }
                ]
            }
        ),
    )
    monkeypatch.setattr(
        orchestrator,
        "_design_layouts",
        AsyncMock(
            return_value={
                "layouts": [
                    {
                        "page_number": 1,
                        "pair_uri": "urn:pair:1",
                        "grid_dimensions": "2x2",
                        "num_images": 2,
                        "visual_balance_score": 0.9,
                        "color_harmony_score": 0.8,
                    }
                ]
            }
        ),
    )
    monkeypatch.setattr(
        orchestrator,
        "_generate_story",
        AsyncMock(return_value={"pages": [{"page_number": 1, "text": "Demo"}]}),
    )
    monkeypatch.setattr(
        orchestrator,
        "_review_quality",
        AsyncMock(return_value={"reviews": [{"page_number": 1, "approved": True}]}),
    )
    html_path = tmp_path / "book.html"
    html_path.write_text("<html></html>")
    monkeypatch.setattr(
        orchestrator,
        "_generate_html_pdf",
        AsyncMock(
            return_value={
                "html_path": str(html_path),
                "pdf_path": None,
                "num_pages": 1,
            }
        ),
    )

    result = await orchestrator.generate_book()

    assert result["pairing"]["pairs_count"] == 1
    assert orchestrator.metrics["step_success"]["ingestion"] is True
    assert orchestrator.metrics["pairs_created"] == 1

