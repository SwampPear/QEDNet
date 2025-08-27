# Hierarchical Planner
  - large MoE Transformer
  - decompose problems into a proof sketch (goals, lemmas, cases)

# Neural Proof Policy + Value Head
  - operates on formal proof states (Lean context, local goals, hypotheses)
  - proposes the next tactic/lemma  
  - estimates distance-to-proof  
  - Augmented by a **premise retriever** over mathlib/stdlib, indexed with symbolic + neural embeddings (RAG for 
  theorems and tactics).  

# Proof DAG Representation
  - Encodes proof states as tokens and a **dependency DAG** (GNN over hypotheses/lemmas)  
  - Enables structural reasoning, not just text-based reasoning

# Search Controller
  - runs best-first / MCTS search over proof states  
  - learns from self-play to decide which candidate branches to explore

# Formal Checker
  - validates each step immediately 
  - successful proof traces feed a replay buffer for continual training

# Output
  - structured as tactics or lemmas



# new stuff:

Neural verifier/critic in the loop (not just after the fact): score/rerank candidate steps before the checker burns time; train it on success + near-misses.

State bridge: a clean encoder that turns Lean goals/ctx into tokens the MoE really understands (pretty-print + symbols + small graph of hypotheses).

Premise diversity: two retrievers (lexical + neural) with jitter (drop/add lemmas) so search doesn’t tunnel.

Speculative search: cheap policy expands several beams; the checker prunes; the value head steers—cache successes to a transposition table so you don’t re-prove the same subgoal.

Lemma synthesis: let the planner mint tiny sub-lemmas and try to prove them; successful ones go to a local scratchpad index for reuse within the run.

Replay with priorities: store (goal, action, outcome, proof-sketch) and sample by “learning progress” so you don’t overfit the easy wins.

Curriculum switches: start with medium proofs, then inject perturbed goals and solver hints; periodically mine “hard negatives” that fooled the verifier.




lean is user-assisted (agent-assisted)