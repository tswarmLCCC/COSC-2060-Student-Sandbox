# Unit 7 Lab Grading Rubric: Orchestration, Asset DAGs, & Dead-Letter Queues

> **Course**: COSC 2060 — Modern Data Engineering & AI Infrastructure  
> **Assessment**: Unit 7 Applied Engineering Lab (`lab7_yourlastname.py`)  
> **Total Points**: 100 Points (Canvas SpeedGrader)

---

| Criteria | Points | Full Mastery (100%) | Minor Flaw (75%) | Unacceptable (0%) |
|---|---|---|---|---|
| **Challenge 1: DAG Dependency Engine** | 25 pts | Correctly resolves topological order using in-degree queue or DFS; catches circular cycles with explicit `ValueError`. | Resolves linear order but fails cycle detection. | Hardcoded list; crashes on DAG graph traversal. |
| **Challenge 2: Exponential Backoff** | 25 pts | Retries transient errors with exponential delay ($2^{\text{attempt}-1}$); caps at `max_retries` before declaring node failed. | Retries without delay or retries forever in an infinite loop. | Fails immediately on first transient error without retrying. |
| **Challenge 3: Dead-Letter Queue** | 25 pts | Quarantines poison pills into DLQ with error reasons and timestamps; clean records continue processing. | Drops poison pills silently without logging to DLQ. | Crashes entire batch on first corrupted record. |
| **Challenge 4: Idempotent Execution** | 25 pts | Partition overwrites prevent duplication; re-running pipeline outputs identical deterministic values. | Duplicate records generated on re-run (e.g. 840 gallons instead of 420). | Execution fails on subsequent runs. |
