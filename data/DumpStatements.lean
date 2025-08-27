-- DumpStatements.lean (fixed for v4.23.0-rc2)
import Lean
import Mathlib
open Lean Meta

/-- declaring module for a constant via the environment’s module index -/
def declModule (env : Environment) (n : Name) : Option String := do
  let mid ← env.getModuleIdxFor? n
  some (env.allImportedModuleNames.get! mid |>.toString)

/-- collect referenced constant names inside an expression (for dependency edges) -/
partial def collectConstNames (e : Expr) (acc : Std.HashSet Name := {}) : Std.HashSet Name :=
  match e with
  | .const n _   => acc.insert n
  | .app f a     => collectConstNames a (collectConstNames f acc)
  | .lam _ _ b _ => collectConstNames b acc
  | .forallE _ _ b _ => collectConstNames b acc
  | .letE _ _ b c _  => collectConstNames c (collectConstNames b acc)
  | .mdata _ b  => collectConstNames b acc
  | .proj _ _ b => collectConstNames b acc
  | _ => acc

def jStr (s : String) : Json := Json.str s
def row (id sys mod name kind stmt : String) (uses : Array String) : Json :=
  Json.obj
    [ ("id",   jStr id)
    , ("sys",  jStr sys)
    , ( "mod", jStr mod)
    , ("name", jStr name)
    , ("kind", jStr kind)
    , ("stmt", jStr stmt)
    , ("uses", Json.arr (uses.map jStr))  -- expect Array Json, not List
    ]

def dump : MetaM (Array Json) := do
  let env ← getEnv
  let mut out : Array Json := #[]
  for (n, ci) in env.constants.map₁.toList do
    if n.toString.startsWith "Mathlib." then
      if let .thmInfo ti := ci then
        let mod := (declModule env n).getD "Mathlib"
        let parts := n.toString.splitOn "."
        let lname := parts.getLastD ""    -- avoid reserved word `local`
        let stmt ← ppExpr ti.type
        let uses : Array String :=
          match ti.value? with
          | some v =>
              (collectConstNames v).toArray
              |>.map (·.toString)
              |>.filter (·.startsWith "Mathlib.")
          | none => #[]
        out := out.push (row s!"lean:{mod}.{lname}" "lean" mod lname "thm" stmt.pretty uses)
  return out

def main : IO Unit := do
  -- load mathlib
  let env ← importModules #[{module := `Mathlib}] {} 0
  -- pretty-printing options live in Core.Context in this Lean version
  let opts := ({} : Options) |>.setBool `pp.unicode true |>.setNat `pp.width 120
  let ctx  : Core.Context := { options := opts }
  let s0   : Core.State   := { env := env }
  let (rows, _s) ← (dump).toIO ctx s0
  let js := Json.obj [("ver", Json.num 1), ("statements", Json.arr rows)]
  IO.println js.compress
