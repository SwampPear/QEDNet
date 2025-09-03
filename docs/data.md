# Lean Installation
## Install Lean toolchain 
curl -L https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | bash -s -- -y → source ~/.profile || source ~/.bashrc → elan toolchain install stable && elan default stable

## Run Statement Script
- parses mathlib4 repo traces
- takes a while but will be cached with lean-dojo