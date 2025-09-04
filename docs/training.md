# Training Pipeline
QEDNet training follows a staged curriculum:

## Pretraining
- on large math/code/formal corpora

## Supervised Fine-Tuning
- on proof tactic traces

## Retrieval Supervision
  - For premise selection tasks

## Reinforcement Learning
- with proof-based rewards
- curriculum learning and self-play that auto-generates new theorems and hard negatives

## Neural Verifier / Critic
- reranks candidate proof steps before formal checking to save search effort