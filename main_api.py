# 2035-07-11 Consolidation – compatibility shim for legacy imports
"""This file remains to keep `from main_api import app` working in tests and user code.
All FastAPI logic now lives in `main.py`.
"""

from main import app  # re-export unified FastAPI `app`  # noqa: F401 