from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import List

import pytest

# --- Ensure `src/` is on sys.path so `from qednet...` works without installing ---
ROOT = Path(__file__).resolve().parents[1]  # repo root
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# --- Optional: try to read imports from configs/default.yaml (no hard dep on pyyaml) ---
def _default_imports() -> List[str]:
    # ENV has priority: QEDNET_IMPORTS="Mathlib,Std,Init"
    env = os.getenv("QEDNET_IMPORTS")
    if env:
        return [s.strip() for s in env.split(",") if s.strip()]

    cfg_path = ROOT / "configs" / "default.yaml"
    if cfg_path.exists():
        try:
            import yaml  # type: ignore
            data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            imps = data.get("imports")
            if isinstance(imps, list) and all(isinstance(x, str) for x in imps):
                return imps  # e.g., ["Mathlib"]
        except Exception:
            pass
    return ["Mathlib"]

def _lean_available() -> bool:
    return bool(shutil.which("lake") or shutil.which("lean"))

def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "lean: tests that require Lean/Mathlib toolchain")

@pytest.fixture(scope="session")
def lean_installed() -> None:
    """Skip Lean-dependent tests cleanly if Lean/Lake aren't on PATH."""
    if not _lean_available():
        pytest.skip("Lean/Lake not found on PATH; skipping Lean integration tests.", allow_module_level=True)

@pytest.fixture(scope="session")
def leanrpc(lean_installed):
    """Session-scoped LeanRPC ready to use in tests."""
    from qednet.io.lean_rpc import LeanRPC

    timeout = int(os.getenv("QEDNET_LEAN_TIMEOUT", "60"))
    imports = _default_imports()
    # If you run tests inside a Lake project, LeanRPC will prefer `lake env lean`
    return LeanRPC(imports=imports, timeout_sec=timeout)
