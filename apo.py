#!/usr/bin/env python3
"""Standalone launcher for the bundled CLI without requiring package installation."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_project_orchestrator.cli import main

if __name__ == "__main__":
    main()
