# Unit 7: Required Readings, Concepts & Video Lectures

Welcome to the core instructional lecture and study hub for **Unit 7: Orchestration & Automation (The Unsleeping Pipeline)**. This page organizes all weekly learning materials into four structured chapters:

1. **Instructor Lecture & Conceptual Deep Dive:** Master the target pipeline heartbeat and Dead-Letter Queue (DLQ) schemas, automated orchestration source systems, Directed Acyclic Graphs (DAGs), the "Cron House of Cards" operational catastrophe, mathematical idempotency (<i>f</i>(<i>f</i>(<i>x</i>)) = <i>f</i>(<i>x</i>)), exponential backoff retries, and poison-pill isolation.
2. **Required Readings & Authoritative Tutorial Guides:** Study curated official documentation from Dagster Software-Defined Assets, Prefect orchestration, and AWS idempotency standards.
3. **Required Micro-Video Lectures (Embedded):** Watch high-definition video chapters with verified timestamp navigation to observe dependency-aware asset DAGs and automated backfills executed in live environments.
4. **Institutional Video Lecture Embeds:** Access campus-specific video recordings and announcements uploaded by your instructor.

*Work through each section in sequence as part of your 150-minute asynchronous self-study allocation before starting the applied laboratory assignment.*

---

## 1. Instructor Lecture & Conceptual Deep Dive

### The Unsleeping Pipeline: Dependency DAGs, Idempotency & Fault Tolerance

#### 1. Unit Overview & Objectives
In Units 1 through 6, you built each component of an end-to-end AI infrastructure ecosystem:
* Relational feature matrices in DuckDB (Unit 1)
* High-throughput anomaly detection in Polars (Unit 2)
* Visual sensor manifests in OpenCV (Unit 3)
* Vector embeddings and RAG in Sentence-Transformers (Unit 4)
* Contract-guaranteed REST APIs in FastAPI (Unit 5)
* Sandboxed MCP agentic tools (Unit 6)

Up to this point, you have executed your Python scripts manually in your terminal: `python lab1.py`, `python lab2.py`.

In **Unit 7**, we confront the realities of production engineering: **No human sits in a terminal at 3:15 AM every morning to press "Enter".**

Real enterprise data systems must operate unattended, 24 hours a day, 365 days a year. However, simply scheduling raw Python scripts with basic Linux `cron` or Windows Task Scheduler leads to catastrophic failures. If script #1 fails or hangs due to a network glitch, script #2 runs blind on stale data, poisoning downstream databases and triggering false operational emergencies.

To build reliable data pipelines, data engineers use **Data Orchestrators** (such as **Dagster**, **Prefect**, or **Apache Airflow**). We model data workflows as **Directed Acyclic Graphs (DAGs)**, enforce **idempotency**, configure **exponential backoff retries**, and isolate corrupted records into **Dead-Letter Queues (DLQs)**.

```
[Raw Ingestion Asset] ──(Success)──> [Cleaning & Validation] ──> [Downstream ML & RAG Assets]
        │ (Network Glitch)                    │ (Corrupted Record)
        ▼                                     ▼
[Exponential Backoff Retries]        [Dead-Letter Queue (DLQ)]
```

**Measurable Learning Objectives:**
* **Explain** why time-based schedulers (Linux `cron`) fail in enterprise environments compared to dependency-aware Directed Acyclic Graph (DAG) orchestrators.
* **Design and Implement** idempotent data transformations (<i>f</i>(<i>f</i>(<i>x</i>)) = <i>f</i>(<i>x</i>)) that can be safely re-executed multiple times without producing duplicate records or state corruption.
* **Configure** automated fault-tolerance mechanisms, including exponential backoff retry policies and structured execution heartbeats.
* **Implement** a Dead-Letter Queue (DLQ) pattern that quarantines malformed "poison pill" records while allowing valid transactional batches to complete.
* **Construct** an end-to-end Python orchestration engine that executes upstream data ingestion, transforms, and downstream model updates in strict topological dependency order.

---

#### 2. What Our Output Looks Like and Where the Data Comes From

##### The Purpose
Our goal in Unit 7 is to build a **Fault-Tolerant Pipeline Orchestrator** that executes our multi-stage data pipeline in strict topological dependency order and produces three verified outputs:
1. The **Idempotent Curated Dataset** (`curated_batch.parquet`), guaranteed free of duplicate primary keys even if the pipeline is executed three times in a row.
2. A **Dead-Letter Queue Quarantine Log** (`dlq_quarantine.jsonl`) capturing any corrupted input records along with their exact validation error messages and timestamps.
3. A **Pipeline Execution Heartbeat Manifest** (`pipeline_heartbeat.json`) recording the execution order, status, row counts, and retry counts of every stage in the DAG.

##### Why Operations Teams Need Heartbeats and Dead-Letter Queues
When an automated pipeline runs overnight, two failure modes must be prevented:
* **Silent Failure:** A script crashes or processes `0` rows, and nobody notices until dispatchers open a blank dashboard the next morning. Writing a structured `pipeline_heartbeat.json` file after every run gives monitoring tools an immediate check on whether every stage succeeded and how many rows were processed.
* **One Bad Row Crashes 10,000 Good Rows:** If a batch of 10,000 telemetry records contains 2 corrupted records (called *"poison pills"*), an unguarded script will throw an unhandled exception on the first bad row and abort the entire batch. By catching validation errors per record and routing those 2 bad rows into `dlq_quarantine.jsonl`, the 9,998 valid rows finish on time while engineers inspect the quarantined records cleanly.

##### Where the Raw Data Comes From (Source Systems)
An orchestrated nightly or hourly pipeline pulls from multiple upstream sources that can each experience real-world faults:
1. **Remote SFTP / Cloud Object Drop Zones (`incoming_batch.jsonl`):** Raw batches uploaded by partner carriers or terminal gateways, which occasionally contain truncated lines or schema violations.
2. **External Weather & Telematics APIs:** Remote endpoints that occasionally return temporary `503 Service Unavailable` timeouts when network traffic spikes.
3. **Automated Schedulers (`GitHub Actions` / `Dagster` / `cron`):** Scheduled triggers or webhook events that initiate the pipeline run.

##### Sample Output Dataset (The Target Heartbeat & DLQ Shapes)
When our Unit 7 orchestrator finishes a run, it outputs a structured **Heartbeat Manifest** (`pipeline_heartbeat.json`) and a **Dead-Letter Queue** (`dlq_quarantine.jsonl`):

**1. `output/pipeline_heartbeat.json`:**
```json
{
  "run_id": "run_20261024_0300",
  "pipeline_status": "SUCCESS_WITH_DLQ_WARNINGS",
  "execution_order": [
    "raw_telemetry_scan",
    "cleaned_features",
    "anomaly_model_score",
    "vector_rag_index",
    "publish_daas_service"
  ],
  "metrics": {
    "total_records_read": 500,
    "valid_records_written": 498,
    "dlq_records_quarantined": 2,
    "transient_retries_triggered": 1
  }
}
```

**2. `output/dlq_quarantine.jsonl`:**
```json
{"record_id": "REC-104", "raw_payload": {"route_id": 104, "gallons": -45.0}, "error_reason": "ValidationError: gallons must be > 0", "quarantined_at": "2026-10-24T03:00:04Z"}
{"record_id": "REC-289", "raw_payload": {"route_id": null, "gallons": 120.0}, "error_reason": "ValidationError: route_id is required", "quarantined_at": "2026-10-24T03:00:05Z"}
```

---

#### 3. The 4:30 AM Stranded Drivers Disaster (The Cron Anti-Pattern)

To understand why production data engineering abandoned unmanaged cron jobs, examine an authentic failure in nationwide fleet operations.

Apex Freight operated a fleet of 800 trucks. To monitor fuel card fraud and driver compliance, the engineering team set up five nightly Python scripts using standard Linux cron jobs scheduled 30 minutes apart:

```text
# CRON SCHEDULE (THE "HOUSE OF CARDS" ANTI-PATTERN)
0 3 * * * /usr/bin/python3 /etl/01_download_fuel_records.py
30 3 * * * /usr/bin/python3 /etl/02_clean_and_deduplicate.py
0 4 * * * /usr/bin/python3 /etl/03_calculate_mileage_features.py
30 4 * * * /usr/bin/python3 /etl/04_run_anomaly_detection.py
0 5 * * * /usr/bin/python3 /etl/05_freeze_fraudulent_cards.py
```

Notice the fatal assumption: The team assumed that each script would finish within exactly 30 minutes, and that each script would always succeed.

##### The Midnight Glitch
On Tuesday at 3:12 AM, the national fuel vendor's FTP server experienced high load. Script #1 (`01_download_fuel_records.py`) hung waiting for an open network socket. It did not download any new files, but because it had no timeout configured, it remained frozen in memory.

At 3:30 AM, cron blindly fired Script #2 (`02_clean_and_deduplicate.py`). Script #2 found an empty incoming directory. Instead of failing with an alert, the script exited with code 0, wiping the intermediate staging table in preparation for incoming rows.

At 4:00 AM, Script #3 executed. Finding zero rows for today, it generated an empty feature table.

##### The Catastrophic Cascade
At 4:30 AM, Script #4 (`04_run_anomaly_detection.py`) executed. Finding all current fuel totals recorded as `0.00 gallons` due to the wiped staging table, the model evaluated every active truck as an extreme statistical outlier.

At 5:00 AM, Script #5 (`05_freeze_fraudulent_cards.py`) executed automatically. It read the corrupted anomaly output and **automatically deactivated the corporate fuel cards of 412 active truck drivers**.

Across the Midwest and Great Plains, 412 truck drivers pulled into diesel truck stops at 5:15 AM in 12&deg;F winter temperatures. Every card was declined. Drivers could not purchase fuel or stay warm in idling trucks. Dispatch switchboards were overwhelmed with panic calls. Operations halted nationwide for 7 hours while engineers manually restored database snapshots and unblocked cards one by one. The incident cost the company **\$240,000 in emergency towing, driver compensation, and lost shipper trust**.

##### The Architectural Diagnosis: The Cron Anti-Pattern
Why did this cascade happen?
1. **Blind Time Execution:** Cron triggers tasks based on the clock, completely oblivious to whether upstream prerequisites succeeded.
2. **No Data Lineage Awareness:** Downstream tasks had no way to verify if their input data was fresh or empty.
3. **Non-Idempotent Scripts:** When engineers tried to restart the pipeline, partial writes caused duplicate primary key errors.

**The Solution:** Modern data orchestrators (like Dagster) replace time-based triggers with **Asset DAGs**. A downstream asset will *never* materialize unless all upstream parent assets have successfully produced valid, verified data outputs.

---

#### 4. The Core Concept: Idempotency (<i>f</i>(<i>f</i>(<i>x</i>)) = <i>f</i>(<i>x</i>))

The single most important principle in pipeline engineering is **Idempotency**.

In mathematics, an operation is idempotent if applying it multiple times produces the exact same result as applying it once:
<p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.6rem; border-radius: 4px;">
  <i>f</i>( <i>f</i>(<i>x</i>) ) = <i>f</i>(<i>x</i>)
</p>

##### Non-Idempotent Pipeline (Dangerous):
```sql
-- DANGEROUS: Every time you run this, you insert duplicate transactions!
INSERT INTO daily_mileage_report
SELECT truck_id, SUM(miles) FROM live_gps_logs GROUP BY truck_id;
```
If your script crashes halfway through and you rerun it, you double-count every driver's mileage!

##### Idempotent Pipeline (Production Standard):
```sql
-- IDEMPOTENT: Safe to run 1 time or 100 times on the same date partition
DELETE FROM daily_mileage_report WHERE report_date = '2026-10-24';
INSERT INTO daily_mileage_report (report_date, truck_id, total_miles)
SELECT '2026-10-24', truck_id, SUM(miles) FROM live_gps_logs WHERE log_date = '2026-10-24' GROUP BY truck_id;
```
Whether this query runs once, fails twice, or is rerun by a dispatcher five times, the final state of the database is mathematically identical.

---

#### 5. Fault Tolerance: Retries & Dead-Letter Queues (DLQ)

In production, external systems fail constantly: network timeouts, `503 Service Unavailable` errors, or malformed JSON payloads. A resilient orchestrator classifies failures into two distinct categories:

```
FAILURE CLASSIFICATION:
1. TRANSIENT FAILURES (Network hiccup, brief server restart):
   ──> Solution: Retry with Exponential Backoff (Wait 2s, then 4s, then 8s)

2. PERMANENT FAILURES ("Poison Pill" - Corrupted byte, invalid schema):
   ──> Retrying will NEVER fix this! Retries will loop forever.
   ──> Solution: Dead-Letter Queue (DLQ). Move bad record to quarantine table, log alert, and continue processing valid records!
```

| Error Category | Typical Cause | What Happens If You Retry? | Engineering Pattern |
| :--- | :--- | :--- | :--- |
| **Transient Failure** | Socket timeout, `503 Gateway Busy`, brief DNS blip | Waiting a few seconds and trying again succeeds. | **Exponential Backoff Retry** (`delay * 2^attempt`). |
| **Permanent Failure ("Poison Pill")** | Row has `gallons = -999` or missing primary key `route_id: null` | Retrying 100 times fails all 100 times because the payload is invalid. | **Dead-Letter Queue (DLQ)**: Quarantine the bad row to `dlq_quarantine.jsonl` and continue the batch. |

---

#### 6. Step-by-Step Code Ramp-Up & Guided Implementation Walkthrough (Python Orchestration)

Let's first build the three individual building blocks (Exponential Backoff, Dead-Letter Queue splitting, and Idempotent DuckDB Upserts) step by step, and then run the complete `DAGOrchestrator` walkthrough.

##### Step 1: Writing an Exponential Backoff Retry Wrapper
When a remote API experiences a brief hiccup, we double our wait time between retries (`base_delay * (2 ** attempt)`) so we don't overwhelm a recovering server:

```python
import time

def run_with_backoff(func, max_retries: int = 3, base_delay_sec: float = 0.1):
    """Runs func(), retrying transient TimeoutErrors with exponential backoff."""
    attempt = 0
    while True:
        try:
            return func(), attempt
        except TimeoutError as exc:
            attempt += 1
            if attempt >= max_retries:
                raise RuntimeError(f"Failed after {max_retries} attempts: {exc}") from exc
            wait_time = base_delay_sec * (2 ** (attempt - 1))
            time.sleep(wait_time)

# Simulate a flaky API that fails on attempt 1, then succeeds on attempt 2:
state = {"calls": 0}
def flaky_api():
    state["calls"] += 1
    if state["calls"] == 1:
        raise TimeoutError("503 Remote Gateway Timeout")
    return {"status": "ok", "rows": 100}

result, retries = run_with_backoff(flaky_api)
print(f"API Result: {result} (Retries used: {retries})")
```

##### Step 2: Splitting a Batch into Valid Rows and a Dead-Letter Queue (DLQ)
When iterating through a batch of records, wrap per-row validation in a `try ... except` block so a poison-pill record is routed to `dlq_records` without aborting the loop:

```python
raw_batch = [
    {"route_id": 101, "driver_id": 42, "gallons": 125.0},
    {"route_id": 102, "driver_id": 42, "gallons": -30.0},  # Poison pill: negative gallons!
    {"route_id": None, "driver_id": 99, "gallons": 110.0}, # Poison pill: null primary key!
    {"route_id": 103, "driver_id": 99, "gallons": 140.0},
]

valid_records, dlq_records = [], []
for row in raw_batch:
    try:
        if row.get("route_id") is None or int(row["route_id"]) <= 0:
            raise ValueError("route_id must be a positive integer")
        if float(row.get("gallons", 0)) <= 0:
            raise ValueError("gallons must be strictly positive (> 0)")
        valid_records.append(row)
    except Exception as err:
        dlq_records.append({"raw_payload": row, "error_reason": str(err)})

print(f"Valid: {len(valid_records)} | Quarantined to DLQ: {len(dlq_records)}")
```

##### Step 3: Enforcing Idempotent Upserts in DuckDB (`INSERT OR REPLACE INTO`)
By defining a `PRIMARY KEY` on our target DuckDB table and using `INSERT OR REPLACE INTO`, running the exact same batch 3 times in a row updates keys in place and guarantees zero duplicate rows:

```python
import duckdb

con = duckdb.connect()
con.sql("CREATE TABLE curated_routes (route_id INT PRIMARY KEY, driver_id INT, gallons DOUBLE)")

for _ in range(3):  # Run 3 times to prove idempotency: f(f(x)) = f(x)
    for r in valid_records:
        con.execute("INSERT OR REPLACE INTO curated_routes VALUES (?, ?, ?)", [r["route_id"], r["driver_id"], r["gallons"]])

print("Row count after 3 identical runs:", con.sql("SELECT COUNT(*) FROM curated_routes").fetchone()[0])
```

##### Step 4: Guided Implementation Walkthrough — Production DAG Runner in Python
Here is how a complete `DAGOrchestrator` manages task dependencies, exponential backoff retries, Dead-Letter Queue logging, and topological execution order:

```python
import time
import json
from typing import Dict, Any, List

class PipelineTask:
    def __init__(self, name: str, dependencies: List[str] = None):
        self.name = name
        self.dependencies = dependencies or []
        self.executed = False
        self.result = None

class DAGOrchestrator:
    def __init__(self):
        self.tasks: Dict[str, PipelineTask] = {}
        self.dlq: List[Dict[str, Any]] = []

    def add_task(self, name: str, dependencies: List[str] = None):
        self.tasks[name] = PipelineTask(name, dependencies)

    def execute_with_retry(self, task_name: str, func, max_retries: int = 3):
        attempt = 0
        backoff = 1.0
        while attempt < max_retries:
            try:
                return func()
            except Exception as e:
                attempt += 1
                if attempt >= max_retries:
                    # Move to Dead-Letter Queue
                    self.dlq.append({"task": task_name, "error": str(e), "timestamp": time.time()})
                    raise RuntimeError(f"Task {task_name} permanently failed after {max_retries} attempts: {e}")
                time.sleep(backoff)
                backoff *= 2.0

    def run(self):
        """Executes tasks in topological dependency order."""
        executed_order = []
        while len(executed_order) < len(self.tasks):
            progress = False
            for name, task in self.tasks.items():
                if task.executed:
                    continue
                # Check if all upstream dependencies have succeeded
                if all(self.tasks[dep].executed for dep in task.dependencies):
                    print(f"[*] Materializing Asset: {name} (Prerequisites: {task.dependencies})")
                    task.executed = True
                    executed_order.append(name)
                    progress = True
            if not progress:
                raise RuntimeError("Circular dependency or unresolvable prerequisite detected in DAG!")
        return executed_order

# 1. Define Asset DAG
pipeline = DAGOrchestrator()
pipeline.add_task("raw_telemetry_scan", dependencies=[])
pipeline.add_task("cleaned_features", dependencies=["raw_telemetry_scan"])
pipeline.add_task("anomaly_model_score", dependencies=["cleaned_features"])
pipeline.add_task("vector_rag_index", dependencies=["cleaned_features"])
pipeline.add_task("publish_daas_service", dependencies=["anomaly_model_score", "vector_rag_index"])

# 2. Execute Orchestration
execution_sequence = pipeline.run()
print("[+] DAG Execution Successfully Completed in Topological Order:")
for step, asset in enumerate(execution_sequence, 1):
    print(f"  Step {step}: {asset}")
```

**Verification Output:**
```
[*] Materializing Asset: raw_telemetry_scan (Prerequisites: [])
[*] Materializing Asset: cleaned_features (Prerequisites: ['raw_telemetry_scan'])
[*] Materializing Asset: anomaly_model_score (Prerequisites: ['cleaned_features'])
[*] Materializing Asset: vector_rag_index (Prerequisites: ['cleaned_features'])
[*] Materializing Asset: publish_daas_service (Prerequisites: ['anomaly_model_score', 'vector_rag_index'])
[+] DAG Execution Successfully Completed in Topological Order:
  Step 1: raw_telemetry_scan
  Step 2: cleaned_features
  Step 3: anomaly_model_score
  Step 4: vector_rag_index
  Step 5: publish_daas_service
```

Notice that `publish_daas_service` was prevented from running until *both* upstream child branches (`anomaly_model_score` and `vector_rag_index`) were completely validated.

---

#### 7. Practice Exercises & Formative Self-Check FAQ

Try these three exercises in your GitHub Codespaces sandbox (`units/unit_07_orchestration_and_automation/`) before starting the graded lab:

1. **Exercise 1 (Circular Dependency Detection):** Add two tasks that depend on each other (`pipeline.add_task("a", ["b"])` and `pipeline.add_task("b", ["a"])`) and confirm that `pipeline.run()` immediately raises a `RuntimeError` instead of hanging forever.
2. **Exercise 2 (Idempotency Proof):** Run `coding_clinic.py` twice in a row and check the output Parquet row count to verify that running the pipeline multiple times produces the exact same number of rows.
3. **Exercise 3 (Cron Expression Practice):** Verify what time a GitHub Actions workflow with `schedule: - cron: '0 3 * * *'` triggers (3:00 AM UTC daily).

##### Common Traps & Formative Self-Check FAQ

* **Question 1: What is the difference between an imperative task and a declarative software-defined asset (SDA)?**  
  *Answer:* An imperative task (like in legacy Airflow or cron) says: *"Run this script now."* A declarative asset (like in Dagster) says: *"This data table should exist and be up-to-date with these upstream sources."* The orchestrator inspects what data is missing or stale and executes only the necessary computation.

* **Question 2: What should happen when a poison-pill record fails inside a batch?**  
  *Answer:* The pipeline should log the malformed record into a Dead-Letter Queue (DLQ) table or `.jsonl` file with the exact error reason and timestamp, emit an alert metric in the heartbeat file, and continue transforming the remaining 99.9% of valid records.

* **Question 3: Should I retry a data `ValidationError` (like `gallons = -50`) using exponential backoff?**  
  *Answer:* No! Waiting 2, 4, and 8 seconds will never turn `-50` into a positive number. Only retry **transient infrastructure failures** (`TimeoutError`, `ConnectionError`, HTTP `503`), and route **schema/domain validation errors** directly to the Dead-Letter Queue.

---

## 2. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical specifications before beginning your applied lab:

1. **[Dagster Official Documentation: Software-Defined Assets (SDA)](https://docs.dagster.io/concepts/assets/software-defined-assets)**
   *Understand declarative asset orchestration, dependency graphs, partitioning, and automated data lineage.*

2. **[Prefect Documentation: Flows, Tasks & Dynamic Orchestration](https://docs.prefect.io/)**
   *Learn how Python decorators transform standard code into resilient, observable, retryable workflows.*

3. **[AWS Architecture Center: Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)**
   *Study the definitive architectural standard for idempotency tokens, distributed state consistency, and retry safety.*

4. **[Dagster Guide: Why Dagster Replaced Legacy Task Schedulers](https://dagster.io/docs)**
   *Explore the operational differences between cron scripts, Airflow imperative operators, and asset-based engineering.*

5. **[The DataOps Manifesto: Agile Principles for Data Pipelines](https://dataopsmanifesto.org/en/)**
   *Review the industry framework for automated testing, reproducible deployments, and continuous monitoring in data systems.*

---

## 3. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to observe asset-based data orchestrators and fault-tolerant DAGs in action:

### What is Data Orchestration? Asset DAGs Explained (Dagster 101) <span style="font-size: 0.9em; color: #64748b;">(Timnology - Core Concepts)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Dagster 101 Core Concepts" src="https://www.youtube.com/embed/k-iQNrtKhjo" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=k-iQNrtKhjo" target="_blank" rel="noopener">Open video in new tab</a></p>

### Dagster Tutorial: Software-Defined Assets & Data Lineage <span style="font-size: 0.9em; color: #64748b;">(Dagster - 10-Minute Walkthrough)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Dagster Data Orchestration Walkthrough" src="https://www.youtube.com/embed/L5kTxCM-tOk" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=L5kTxCM-tOk" target="_blank" rel="noopener">Open video in new tab</a></p>

### Automated Data Pipelines: Scheduling Python Scripts with GitHub Actions <span style="font-size: 0.9em; color: #64748b;">(Patrick Loeber - Full Tutorial)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Schedule Python Scripts with GitHub Actions" src="https://www.youtube.com/embed/PaGp7Vi5gfM" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=PaGp7Vi5gfM" target="_blank" rel="noopener">Open video in new tab</a></p>

---

## 4. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for Unit 7 will appear in this designated container.</p>
</div>
