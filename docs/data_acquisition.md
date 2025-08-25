Create workspace: mkdir -p ~/qednet/{repos,data,logs,scripts} && cd ~/qednet


# Install Lean toolchain 
curl -L https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | bash -s -- -y → source ~/.profile || source ~/.bashrc → elan toolchain install stable && elan default stable

# Clone mathlib4
cd repos && git clone https://github.com/leanprover-community/mathlib4 && cd mathlib4 && git rev-parse HEAD > ../../data/mathlib4.commit

# Build & pin deps
lake update && lake build (save output to ../../logs/lake_build.txt)

# Make file allowlist and filters

Allow: Mathlib/**/*.lean

Exclude: _archive/, Tactic/, any file containing #print axioms or sorry (later step will re-check).

Write a fast harvester script (e.g., scripts/harvest_mathlib.py) that for each allowed .lean file emits JSONL rows with fields:

id (module.name), name, kind (theorem|lemma|def? but keep only theorem/lemma), statement (type), module, src_path, line_span, imports, namespaces, attrs, has_sorry (bool).
Minimal regex to catch heads like ^(theorem|lemma)\s+([A-Za-z0-9_'.]+)\s*:(.*?)(?==\s*by|:=|where|$); capture until first :=/by.

Also parse per-file import lines (^import\s+([A-Za-z0-9\.\s]+)) and namespace … / open … blocks to fill imports/namespaces.

Skip any item where has_sorry is true (detect \bsorry\b between declaration start and next theorem|lemma|end or file end).

Run the harvester:

python3 scripts/harvest_mathlib.py repos/mathlib4/Mathlib > data/lean/mathlib4.v0.jsonl 2> logs/harvest_v0.err

Validate the corpus quickly:

Count rows: wc -l data/lean/mathlib4.v0.jsonl

Sample 5: jq -c '.[0:5]' data/lean/mathlib4.v0.jsonl or shuf -n5 data/lean/mathlib4.v0.jsonl

Ensure no empty statement and kind ∈ {theorem, lemma}.

Record manifest for reproducibility: create data/manifest.yaml with: Lean/elan versions (elan --version, lean --version), lake --version, mathlib4 commit (from step 3), harvester script checksum (shasum scripts/harvest_mathlib.py), and timestamp.

Split train/val/test by module (to reduce leakage):

python3 - <<'PY'\nimport json,random,hashlib\nrandom.seed(0)\nmods={}\nfor ln in open('data/lean/mathlib4.v0.jsonl'): \n d=json.loads(ln); mods.setdefault(d['module'],[]).append(d)\nkeys=list(mods); random.shuffle(keys)\nN=len(keys); tr=keys[:int(.9*N)]; va=keys[int(.9*N):int(.95*N)]; te=keys[int(.95*N):]\nfor name,ks in [('train','tr'),('val','va'),('test','te')]: pass\nout={'train':tr,'val':va,'test':te}\nfor split,ks in out.items():\n f=open(f'data/lean/mathlib4.{split}.jsonl','w')\n for m in ks:\n for d in mods[m]: f.write(json.dumps(d)+'\\n')\nPY

Sanity counts: for s in train val test; do echo $s $(wc -l data/lean/mathlib4.$s.jsonl); done

Snapshot everything: git init && echo "data/*.jsonl\nlogs/*" > .gitignore && git add scripts data/manifest.yaml .gitignore && git commit -m "QEDNet seed corpus v0 (mathlib4 index)"

If you want, I can drop in the exact harvest_mathlib.py (tight regex + file walkers) next.