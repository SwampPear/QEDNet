# QEDNet
QEDNet is a machine learning model designed to learn and generate verifiable mathematical proofs. It integrates 
large-scale language models with formal verification systems, reinforcement learning, and symbolic reasoning. The
ultimate goal of QEDNet is to serve as a scalable, general-purpose mathematical reasoning engine, capable of advancing
formal theorem proving, education, and research automation.

## Key Features
- modular verifier-in-the-loop architecture
- neural + symbolic hybrid reasoning  
- proof DAG with GNN structural encoding 
- replay-buffer reinforcement learning  
- neural verifier/critic for efficient candidate selection
- store (goal, action, outcome, proof-sketch) and sample by “learning progress” so you don’t overfit the easy wins

# Overview
QEDNet is a modular, verifier-in-the-loop system with the following core components:

## Hierarchical Planner
- large MoE Transformer used to decompose problems into a proof sketch of goals, lemmas, and cases
- a clean encoder that turns Lean goals/ctx into tokens the MoE really understands (pretty-print + symbols + small graph 
of hypotheses)

## Neural Proof Policy + Value Head
- proposes next tactic/lemma and operates on formal proof states
- esitmates distance to proof
- augmented by a premise retriever over mathlib4, indexed with symbolic + neural embeddings (RAG for theorems and tactics)

## Proof DAG Representation
- encodes proof states as tokens and a dependency DAG
- enables structural reasoning, not just text-based reasoning

## Search Controller
- runs best-first / MCTS search over proof states
- learns from self-play to decide which candidate branches to explore

## Formal Checker
- validates each step immediately, closing the loop
- successful proof traces feed a replay buffer for continual training

## Output
- structured as tactics or lemmas

# More Features
## Curriculum Switches
- start with medium proofs, then inject perturbed goals and solver hints; periodically mine “hard negatives” that fooled 
the verifier
