-- DumpStatements.lean — parse ALL mathlib theorems into JSON
-- Compatible with leanprover/lean4:v4.23.0-rc2

import Lean
import Mathlib
open Lean Meta

/-- declaring module via the environment’s module index (provenance) -/
def declModule (env : Environment) (n : Name) : Option String := do
  let mid ← env.getModuleIdxFor? n
  some (env.allImportedModuleNames[mid]! |>.toString)

/-- gather referenced constants inside a proof term (for dependency edges) -/
partial def collectConstNames (e : Expr) (acc : Std.HashSet Name := {}) : Std.HashSet Name :=
  match e with
  | .const n _      => acc.insert n
  | .app f a        => collectConstNames a (collectConstNames f acc)
  | .lam _ _ b _    => collectConstNames b acc
  | .forallE _ _ b _=> collectConstNames b acc
  | .letE _ v b c _ => collectConstNames c (collectConstNames b (collectConstNames v acc))
  | .mdata _ b      => collectConstNames b acc
  | .proj _ _ b     => collectConstNames b acc
  | _               => acc

def jStr (s : String) : Json := Json.str s

/-- one JSON row for a theorem -/
def row (id sys mod name kind stmt : String) (uses : Array String) : Json :=
  Json.mkObj
    [ ("id",   jStr id)
    , ("sys",  jStr sys)
    , ("mod",  jStr mod)
    , ("name", jStr name)
    , ("kind", jStr kind)
    , ("stmt", jStr stmt)
    , ("uses", Json.arr (uses.map jStr))
    ]

/-- dump ALL mathlib theorems (kernel truth, no regex) -/
def dumpAll : MetaM (Array Json) := do
  let env ← getEnv
  let mut out : Array Json := #[]
  for (n, ci) in env.constants.map₁.toList do
    if n.toString.startsWith "Mathlib." then
      if let .thmInfo ti := ci then
        let some mod := declModule env n
          | continue
        let lname := (n.toString.splitOn ".").getLastD ""
        let stmtFmt ← ppExpr ti.type
        -- proof-term dependencies (restrict to Mathlib.* for cleanliness)
        let uses : Array String :=
          (collectConstNames ti.value).toArray
            |>.map (·.toString)
            |>.filter (·.startsWith "Mathlib.")
        out := out.push (row s!"lean:{mod}.{lname}" "lean" mod lname "thm" stmtFmt.pretty uses)
  return out

/-- main: import Mathlib, run dumper, print compact JSON to stdout -/
def main : IO Unit := do
  -- load full mathlib into an environment
  let env ← importModules #[{ module := `Mathlib }] {} 0
  -- pretty-print options (rc2 needs a full Core.Context with file fields)
  let opts : Options := (Options.empty).setBool `pp.unicode true |>.setNat `pp.width 120
  let ctx  : Core.Context := { options := opts, fileName := "<DumpStatements>", fileMap := default }
  let s0   : Core.State   := { env := env }
  let (rows, _) ← (dumpAll).toIO ctx s0
  let js := Json.mkObj [("ver", Json.num 1), ("statements", Json.arr rows)]
  IO.println js.compress
