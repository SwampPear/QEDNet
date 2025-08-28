import Lake
open Lake DSL

package qeddump

-- Optionally replace "master" with a specific commit SHA for reproducibility.
require mathlib from git
  "https://github.com/leanprover-community/mathlib4" @ "master"

@[default_target]
lean_exe qeddump where
  root := `DumpStatements
