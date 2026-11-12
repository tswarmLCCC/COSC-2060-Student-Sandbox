# Unit 7 Lab: The Unsleeping Pipeline (DAG Orchestration & DLQ)

> **Course**: COSC 2060 — Modern Data Engineering & AI Infrastructure  
> **Lab Deliverable**: Python script (`lab7_starter.py`) implementing an asset-based DAG orchestrator, retry policies with backoff, DLQ quarantine, and idempotent execution.  
> **Grading Mode**: 100-Point Rubric with automated verification assertions.

---

## 1. Coding Clinic: "I Do, We Do, You Do"

### "I Do" — The Instructor Demonstration: Exponential Backoff Retry Policy
When an external API or database is temporarily unavailable, we retry with exponential delays rather than hammering the server immediately:

```python
import time

def resilient_operation(action, max_attempts=3, base_delay=0.1):
    for attempt in range(1, max_attempts + 1):
        try:
            return action()
        except Exception as e:
            if attempt == max_attempts:
                raise e
            sleep_time = base_delay * (2 ** (attempt - 1))
            print(f"[RETRY] Attempt {attempt} failed ({e}). Sleeping {sleep_time:.2f}s...")
            time.sleep(sleep_time)

# Simulating transient failure that succeeds on attempt 2:
counter = 0
def flaky_network():
    global counter
    counter += 1
    if counter < 2:
        raise ConnectionResetError("Remote host disconnected.")
    return "SUCCESS: 500 records downloaded"

result = resilient_operation(flaky_network)
print("Final Outcome:", result)
```

---

### "We Do" — Guided Class Practice: Enforcing Idempotent Batch Inserts
To guarantee that re-running an ETL pipeline does not duplicate rows, we delete existing records for that partition before writing:

```python
# Target table represented as a dictionary partitioned by date:
TARGET_TABLE = {}

def idempotent_batch_write(date_partition: str, records: list):
    # Enforce idempotency: overwrite or clear existing partition:
    TARGET_TABLE[date_partition] = []
    for rec in records:
        TARGET_TABLE[date_partition].append(rec)
    print(f"Partition '{date_partition}' committed with {len(records)} records.")

# Running once:
idempotent_batch_write("2024-10-24", [{"id": 1}, {"id": 2}])
# Running a second time (simulating a pipeline replay):
idempotent_batch_write("2024-10-24", [{"id": 1}, {"id": 2}])

# Length remains 2, NOT 4!
assert len(TARGET_TABLE["2024-10-24"]) == 2
print("Idempotency verified: Zero duplicate rows generated.")
```

---

### "You Do" — Autonomous Applied Problem
Now, construct a resilient, automated DAG orchestrator that automates data ingestion, sanitization, DLQ routing, and downstream model updates.

---

## 2. 100-Point Graded Challenges

#### Part 0: Basics Warm-Up — Idempotent Key Writes & DLQ Filtering
Before running the full topological DAG orchestrator, run `part0_basics_warmup()` in `lab7_starter.py` to verify that overwriting records by primary key in a dictionary is idempotent across repeated runs.



You will complete four progressive challenges inside `lab7_starter.py`.

```
================================================================================
COSC 2060 - UNIT 7 LAB: ORCHESTRATION, DAGS, & DEAD-LETTER QUEUES
================================================================================
[Challenge 1: 25 pts] Directed Acyclic Graph (DAG) Dependency Resolver
[Challenge 2: 25 pts] Automated Retry Policy with Exponential Backoff
[Challenge 3: 25 pts] Poison Pill Quarantine & Dead-Letter Queue (DLQ)
[Challenge 4: 25 pts] Idempotent Daily Pipeline Execution Verification
================================================================================
```

### Complete Copy-and-Paste Starter Script (`lab7_starter.py`)

Save the following code as `courses/cosc-2060-data-engineering/content/labs/lab7_starter.py`:

```python
"""
COSC 2060 — Unit 7 Lab: Orchestration, DAGs, & Dead-Letter Queues
Name: [Your Name]
Date: [Current Date]
"""

import time
from typing import Dict, List, Any, Callable

# =========================================================================
# PART 0: BASICS WARM-UP — IDEMPOTENCY & DLQ FILTERING FROM SCRATCH
# =========================================================================
def part0_basics_warmup() -> Dict[str, Any]:
    """
    PART 0: Basics Warm-Up (Ground-Up Idempotency & DLQ Routing)
    Demonstrates why overwriting a dictionary key by ID is idempotent (running twice
    never creates duplicate keys) before building the full DAG orchestrator.
    """
    print("=== Part 0: Basics Warm-Up (Idempotent Key Writes & DLQ Filtering) ===")
    store = {}
    for run in range(2):
        store["TRUCK-101"] = 120.0
        store["TRUCK-219"] = 240.0
    print(f"Store after 2 identical runs has {len(store)} trucks (Zero duplicates!): {store}")
    return store


# =========================================================================
# CHALLENGE 1: Directed Acyclic Graph (DAG) Dependency Resolver (25 pts)
# =========================================================================
class PipelineNode:
    def __init__(self, name: str, func: Callable, dependencies: List[str] = None, max_retries: int = 2):
        self.name = name
        self.func = func
        self.dependencies = dependencies or []
        self.max_retries = max_retries
        self.status = "PENDING"  # PENDING, RUNNING, SUCCESS, FAILED, SKIPPED
        self.result = None
        self.error = None


class DAGOrchestrator:
    def __init__(self):
        self.nodes: Dict[str, PipelineNode] = {}
        self.context: Dict[str, Any] = {}
        self.dlq: List[Dict[str, Any]] = []

    def add_node(self, node: PipelineNode):
        self.nodes[node.name] = node

    def get_execution_order(self) -> List[str]:
        """
        Computes topological order using Kahn's algorithm or recursive DFS.
        Raises ValueError if a circular dependency (cycle) is detected.
        """
        in_degree = {name: 0 for name in self.nodes}
        adj = {name: [] for name in self.nodes}
        
        for name, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    raise ValueError(f"Dependency '{dep}' does not exist in DAG.")
                adj[dep].append(name)
                in_degree[name] += 1
                
        queue = [name for name, deg in in_degree.items() if deg == 0]
        order = []
        
        while queue:
            curr = queue.pop(0)
            order.append(curr)
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    
        if len(order) != len(self.nodes):
            raise ValueError("Cycle detected in DAG! Pipeline execution blocked.")
            
        return order


# =========================================================================
# CHALLENGE 2: Automated Retry Policy with Exponential Backoff (25 pts)
# =========================================================================
    def execute_node_with_retry(self, node: PipelineNode, base_delay: float = 0.05) -> bool:
        """
        Executes a node function. If an exception occurs, retries up to max_retries
        with exponential backoff delay (base_delay * 2^(attempt - 1)).
        Returns True if success, False if all retries exhausted.
        """
        for attempt in range(1, node.max_retries + 2):
            try:
                node.status = "RUNNING"
                node.result = node.func(self.context)
                node.status = "SUCCESS"
                self.context[node.name] = node.result
                return True
            except Exception as e:
                node.error = str(e)
                if attempt <= node.max_retries:
                    delay = base_delay * (2 ** (attempt - 1))
                    time.sleep(delay)
                else:
                    node.status = "FAILED"
                    return False


# =========================================================================
# CHALLENGE 3: Poison Pill Quarantine & Dead-Letter Queue (DLQ) (25 pts)
# =========================================================================
    def run_pipeline(self):
        """
        Executes the entire DAG in topological order.
        If a dependency fails, downstream nodes are marked as SKIPPED.
        """
        order = self.get_execution_order()
        for name in order:
            node = self.nodes[name]
            
            # Check dependencies:
            deps_ok = True
            for dep in node.dependencies:
                if self.nodes[dep].status != "SUCCESS":
                    deps_ok = False
                    break
                    
            if not deps_ok:
                node.status = "SKIPPED"
                print(f"Skipping node '{name}' because upstream dependencies were not successful.")
                continue
                
            self.execute_node_with_retry(node)


# =========================================================================
# CHALLENGE 4: Idempotent Daily Pipeline Execution (25 pts)
# =========================================================================
# Production State Store:
FINAL_FEATURE_STORE = {}

# Node 1: Ingest with Simulated Transient Glitch
_transient_attempts = 0
def task_ingest_fuel(ctx):
    global _transient_attempts
    _transient_attempts += 1
    if _transient_attempts < 2:
        raise ConnectionError("Transient network timeout connecting to fuel gateway.")
    return [
        {"tx_id": "TX-01", "truck_id": "TRUCK-101", "gallons": 120.0, "status": "VALID"},
        {"tx_id": "TX-02", "truck_id": "TRUCK-219", "gallons": 240.0, "status": "VALID"},
        {"tx_id": "TX-03", "truck_id": "TRUCK-304", "gallons": -50.0, "status": "POISON_PILL"}, # Corrupted!
        {"tx_id": "TX-04", "truck_id": "TRUCK-219", "gallons": 180.0, "status": "VALID"}
    ]

# Node 2: Clean & Quarantine Poison Pills into DLQ
def task_clean_and_dlq(ctx):
    raw_data = ctx["ingest_fuel"]
    clean_batch = []
    for row in raw_data:
        if row["gallons"] <= 0.0 or row["status"] == "POISON_PILL":
            # Quarantine to DLQ:
            orchestrator.dlq.append({
                "record": row,
                "reason": "Invalid gallon measurement: negative or zero quantity.",
                "quarantined_at": time.time()
            })
        else:
            clean_batch.append(row)
    return clean_batch

# Node 3: Idempotent Aggregate Write
def task_write_features(ctx):
    clean_data = ctx["clean_fuel"]
    date_partition = "2024-10-24"
    
    # Enforce idempotency: clear existing partition before inserting:
    FINAL_FEATURE_STORE[date_partition] = {}
    for row in clean_data:
        tid = row["truck_id"]
        if tid not in FINAL_FEATURE_STORE[date_partition]:
            FINAL_FEATURE_STORE[date_partition][tid] = 0.0
        FINAL_FEATURE_STORE[date_partition][tid] += row["gallons"]
    return FINAL_FEATURE_STORE[date_partition]


# =========================================================================
# VERIFICATION SUITE (Do not modify)
# =========================================================================
if __name__ == "__main__":
    part0_basics_warmup()
    print("\n=== Step 1: Building DAG & Checking Topological Order ===")
    orchestrator = DAGOrchestrator()
    orchestrator.add_node(PipelineNode("ingest_fuel", task_ingest_fuel, dependencies=[], max_retries=2))
    orchestrator.add_node(PipelineNode("clean_fuel", task_clean_and_dlq, dependencies=["ingest_fuel"]))
    orchestrator.add_node(PipelineNode("write_features", task_write_features, dependencies=["clean_fuel"]))

    order = orchestrator.get_execution_order()
    print(f"Topological Execution Order: {order}")
    assert order == ["ingest_fuel", "clean_fuel", "write_features"]

    print("\n=== Step 2: Testing Cycle Detection ===")
    cycle_dag = DAGOrchestrator()
    cycle_dag.add_node(PipelineNode("A", lambda ctx: None, dependencies=["B"]))
    cycle_dag.add_node(PipelineNode("B", lambda ctx: None, dependencies=["A"]))
    try:
        cycle_dag.get_execution_order()
        assert False, "Failed to detect circular dependency!"
    except ValueError as e:
        print(f"[PASS] Cycle detected successfully: {e}")

    print("\n=== Step 3: Executing Resilient Pipeline (With Retries & DLQ) ===")
    orchestrator.run_pipeline()

    assert orchestrator.nodes["ingest_fuel"].status == "SUCCESS"
    assert orchestrator.nodes["clean_fuel"].status == "SUCCESS"
    assert orchestrator.nodes["write_features"].status == "SUCCESS"
    print("[PASS] All pipeline nodes completed with SUCCESS.")

    print("\n=== Step 4: Verifying Dead-Letter Queue (DLQ) Quarantine ===")
    print(f"DLQ contains {len(orchestrator.dlq)} quarantined records.")
    assert len(orchestrator.dlq) == 1
    assert orchestrator.dlq[0]["record"]["tx_id"] == "TX-03"
    print(f"[PASS] Poison pill TX-03 correctly isolated in DLQ.")

    print("\n=== Step 5: Verifying Idempotent Execution ===")
    # Re-running the pipeline a second time:
    orchestrator.run_pipeline()
    partition = FINAL_FEATURE_STORE["2024-10-24"]
    print(f"Aggregated Totals: {partition}")
    # TRUCK-219 had 240.0 + 180.0 = 420.0 gallons:
    assert partition["TRUCK-219"] == 420.0, f"Expected 420.0, got {partition['TRUCK-219']}"
    assert partition["TRUCK-101"] == 120.0
    print("[PASS] Idempotency confirmed: Re-run produced zero duplicate gallons.")

    print("\n[SUCCESS] All Unit 7 Lab challenges verified successfully!")
```

---

## 3. 100-Point Rubric Table

| Criteria | Points | Full Mastery (100%) | Minor Flaw (75%) | Unacceptable (0%) |
|---|---|---|---|---|
| **Challenge 1: DAG Dependency Engine** | 25 pts | Correctly resolves topological order using in-degree queue or DFS; catches circular cycles with explicit `ValueError`. | Resolves linear order but fails cycle detection. | Hardcoded list; crashes on DAG graph traversal. |
| **Challenge 2: Exponential Backoff** | 25 pts | Retries transient errors with exponential delay ($2^{\text{attempt}-1}$); caps at `max_retries` before declaring node failed. | Retries without delay or retries forever in an infinite loop. | Fails immediately on first transient error without retrying. |
| **Challenge 3: Dead-Letter Queue** | 25 pts | Quarantines poison pills into DLQ with error reasons and timestamps; clean records continue processing. | Drops poison pills silently without logging to DLQ. | Crashes entire batch on first corrupted record. |
| **Challenge 4: Idempotent Execution** | 25 pts | Partition overwrites prevent duplication; re-running pipeline outputs identical deterministic values. | Duplicate records generated on re-run (e.g. 840 gallons instead of 420). | Execution fails on subsequent runs. |
