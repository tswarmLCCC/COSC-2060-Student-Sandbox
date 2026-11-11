# Unit 7: Asynchronous Preparation & Diagnostic Drills
## Pipeline Orchestration & Software-Defined Asset DAGs

> **Time Commitment**: ~60 Minutes (Asynchronous Self-Study)  
> **Prerequisites**: Review of [Unit 7 Required Readings & Concepts](study_guide.md)  
> **Target Mastery**: Directed Acyclic Graphs (DAGs), Kahn's algorithm, In-degree tracking, Asset caching, Cycle detection.

---

## 1. Readiness Self-Check Checklist
Before attempting the diagnostic drills below, verify you have completed the foundational preparation:
- [ ] Grasped why monolithic linear ETL scripts collapse when a late-stage downstream task fails.
- [ ] Studied Kahn's algorithm for topological sorting of dependency graphs.
- [ ] Understood why data pipelines should track immutable assets rather than arbitrary task schedules.

---

## 2. Part 1: Foundational Concept Checks
Test your conceptual grasp of pipeline orchestration and asset dependency graphs. Formulate your answer first, then click the bar to verify your reasoning against the architectural rationale.

<details>
<summary>Question 1: What is the primary operational weakness of a monolithic linear Python script?</summary>

**Architectural Rationale:**
In a monolithic linear script, execution proceeds top-to-bottom. Intermediate states are held only in volatile RAM. 

If step 9 out of 10 fails due to an intermittent network hiccup (after 2.5 hours of heavy data extraction in steps 1 through 8), the entire script crashes. All in-memory work is destroyed, and the engineer must rerun the entire pipeline from line 1, doubling database load and missing SLA deadlines.
</details>

<details>
<summary>Question 2: What is an "in-degree" count in graph theory, and how is it used during DAG execution?</summary>

**Architectural Rationale:**
The **in-degree** of a node in a directed graph represents the number of direct upstream dependencies pointing into it. 

- A node with `in-degree == 0` has no pending dependencies and is immediately ready for execution.
- When an asset finishes execution successfully, the orchestrator decrements the in-degree count of all its downstream dependents.
- Any dependent node whose in-degree drops to zero is immediately queued for execution.
</details>

<details>
<summary>Question 3: How does Kahn's algorithm detect circular dependencies in a pipeline?</summary>

**Architectural Rationale:**
Kahn's algorithm initializes a queue of all nodes with `in_degree == 0`. It dequeues nodes one-by-one, adds them to the execution order list, and decrements the in-degrees of their neighbors. 

If a circular dependency exists (e.g. Node A $\to$ Node B $\to$ Node A), both nodes retain an in-degree of at least 1, and neither can ever enter the zero-degree queue. When the queue is empty, if the number of sorted nodes is less than the total number of nodes in the graph (`len(order) != len(nodes)`), a circular dependency cycle is mathematically proven to exist.
</details>

<details>
<summary>Question 4: What is the architectural difference between task-based orchestration and asset-based orchestration?</summary>

**Architectural Rationale:**
- **Task-Based Orchestration (Legacy Cron / Airflow):** Focuses on executing actions ("run script A, then run script B"). It tracks execution status but has zero awareness of what data was produced or whether the output table is stale.
- **Asset-Based Orchestration (Dagster / Modern DE):** Focuses on the data products themselves ("Asset: Clean_Telemetry_Parquet"). Each asset is defined with its upstream software dependencies and materialization logic. If upstream data has not changed, the orchestrator reuses cached assets automatically, skipping redundant execution.
</details>

---

## 3. Part 2: Code Execution Order & Syntax Traces

### Trace Drill 1: Manual Kahn's Topological Sort Trace
Consider the 5-node asset dependency graph below:
- Asset `raw_trips`: dependencies = `[]`
- Asset `raw_weather`: dependencies = `[]`
- Asset `clean_weather`: dependencies = `["raw_weather"]`
- Asset `joined_features`: dependencies = `["raw_trips", "clean_weather"]`
- Asset `trained_model`: dependencies = `["joined_features"]`

Calculate the initial in-degree counts and determine a valid topological execution order:

<details>
<summary>Trace the Algorithm: Step through in-degree counts and determine the execution order.</summary>

**Step-by-Step Execution Trace:**
1. **Initial In-Degrees**:
   - `raw_trips`: 0
   - `raw_weather`: 0
   - `clean_weather`: 1 (from `raw_weather`)
   - `joined_features`: 2 (from `raw_trips` and `clean_weather`)
   - `trained_model`: 1 (from `joined_features`)
2. **Initial Queue (`in_degree == 0`)**: `["raw_trips", "raw_weather"]`
3. **Execution Steps**:
   - Dequeue `raw_trips`: Add to order. Decrement `joined_features` in-degree ($2 \to 1$).
   - Dequeue `raw_weather`: Add to order. Decrement `clean_weather` in-degree ($1 \to 0$). Queue `clean_weather`.
   - Dequeue `clean_weather`: Add to order. Decrement `joined_features` in-degree ($1 \to 0$). Queue `joined_features`.
   - Dequeue `joined_features`: Add to order. Decrement `trained_model` in-degree ($1 \to 0$). Queue `trained_model`.
   - Dequeue `trained_model`: Add to order.
4. **Valid Topological Order**:
   `raw_trips` $\to$ `raw_weather` $\to$ `clean_weather` $\to$ `joined_features` $\to$ `trained_model`
</details>

### Trace Drill 2: Detecting Infinite Dependency Loops
Examine the dependency dictionary below:

```python
graph = {
    "extract_sales": [],
    "transform_orders": ["extract_sales", "apply_discounts"],
    "apply_discounts": ["transform_orders"] # Cycle!
}
```

<details>
<summary>Spot the Bug: Explain what Kahn's algorithm outputs when processing this graph.</summary>

**Diagnostic Analysis: CIRCULAR DEADLOCK**
- `extract_sales` has in-degree 0 and executes first.
- `transform_orders` and `apply_discounts` depend on each other in an infinite cycle. Both retain `in_degree == 1`.
- When `extract_sales` finishes, no remaining nodes have in-degree 0. The queue becomes empty.
- The sorted list only contains `["extract_sales"]` (length 1), but the graph has 3 nodes.
- **Defensive Error**: The orchestrator raises `ValueError("CYCLE DETECTED: Pipeline contains circular dependencies: transform_orders <-> apply_discounts")`.
</details>

---

## 4. Architecture Traps & Defensive Rules

<div style="background: #f8fafc; border-left: 4px solid #1e3a8a; padding: 1rem 1.25rem; margin: 1.5rem 0; border-radius: 0 4px 4px 0;">
  <h4 style="margin: 0 0 0.5rem 0; color: #1e3a8a;">The Three Golden Rules of DAG Pipeline Orchestration:</h4>
  <ol style="margin: 0; padding-left: 1.25rem; line-height: 1.7;">
    <li><strong>Isolate Failure Blast Radius:</strong> Each node must materialize an immutable, versioned artifact so failed runs can be resumed without rerunning completed upstream nodes.</li>
    <li><strong>Validate DAG Acyclicity at Startup:</strong> Always execute topological sorting at pipeline initialization to catch circular dependencies before running long computational tasks.</li>
    <li><strong>Ensure Idempotent Node Execution:</strong> Running an asset transformation twice must produce identical outputs without creating duplicate database rows or corrupted files.</li>
  </ol>
</div>

---

## 5. Preparation for Live In-Class Coding Clinic (Slot 2)
In the upcoming synchronous session, we will execute a live **"I Do, We Do" refactoring clinic**:
- **What to Have Open**: Terminal with Python 3.10+ activated, VS Code, and local Jupyter environment.
- **The Clinic Mission**: We will inspect a fragile 1,200-line monolithic linear ETL script, observe how a single late-stage error destroys all upstream computation, and live-code a pure-Python **Software-Defined Asset DAG** featuring topological sorting, failure isolation, and automated cache hits.
