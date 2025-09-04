# QEDNet
QEDNet is a machine learning model designed to learn and generate verifiable mathematical proofs. It integrates 
large-scale language models with formal verification systems, reinforcement learning, and symbolic reasoning. The
ultimate goal of QEDNet is to serve as a scalable, general-purpose mathematical reasoning engine, capable of advancing
formal theorem proving, education, and research automation.

## Key Features
- Modular verifier-in-the-loop architecture
- Neural + symbolic hybrid reasoning  
- Proof DAG with GNN structural encoding  
- External solver integration (CAS, SMT, LP solvers)  
- Replay-buffer reinforcement learning  
- Neural verifier/critic for efficient candidate selection  

## Overview
QEDNet is a modular, verifier-in-the-loop system with the following core components:

### Hierarchical Planner
  - Uses a large MoE Transformer to decompose problems into a proof sketch (goals, lemmas, cases).  

### Neural Proof Policy + Value Head**  
  - Operates on formal proof states (Lean/Coq context, local goals, hypotheses).  
  - Proposes the next tactic/lemma.  
  - Estimates distance-to-proof.  
  - Augmented by a **premise retriever** over mathlib/stdlib, indexed with symbolic + neural embeddings (RAG for 
  theorems and tactics).  

**3. Proof DAG Representation**  
  - Encodes proof states as tokens and a **dependency DAG** (GNN over hypotheses/lemmas).  
  - Enables structural reasoning, not just text-based reasoning.  

**4. Search Controller**  
  - Runs best-first / MCTS search over proof states.  
  - Learns from **self-play** to decide which candidate branches to explore.  

**5. Formal Checker**  
  - Validates each step immediately, closing the loop.  
  - Successful proof traces feed a **replay buffer** for continual training.  

**6. External Tool Integration**  
  - Interfaces with **CAS, SMT solvers (Z3), integer/LP solvers** via typed tool-use APIs.  
  - Outputs are structured as tactics or lemmas.  

## Training Pipeline

QEDNet training follows a **staged curriculum**:

**1. Pretraining**  
   - On large math/code/formal corpora.  

**2. Supervised Fine-Tuning**  
  - On proof tactic traces.  

**3. Retrieval Supervision**  
  - For premise selection tasks.  

**4. Reinforcement Learning**  
  - With proof-based rewards.  
  - Curriculum learning and self-play that auto-generates new theorems and hard negatives.  

5. **Neural Verifier / Critic**  
  - Reranks candidate proof steps before formal checking to **save search effort**.