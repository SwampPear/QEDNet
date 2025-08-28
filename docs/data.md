# Lean Installation
## Install Lean toolchain 
curl -L https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | bash -s -- -y → source ~/.profile || source ~/.bashrc → elan toolchain install stable && elan default stable

## Clone mathlib4
cd repos && git clone https://github.com/leanprover-community/mathlib4 && cd mathlib4 && git rev-parse HEAD > ../../data/mathlib4.commit

## Build & pin deps
lake update && lake build (save output to ../../logs/lake_build.txt)

# Lake Build Proces
## Lakefile, DumpStatements, lean-prover
lake update
lake clean
lake build

# Statement Parsing
# Proof Trace Parsing

# 1) fetch deps (mathlib) and sync toolchain
lake update
# if you get a toolchain mismatch warning, do:
# cp .lake/packages/mathlib/lean-toolchain ./lean-toolchain
# elan toolchain install "$(cat lean-toolchain)"

# 2) build just enough mathlib for Mathlib.Data.Nat.Basic and your file
lake build

# 3) run the debug dumper (first 10 statements) to a sample file
lake exe qeddump > ~/qednet/data/sample_statements.json