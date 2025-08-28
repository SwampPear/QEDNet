-- lakefile.lean
import Lake
open Lake DSL

package qeddump

-- Use your local mathlib clone via a file:// git URL.
-- Adjust the absolute path if yours differs.
require mathlib from git
  "file:///Users/michaelvaden/Desktop/development/qednet/data/raw/mathlib4" @ "master"

@[default_target]
lean_exe qeddump where
  root := `DumpStatements
