-- DumpStatementsDebug.lean  (dumps only the first 10 statements from a tiny module)
import Lean
import Mathlib.Data.Nat.Basic   -- small slice of mathlib to keep initial build light
open Lean Meta

/-- declaring module via environment’s module index (provenance) -/
def declModule (env : Environment) (n : Name) : Option String := do
  let mid ← env.getModuleIdxFor? n
  some (env.allImportedModuleNames.get! mid |>.toString)

/-- collect referenced constants in a proof term (for dependency edges) -/
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

/-- dump only the first `limit` theorems from the imported slice -/
def dumpSome (limit : Nat) : MetaM (Array Json) := do
  let env ← getEnv
  let mut out : Array Json := #[]
  let mut count := 0
  for (n, ci) in env.constants.map₁.toList do
    if count >= limit then
      break
    -- keep only declarations that belong to our tiny module
    if let some m := declModule env n then
      if m == "Mathlib.Data.Nat.Basic" then
        if let .thmInfo ti := ci then
          let lname := (n.toString.splitOn ".").getLastD ""
          let stmtFmt ← ppExpr ti.type
          let uses : Array String :=
            (collectConstNames ti.value).toArray
              |>.map (·.toString)
              |>.filter (·.startsWith "Mathlib.")
          out := out.push (row s!"lean:{m}.{lname}" "lean" m lname "thm" stmtFmt.pretty uses)
          count := count + 1
  return out

/-- main: import a tiny mathlib module, dump first 10 theorems as pretty JSON -/
def main : IO Unit := do
  -- Only pull a small slice to minimize initial build
  let env ← importModules #[{ module := `Mathlib.Data.Nat.Basic }] {} 0

  -- pretty-print options (Core.Context wants fileName/fileMap here)
  let opts : Options := (Options.empty).setBool `pp.unicode true |>.setNat `pp.width 120
  let ctx  : Core.Context := { options := opts, fileName := "<DumpStatementsDebug>", fileMap := default }
  let s0   : Core.State   := { env := env }

  let (rows, _) ← (dumpSome 10).toIO ctx s0
  let js := Json.mkObj [("ver", Json.num 1), ("statements", Json.arr rows)]
  IO.println js.pretty
