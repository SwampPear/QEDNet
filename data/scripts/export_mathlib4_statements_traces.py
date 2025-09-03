"""
Export mathlib4 statements and traces.

Usage:
  uv run python data/scripts/export_mathlib4_statements_traces.py [options]

Description:
  - Ensures a LeanDojo traced repo exists (traces if missing, reuses if present).
  - Builds a unified "statements" list from:
      • Traced theorems/lemmas (via TracedRepo API)
      • Any declaration rows found in LeanDojo artifact JSON/JSONL files (defs, axioms, inductives, …)
  - Builds a "traces" list (tactic steps) for declarations that actually have traced proofs.
  - Writes a single JSON to data/exports/mathlib4/mathlib4_statements_traces.json.

Options:
  --repo URL       Git URL (default: https://github.com/leanprover-community/mathlib4)
  --commit HASH    Commit hash (default: latest on remote)
  --dst PATH       Traced repo directory (default: data/traces/mathlib4)
  --out PATH       Output JSON (default: data/exports/mathlib4/mathlib4_statements_traces.json)
  --test           Cap statements+traces to 10 items
  --limit N        Cap statements+traces to N items (overrides --test)
  --force          Delete --dst if it exists and retrace (DANGEROUS)

Requirements:
  • elan/lean on PATH
  • env var GITHUB_ACCESS_TOKEN set
"""

from __future__ import annotations
import argparse, json, os, sys, shutil
from pathlib import Path
from itertools import islice
from typing import Iterable

from lean_dojo.data_extraction.lean import LeanGitRepo, get_latest_commit
from lean_dojo.data_extraction.trace import trace
from lean_dojo.data_extraction.traced_data import TracedRepo

DEFAULT_REPO = "https://github.com/leanprover-community/mathlib4"

# ------------------------- helpers -------------------------

def limited(iterable: Iterable, limit: int | None):
  return islice(iterable, limit) if limit is not None else iterable

def detect_traced_root(dst: Path) -> Path:
  """LeanDojo may create a single subdir under dst; try to resolve that."""
  if not dst.exists():
    return dst
  subs = [p for p in dst.iterdir() if p.is_dir()]
  if len(subs) == 1:
    return subs[0]
  guess = dst / "mathlib4"
  return guess if guess.exists() else dst

def infer_mod_and_name(full: str) -> tuple[str, str]:
  parts = full.split(".")
  mod = ".".join(parts[:-1]) if len(parts) > 1 else ""
  name = parts[-1] if parts else full
  return mod, name

def load_jsonl(p: Path):
  out = []
  with p.open("r", encoding="utf-8") as f:
    for line in f:
      line = line.strip()
      if not line:
        continue
      try:
        out.append(json.loads(line))
      except Exception:
        out.append({"_raw": line})
  return out

def sweep_artifacts(traced_root: Path):
  """
  Collect any *.json/*.jsonl artifacts under traced_root.
  Return list of rows (dicts) that look like declarations.
  """
  rows = []

  def maybe_decl(obj):
    if not isinstance(obj, dict):
      return
    # Try common key variants LeanDojo/artifacts use
    full = obj.get("full_name") or obj.get("name") or obj.get("decl_name") or obj.get("constant")
    typ  = obj.get("type") or obj.get("ty") or obj.get("signature")
    kind = obj.get("kind") or obj.get("k") or obj.get("decl_kind") or obj.get("declType")
    if isinstance(full, str) and (typ is not None or kind is not None):
      rows.append({"full_name": full, "type": typ, "kind": kind})

  for p in traced_root.rglob("*"):
    if not p.is_file():
      continue
    suf = p.suffix.lower()
    try:
      if suf == ".json":
        payload = json.load(p.open("r", encoding="utf-8"))
        if isinstance(payload, list):
          for item in payload:
            maybe_decl(item)
        elif isinstance(payload, dict):
          # Common nested containers
          for key in ("decls", "constants", "items", "rows"):
            if key in payload and isinstance(payload[key], list):
              for item in payload[key]:
                maybe_decl(item)
          # Or single object
          maybe_decl(payload)
      elif suf == ".jsonl":
        for item in load_jsonl(p):
          maybe_decl(item)
    except Exception:
      # Ignore unreadable/mismatched artifacts
      continue

  return rows

def build_statement_record(full_name: str, typ: str | None, kind: str | None):
  mod, nm = infer_mod_and_name(full_name)
  # For consistency, we store the type/signature in "stmt" even for defs/axioms.
  return {
    "id": f"lean:{full_name}",
    "sys": "lean",
    "mod": mod,
    "name": nm,
    "kind": (kind or "const"),
    "stmt": typ,  # theorems: proposition; defs: type; axioms: proposition
  }

# ------------------------- main -------------------------

def main():
  ap = argparse.ArgumentParser(description="Export mathlib4 statements (all decl kinds) + traces.")
  ap.add_argument("--repo", default=DEFAULT_REPO)
  ap.add_argument("--commit", default=None)
  ap.add_argument("--dst", default="data/traces/mathlib4")
  ap.add_argument("--out", default="data/exports/mathlib4/mathlib4_statements_traces.json")
  ap.add_argument("--test", action="store_true", help="Cap outputs to 10 items")
  ap.add_argument("--limit", type=int, default=None, help="Cap outputs to N items (overrides --test)")
  ap.add_argument("--force", action="store_true", help="Delete --dst if it exists and retrace (DANGEROUS)")
  args = ap.parse_args()

  if not os.getenv("GITHUB_ACCESS_TOKEN"):
    print("ERROR: GITHUB_ACCESS_TOKEN must be set.", file=sys.stderr)
    sys.exit(2)

  # Prepare paths
  dst = Path(args.dst)
  dst.parent.mkdir(parents=True, exist_ok=True)

  out = Path(args.out)
  out.parent.mkdir(parents=True, exist_ok=True)

  # Resolve commit
  commit = args.commit or get_latest_commit(args.repo)
  repo = LeanGitRepo(args.repo, commit)

  # Ensure traced repo exists (don't pre-create dst; LeanDojo requires non-existing dir)
  if dst.exists():
    if args.force:
      print(f"[force] removing existing trace dir: {dst}")
      shutil.rmtree(dst)
    else:
      print(f"[reuse] traced repo exists at {dst}")
  if not dst.exists():
    print(f"[trace] repo={args.repo} commit={commit} -> {dst}")
    trace(repo, dst_dir=str(dst))

  traced_root = detect_traced_root(dst).resolve()
  print(f"[load] traced_root = {traced_root}")
  trepo = TracedRepo.load_from_disk(traced_root)

  # Limits
  limit = 10 if args.test else None
  if args.limit is not None:
    limit = max(0, args.limit)

  # ---------------- statements (union of traced theorems + artifact decls) ----------------
  statements: list[dict] = []
  seen_ids: set[str] = set()

  # A) from traced theorems/lemmas (high confidence, includes propositions)
  traced_theorems = list(trepo.get_traced_theorems())
  for th in limited(traced_theorems, limit):
    full = th.theorem.full_name
    # LeanDojo exposes the formal statement/proposition:
    stmt_txt = th.get_theorem_statement()
    rec = build_statement_record(full, stmt_txt, kind="thm")
    if rec["id"] not in seen_ids:
      statements.append(rec)
      seen_ids.add(rec["id"])

  # B) sweep artifacts to include ALL other decl kinds (defs, axioms, inductives, etc.)
  decl_rows = sweep_artifacts(traced_root)
  for row in decl_rows:
    full = row["full_name"]
    typ  = row.get("type")
    kind = row.get("kind")
    rec = build_statement_record(full, typ, kind)
    if rec["id"] not in seen_ids:
      statements.append(rec)
      seen_ids.add(rec["id"])

  # If a limit is set, trim the final statements to at most limit (useful for --test)
  if limit is not None:
    statements = statements[:limit]

  # ---------------- traces (for items that actually have proof traces) ----------------
  traces: list[dict] = []
  # Use a fresh iterator (or reuse list) and align with final statements set
  allowed_ids = {s["id"] for s in statements}
  count = 0
  for th in traced_theorems:
    full = th.theorem.full_name
    the_id = f"lean:{full}"
    if the_id not in allowed_ids:
      continue  # only include traces for statements we kept
    # Build step list
    steps = []
    i = 0
    try:
      for t in th.get_traced_tactics(atomic_only=False):
        try:
          tact_annot, prem = t.get_annotated_tactic()
        except Exception:
          tact_annot, prem = None, None
        steps.append({
          "i": i,
          "state_before": getattr(t, "state_before", None),
          "state_after": getattr(t, "state_after", None),
          "action": getattr(t, "tactic", None),
          "tactic_annotated": tact_annot,
          "premises": prem,
        })
        i += 1
    except Exception as e:
      steps.append({"_tactics_error": f"{type(e).__name__}: {e}"})

    traces.append({
      "theorem_id": the_id,
      "steps": steps
    })

    count += 1
    if limit is not None and count >= limit:
      break

  # ---------------- payload ----------------
  payload = {
    "statements": statements,
    "traces": traces,
    "meta": {
      "repo": args.repo,
      "repo_commit": commit,
      "traced_root": str(traced_root),
      "counts": {
        "statements": len(statements),
        "traces": len(traces)
      }
    }
  }

  with out.open("w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

  print(f"[done] wrote {out}")

if __name__ == "__main__":
  main()
