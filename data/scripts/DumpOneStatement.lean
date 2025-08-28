-- DumpOneStatement.lean  (leanprover/lean4:v4.23.0-rc2)
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
  Json.mkObj
    [ ("id",   jStr id)
    , ("sys",  jStr sys)
    , ("mod",  jStr mod)
    , ("name", jStr name)
    , ("kind", jStr kind)
    , ("stmt", jStr stmt)
    , ("uses", Json.arr (uses.map jStr))
    ]

/-- dump exactly one theorem from a specific module (fast sanity check) -/
def dumpOne (targetMod : String) : MetaM (Option Json) := do
  let env ← getEnv
  for (n, ci) in env.constants.map₁.toList do
    if let some m := declModule env n then
      if m == targetMod then
        if let .thmInfo ti := ci then
          let parts := n.toString.splitOn "."
          let lname := parts.getLastD ""
          let stmtFmt ← ppExpr ti.type
          let uses : Array String :=
            (collectConstNames ti.value).toArray
              |>.map (·.toString)
              |>.filter (·.startsWith "Mathlib.")
          let r := row s!"lean:{m}.{lname}" "lean" m lname "thm" stmtFmt.pretty uses
          return some r
  return none

def main : IO Unit := do
  /- pick a small slice of mathlib so we don’t build the world first time.
     You can swap this for another tiny module like:
       `Mathlib.Algebra.Group.Defs`
       `Mathlib.Data.Int.Basic`
  -/
  let targetModName := "Mathlib.Data.Nat.Basic"
  let env ← importModules #[{ module := `Mathlib.Data.Nat.Basic }] {} 0

  -- options/context (rc2 wants full Core.Context)
  let opts₀ : Options := Options.empty
  let opts₁ := opts₀.setBool `pp.unicode true
  let opts  := opts₁.setNat  `pp.width 120
  let ctx  : Core.Context := { options := opts, fileName := "<DumpOne>", fileMap := default }
  let s0   : Core.State   := { env := env }

  let (res?, _) ← (dumpOne targetModName).toIO ctx s0
  let js :=
    match res? with
    | some r => Json.mkObj [("ver", Json.num 1), ("statements", Json.arr #[r])]
    | none   => Json.mkObj [("ver", Json.num 1), ("statements", Json.arr #[])]
  IO.println js.compress
