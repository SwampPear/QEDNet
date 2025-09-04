qednet/
├─ src/
│  └─ qednet/
│     ├─ __init__.py
│     ├─ io/
│     │  ├─ __init__.py
│     │  └─ lean_rpc.py          # fetch_goal, check_tactic
│     ├─ encoders/
│     │  ├─ __init__.py
│     │  └─ bridge.py            # state → tokens + pyg graph
│     ├─ models/
│     │  ├─ __init__.py
│     │  ├─ policy_value.py      # tiny Transformer + value head
│     │  └─ retriever.py         # BM25 stub (swap dense later)
│     ├─ dag/
│     │  ├─ __init__.py
│     │  └─ store.py             # nodes/edges/frontier
│     ├─ search/
│     │  ├─ __init__.py
│     │  ├─ tactics.py           # ~30 safe tactics list
│     │  └─ mcts.py              # best-first/MCTS expansion loop
│     ├─ train/
│     │  ├─ __init__.py
│     │  ├─ replay.py            # prioritized buffer
│     │  └─ loop.py              # Lightning/torch train harness
│     ├─ curriculum/
│     │  ├─ __init__.py
│     │  └─ switches.py          # difficulty schedule
│     └─ cli/
│        ├─ __init__.py
│        └─ run_prove.py         # `prove(theorem_name)`
├─ tests/
│  ├─ conftest.py
│  ├─ test_lean_rpc.py
│  ├─ test_encoder.py
│  ├─ test_search_loop.py
│  └─ fixtures/
│     ├─ tiny_goal.lean
│     └─ tiny_trace.jsonl
└─ notebooks/
   └─ 00_quickstart.ipynb
