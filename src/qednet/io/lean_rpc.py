# src/qednet/io/lean_rpc.py
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

_LEAN_TIMEOUT_SEC = 60


@dataclass
class LeanState:
    name: str
    pp_goal: str                  # pretty-printed goal (theorem type)
    pp_ctx: List[str]             # pretty-printed local context (empty in this MVP)
    hyp_graph_edges: List[Tuple[str, str]]  # MVP: empty; fill later from parser


@dataclass
class StepResult:
    valid: bool
    new_state: Optional[LeanState] = None
    error: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


class LeanRPC:
    """
    Minimal Lean runner used by QEDNet MVP.
    - fetch_goal(theorem_name): returns theorem type (as pp_goal).
    - check_tactic(goal_type, script): verifies a tactic script that proves `goal_type`.
    Notes:
      * This does NOT speak LSP/JSON-RPC. It shells out to Lean/Lake with temp files.
      * For Mathlib4 availability, we try `lake env lean` first (if inside a Lake project),
        else fallback to `lean` on PATH (must have mathlib precompiled in that toolchain).
    """

    def __init__(
        self,
        imports: Optional[List[str]] = None,
        extra_prelude: str = "",
        workdir: Optional[Path] = None,
        timeout_sec: int = _LEAN_TIMEOUT_SEC,
    ) -> None:
        self.imports = imports or ["Mathlib"]
        self.extra_prelude = extra_prelude
        self.workdir = Path(workdir) if workdir else None
        self.timeout_sec = timeout_sec
        self._lean_cmd = self._detect_lean_cmd()

    # ---------- Public API ----------

    def fetch_goal(self, theorem_name: str) -> LeanState:
        """
        Uses `#check <name>` to retrieve the theorem's type.
        Returns LeanState with pp_goal set to the type; ctx/graph empty in MVP.
        """
        src = self._preamble() + f"\n#check {theorem_name}\n"
        ok, out, err = self._run_lean(src, label=f"check_{theorem_name}")

        if not ok:
            raise RuntimeError(f"Lean failed while fetching goal for '{theorem_name}':\n{err or out}")

        # Lean prints lines like: "<name> : <type>"
        # We find the last occurrence to be robust if Lean echoes imports etc.
        m = None
        for line in (out or "").splitlines()[::-1]:
            # Accept variants with namespace prefixes or unicode; we anchor on " : "
            if " : " in line:
                left, right = line.split(" : ", 1)
                # Lean may print fully qualified name; tolerate it
                if left.strip().endswith(theorem_name) or theorem_name in left:
                    m = (left.strip(), right.strip())
                    break
        if not m:
            # fallback: first " : " line
            for line in (out or "").splitlines():
                if " : " in line:
                    m = ("<unknown>", line.split(" : ", 1)[1].strip())
                    break

        if not m:
            raise ValueError(f"Could not parse theorem type from Lean output:\n{out}")

        _, ty = m
        return LeanState(
            name=theorem_name,
            pp_goal=ty,
            pp_ctx=[],
            hyp_graph_edges=[],
        )

    def check_tactic(self, goal_type: str, tactic_script: str, theorem_name: str = "__tmp") -> StepResult:
        """
        Compiles a small Lean file:
            theorem __tmp : <goal_type> := by
              <tactic_script>
        Returns StepResult(valid=...) and raw stdout/stderr for debugging.
        """
        body = self._preamble() + "\n"
        body += "set_option maxRecDepth 10000\n"
        body += "set_option maxHeartbeats 200000\n\n"
        # Normalize script indentation and ensure it's on new lines
        script = self._dedent(tactic_script).rstrip() + "\n"
        body += f"theorem {theorem_name} : {goal_type} := by\n"
        body += self._indent(script, n=2)

        ok, out, err = self._run_lean(body, label=f"prove_{theorem_name}")

        if ok:
            # On success, we don’t yet have the next-state decomposition; return the same goal.
            return StepResult(
                valid=True,
                new_state=LeanState(name=theorem_name, pp_goal=goal_type, pp_ctx=[], hyp_graph_edges=[]),
                stdout=out,
                stderr=err,
            )
        else:
            # Extract a concise first error line for convenience.
            concise = self._first_lean_error(err or out)
            return StepResult(valid=False, error=concise, stdout=out, stderr=err)

    # ---------- Internals ----------

    def _preamble(self) -> str:
        imps = "\n".join(f"import {m}" for m in self.imports)
        return f"{imps}\n{self.extra_prelude}".rstrip() + "\n"

    def _detect_lean_cmd(self) -> List[str]:
        """
        Prefer running Lean through `lake env` when available (ensures the proper toolchain & deps),
        otherwise fall back to plain `lean`. We only need `--stdin`-less execution (compile file).
        """
        lake = shutil.which("lake")
        if lake:
            # We will invoke: lake env lean <file>
            return [lake, "env", "lean"]
        lean = shutil.which("lean")
        if lean:
            return [lean]
        raise EnvironmentError("Neither `lake` nor `lean` was found on PATH. Install Lean 4 / Mathlib toolchain.")

    def _run_lean(self, lean_source: str, label: str = "tmp") -> Tuple[bool, str, str]:
        """
        Writes `lean_source` to a temporary .lean file and runs Lean compiler on it.
        Returns (ok, stdout, stderr).
        """
        tmpdir_ctx = tempfile.TemporaryDirectory(prefix="qednet_lean_")
        tmpdir = Path(tmpdir_ctx.name)

        # Heuristic: if using plain `lean`, ensure a .lean-toolchain exists from elan if present
        toolchain_file = Path(".lean-toolchain")
        if not toolchain_file.exists():
            # Not required, but warn in output if mathlib cannot be resolved.
            pass

        src_path = tmpdir / f"{label}.lean"
        src_path.write_text(lean_source, encoding="utf-8")

        cmd = [*self._lean_cmd, str(src_path)]
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.workdir) if self.workdir else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout_sec,
                check=False,
                text=True,
            )
        except subprocess.TimeoutExpired as te:
            tmpdir_ctx.cleanup()
            return False, "", f"Lean timed out after {self.timeout_sec}s running {cmd}: {te}"
        except Exception as e:
            tmpdir_ctx.cleanup()
            return False, "", f"Failed to run Lean: {e}"

        out = proc.stdout or ""
        err = proc.stderr or ""
        ok = proc.returncode == 0

        tmpdir_ctx.cleanup()
        return ok, out, err

    @staticmethod
    def _dedent(s: str) -> str:
        # Simple dedent without importing textwrap to keep deps tiny.
        lines = s.splitlines()
        # compute min leading spaces on non-empty lines
        mins = [len(re.match(r"^[ \t]*", ln).group(0)) for ln in lines if ln.strip()]
        if not mins:
            return s
        cut = min(mins)
        return "\n".join(ln[cut:] if len(ln) >= cut else ln for ln in lines)

    @staticmethod
    def _indent(s: str, n: int = 2) -> str:
        pad = " " * n
        return "\n".join((pad + ln if ln.strip() else ln) for ln in s.splitlines()) + ("\n" if s and not s.endswith("\n") else "")

    @staticmethod
    def _first_lean_error(stream: str) -> str:
        if not stream:
            return ""
        # Grab first line that looks like an error location or message.
        for ln in stream.splitlines():
            if "error:" in ln or re.search(r":\d+:\d+: error:", ln):
                return ln.strip()
        # Fallback to first non-empty line.
        for ln in stream.splitlines():
            if ln.strip():
                return ln.strip()
        return stream.strip()
