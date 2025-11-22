"""
Compatibility shim for legacy imports.

`main.py` expects `MainAgent` to live at the project root, but the active
implementation was moved under `scripts/tools`.  This module re-exports the
class so uvicorn can start without modifying downstream imports.
"""

from scripts.tools.main_agent import MainAgent  # noqa: F401

__all__ = ["MainAgent"]

