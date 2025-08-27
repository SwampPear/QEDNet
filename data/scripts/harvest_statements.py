#!/usr/bin/env python3
import subprocess, json
from pathlib import Path

ROOT = Path.home() / 'qednet'
PROJ = ROOT / 'qeddump'          # tiny Lake project
OUT  = ROOT / 'data' / 'statements.json'
PROJ.mkdir(parents=True, exist_ok=True)
( ROOT / 'data').mkdir(parents=True, exist_ok=True)

lakefile = r'''
import Lake
open Lake DSL

package qeddump

-- Pull mathlib4 as a dependency (you can pin a commit instead of "master")
require mathlib from git
  "https://github.com/leanprover-community/mathlib4" @ "master"

@[default_target]
lean_exe qeddump where
  root := `DumpStatements
'''
dump_lean = r'''
import Lean
import Mathlib

open Lean Meta

namespace QEDDump

def splitModName (n : Name) : (String × String) :=
  let s := n.toString
  match s.rev.findIdx? (· == '.') with
  | some i =>
      let j := s.length - i - 1
      (s.extract 0 j, s.extract (j+1) s.length)
  | none => ("", s)

def isMathlibConst (n : Name) : Bool :=
  n.toString.startsWith "Mathlib."

def jStr (s : String) : Json := Json.str s
def stmtEntry (sys mod name kind stmt : String) : Json :=
  Json.obj
    [ ("id",   jStr s!"{sys}:{mod}.{name}")
    , ("sys",  jStr sys)
    , ("mod",  jStr mod)
    , ("name", jStr name)
    , ("kind", jStr kind)
    , ("stmt", jStr stmt)
    ]

def collectStatements : MetaM (Array Json) := do
  let env ← getEnv
  let consts := env.constants.map₁.toList
  let mut out : Array Json := #[]
  for (n, ci) in consts do
    if isMathlibConst n then
      match ci with
      | .thmInfo ti =>
          let (mod, name) := splitModName n
          let fmt ← ppExpr ti.type
          let stmt := fmt.pretty
          out := out.push (stmtEntry "lean" mod name "thm" stmt)
      | _ => pure ()
  return out

def main : IO Unit := do
  let ppOpts := ({} : Options)
    |>.setBool `pp.unicode true
    |>.setNat  `pp.width  120
  let env ← importModules #[{module := `Mathlib}] {} 0
  let (_, arr) ← (collectStatements).toIO ppOpts { env := env }
  let json := Json.obj [("ver", Json.num 1), ("statements", Json.arr arr.toList)]
  IO.println json.compress

end QEDDump

open QEDDump in
#eval main
'''
(PROJ / 'lakefile.lean').write_text(lakefile, encoding='utf-8')
(PROJ / 'DumpStatements.lean').write_text(dump_lean, encoding='utf-8')

def run(cmd, cwd=None):
  r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
  if r.returncode != 0:
    raise SystemExit(f"cmd failed: {' '.join(cmd)}\n--- STDOUT ---\n{r.stdout}\n--- STDERR ---\n{r.stderr}")
  return r.stdout

print('[1/3] lake update (fetch mathlib)…')
run(['lake','update'], cwd=PROJ)

print('[2/3] lake build (compile)…')
run(['lake','build'], cwd=PROJ)

print('[3/3] lake exe qeddump (dump)…')
out = run(['lake','exe','qeddump'], cwd=PROJ)

OUT.write_text(json.dumps(json.loads(out), ensure_ascii=False, indent=2), encoding='utf-8')
print(f'[ok] wrote statements → {OUT}')
