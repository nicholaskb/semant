"""Midjourney agent tool registry.

This registry allows discovery of implemented tools without inspecting code.
"""

from typing import Dict, Callable

from .tools.imagine_tool import ImagineTool
from .tools.action_tool import ActionTool
from .tools.describe_tool import DescribeTool
from .tools.seed_tool import SeedTool
from .tools.blend_tool import BlendTool
from .tools.get_task_tool import GetTaskTool
from .tools.cancel_tool import CancelTool
from .tools.inpaint_tool import InpaintTool
from .tools.outpaint_tool import OutpaintTool
from .tools.pan_tool import PanTool
from .tools.zoom_tool import ZoomTool
from .tools.gcs_mirror_tool import GCSMirrorTool
from .tools.book_generator_tool import BookGeneratorTool


ToolFactory = Callable[[], object]

REGISTRY: Dict[str, ToolFactory] = {
	"mj.imagine": lambda: ImagineTool(),
	"mj.action": lambda: ActionTool(),
	"mj.describe": lambda: DescribeTool(),
	"mj.seed": lambda: SeedTool(),
	"mj.blend": lambda: BlendTool(),
	"mj.get_task": lambda: GetTaskTool(),
	"mj.cancel": lambda: CancelTool(),
	"mj.inpaint": lambda: InpaintTool(),
	"mj.outpaint": lambda: OutpaintTool(),
	"mj.pan": lambda: PanTool(),
	"mj.zoom": lambda: ZoomTool(),
	"mj.gcs_mirror": lambda: GCSMirrorTool(),
	"mj.book_generator": lambda: BookGeneratorTool(),
}

