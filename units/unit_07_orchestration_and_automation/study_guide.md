# Unit 7: Required Readings, Concepts & Video Lectures

Welcome to the instructional reading and study guide for **Unit 7: Pipeline Orchestration, Retries & Dead-Letter Queues**. This page organizes the week's learning materials into four sections:

1. **Instructor Lecture & Conceptual Deep Dive:** Learn how automated pipelines run without human intervention, what our orchestration telemetry and Dead-Letter Queue (DLQ) outputs look like, why simple clock-based schedules fail when upstream steps hang, and how to build idempotent DAG workflows with exponential backoff in Python.
2. **Required Readings & Tutorial Guides:** Explore official documentation from Dagster, Prefect, AWS idempotency engineering guides, and DataOps standards.
3. **Required Micro-Video Lectures (Embedded):** Watch focused video tutorials covering asset DAGs, Dagster orchestration, and scheduling Python pipelines with GitHub Actions.
4. **Institutional Video Lecture Embeds:** Access instructor announcements and lab walkthrough recordings.

*Work through each section in sequence as part of your 150-minute self-study block before starting the applied lab.*

---

## 1. Instructor Lecture & Conceptual Deep Dive

### Automating Data Pipelines So They Run Reliably Every Night

In Units 1 through 6, we built scripts for feature engineering, outlier detection, image preprocessing, text chunking, REST APIs, and MCP agent tools. Up to now, we ran each script by typing `python script.py` in the terminal.

In **Unit 7**, we answer a practical operational question: **how do we run all of these steps automatically on a schedule—and make sure a glitch at 3:00 AM doesn't corrupt the entire database?**

In real production systems, nobody sits at a keyboard at 3:00 AM to run scripts in order. Instead, data engineers use **Pipeline Orchestration** (tools like **Dagster**, **Prefect**, and **GitHub Actions**) to connect pipeline steps into a **Directed Acyclic Graph (DAG)**, make every database write **idempotent** (safe to re-run without creating duplicate rows), recover from temporary network hiccups with **exponential backoff retries**, and isolate corrupted records into a **Dead-Letter Queue (DLQ)**.

```
[1. Ingest Raw Data] ──(Success)──> [2. Clean & Validate] ──> [3. Update Feature & RAG Stores]
         │                                    │
  (Network Glitch)                   (Corrupted Record)
         ▼                                    ▼
[Exponential Backoff Retry]          [Dead-Letter Queue (DLQ)]
```

#### Measurable Learning Objectives
* **Explain** why blind clock-based schedules (`cron`) fail when upstream steps are delayed and how dependency-aware **Directed Acyclic Graphs (DAGs)** prevent cascade failures.
* **Implement** **idempotent** data writes (`<i>f</i>(<i>f</i>(<i>x</i>)) = <i>f</i>(<i>x</i>)`) so re-running a failed job never duplicates rows or double-counts totals.
* **Write** an **exponential backoff retry** wrapper that recovers from temporary network or API timeouts.
* **Route** malformed "poison-pill" records into a **Dead-Letter Queue (`dlq_quarantine.jsonl`)** so valid records continue processing without crashing the batch.
* **Produce** structured pipeline execution heartbeats (`pipeline_heartbeat.json`) for automated monitoring.

---

### What Our Output Looks Like and Where the Data Comes From

#### The Purpose
Our goal in Unit 7 is to build a **Fault-Tolerant Pipeline Orchestrator** that runs our multi-stage data pipeline in strict dependency order and produces three verified outputs:
1. The **Idempotent Curated Dataset** (`curated_batch.parquet`), guaranteed free of duplicate primary keys even if the pipeline is executed three times in a row.
2. A **Dead-Letter Queue Quarantine Log** (`dlq_quarantine.jsonl`) capturing any corrupted input records along with their exact validation error messages and timestamps.
3. A **Pipeline Execution Heartbeat Manifest** (`pipeline_heartbeat.json`) recording the status, duration, row counts, and retry counts of every stage in the DAG.

#### Why Operations Teams Need Heartbeats and Dead-Letter Queues
When an automated pipeline runs overnight, two bad things can happen if you don't engineer defensively:
* **Silent Failure:** A script crashes or processes `0` rows, and nobody notices until dispatchers open a blank dashboard the next morning. Writing a structured `pipeline_heartbeat.json` file after every run gives monitoring tools an immediate check on whether every stage succeeded and how many rows were processed.
* **One Bad Row Crashes 10,000 Good Rows:** If a batch of 10,000 telemetry records contains 3 corrupted records (often called *"poison pills"*), an unguarded script will throw an exception on Row #42 and abort the entire batch. By catching validation errors per record and moving those 3 bad rows into `dlq_quarantine.jsonl`, the 9,997 valid rows finish on time while engineers can inspect the 3 quarantined records at their desk.

#### Where the Raw Data Comes From (Source Systems)
An orchestrated nightly or hourly pipeline pulls from multiple upstream sources that can each experience real-world hiccups:
1. **Remote SFTP / Cloud Object Drop Zones (`incoming_batch.jsonl`):** Raw batches uploaded by partner carriers or terminal gateways, which sometimes contain truncated lines or schema typos.
2. **External Weather & Telematics APIs:** Remote endpoints that occasionally return temporary `503 Service Unavailable` timeouts when network traffic spikes.
3. **Scheduler Triggers (`GitHub Actions` / `Dagster` / `cron`):** Automated timers or webhook events that kick off the pipeline run.

#### Sample Output Dataset (The Target Heartbeat & DLQ Shapes)
When our Unit 7 orchestrator finishes a run, it outputs a structured **Heartbeat Manifest** (`pipeline_heartbeat.json`) and a **Dead-Letter Queue** (`dlq_quarantine.jsonl`):

**1. `output/pipeline_heartbeat.json`:**
```json
{
  "run_id": "run_20261024_0300",
  "pipeline_status": "SUCCESS_WITH_DLQ_WARNINGS",
  "execution_order": [
    "ingest_raw_batch",
    "validate_and_quarantine",
    "upsert_feature_store",
    "refresh_api_cache"
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

### Why Blind Clock Schedules Fail: The 4:30 AM Fuel Card Freeze

To see why we connect pipeline steps into a **dependency graph (DAG)** instead of just scheduling separate scripts on a clock, let's look at a real operational failure.

A freight company had five nightly scripts that prepared their daily fuel fraud report. They scheduled the five scripts in Linux `cron` spaced 30 minutes apart:

```text
03:00 AM -> python 01_download_fuel_logs.py
03:30 AM -> python 02_clean_staging_table.py
04:00 AM -> python 03_compute_driver_averages.py
04:30 AM -> python 04_score_anomalies.py
05:00 AM -> python 05_freeze_flagged_cards.py
```

Look at the hidden assumption: the schedule assumed Step 1 would *always* finish before 3:30 AM!

One Tuesday night at 3:05 AM, the fuel vendor's server was slow, so `01_download_fuel_logs.py` hung waiting for the download.
* At **3:30 AM**, the clock struck 3:30, so `cron` blindly started `02_clean_staging_table.py`—even though Step 1 hadn't finished! Step 2 saw an empty incoming folder and cleared out the staging table.
* At **4:00 AM** and **4:30 AM**, Steps 3 and 4 ran on zero current records, producing distorted Z-scores.
* At **5:00 AM**, Step 5 read the bad output and automatically froze 400 active drivers' fuel cards just as morning shifts were starting.

#### How a Directed Acyclic Graph (DAG) Prevents Cascade Failures
In a **DAG Orchestrator** (like Dagster or Prefect), Step 2 is not triggered by a wall clock—it is triggered **only after Step 1 finishes and passes its data quality check**:
* **Directed:** Every arrow points from an upstream prerequisite to a downstream step (`ingest` &rarr; `clean` &rarr; `score`).
* **Acyclic:** There are no circular loops (`Step A` cannot wait on `Step B` while `Step B` waits on `Step A`).
* **Guardrail:** If `ingest` fails after all retries, the orchestrator stops the pipeline immediately, leaves yesterday's valid table untouched, and sends an alert.

---

### Making Pipelines Safe to Re-Run: Idempotency

What happens when a pipeline crashes halfway through and you run it a second time?

If your script uses a blind `INSERT INTO` or appends rows to the end of a file every time it runs, running it twice for October 24 will **double-count every row** on October 24!

In data engineering, we design every pipeline step to be **idempotent**:
<p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.6rem; border-radius: 4px;">
  <i>f</i>( <i>f</i>(<i>x</i>) ) = <i>f</i>(<i>x</i>)
</p>

In plain English, **idempotency** means: *running a pipeline step once, twice, or ten times on the same input batch leaves the output dataset in the exact same state, with zero duplicate rows.*

#### Compare Non-Idempotent vs. Idempotent SQL
```sql
-- NON-IDEMPOTENT (DANGEROUS): Running this twice creates duplicate rows!
INSERT INTO daily_route_summary
SELECT route_id, driver_id, distance_miles FROM staging_routes;

-- IDEMPOTENT (SAFE): Delete or replace matching primary keys before inserting
DELETE FROM daily_route_summary
WHERE route_id IN (SELECT route_id FROM staging_routes);

INSERT INTO daily_route_summary
SELECT route_id, driver_id, distance_miles FROM staging_routes;
```
Or even simpler in DuckDB when writing a partitioned Parquet output or table with a `PRIMARY KEY`: use `INSERT OR REPLACE INTO` (also called an **Upsert**) or deduplicate on `route_id` before writing!

---

### Handling Glitches: Exponential Backoff vs. Dead-Letter Queues

Not all errors should be handled the same way. A good orchestrator separates errors into two buckets:

| Error Type | Example | What Happens If You Retry Immediately? | Correct Engineering Action |
| :--- | :--- | :--- | :--- |
| **1. Transient Error** (Temporary Glitch) | Weather API returns `503 Server Busy` or network socket times out for 2 seconds | Waiting a moment and trying again usually succeeds! | **Retry with Exponential Backoff** (wait `1s`, then `2s`, then `4s`, up to `max_retries=3`). |
| **2. Permanent Error** ("Poison Pill" Record) | Row #42 has `gallons = -999` or missing `route_id: null` | Retrying 100 times will fail all 100 times because the data itself is invalid! | **Dead-Letter Queue (DLQ)**: Immediately quarantine Row #42 into `dlq_quarantine.jsonl` and keep processing Row #43! |

---

### Step-by-Step Code Ramp-Up: Building Retries, DLQs, Idempotent Upserts, and DAGs

Let's build each of these four patterns in Python from the ground up.

#### Step 1: Writing an Exponential Backoff Retry Helper
Why do we double the wait time (`1s`, `2s`, `4s`—called *exponential backoff*) instead of retrying 100 times per millisecond? Because if a database or API server is momentarily overloaded, hammering it 100 times in a millisecond makes the overload worse!

```python
import time

def run_with_backoff(func, max_retries: int = 3, base_delay_sec: float = 0.1):
    """Runs func(), retrying transient failures with exponential backoff (delay * 2^attempt)."""
    attempt = 0
    while True:
        try:
            return func(), attempt
        except TimeoutError as exc:
            attempt += 1
            if attempt >= max_retries:
                raise RuntimeError(f"Failed after {max_retries} attempts: {exc}") from exc
            wait_time = base_delay_sec * (2 ** (attempt - 1))
            print(f"  [Retry {attempt}/{max_retries}] Transient timeout; waiting {wait_time:.2f}s...")
            time.sleep(wait_time)

# Simulate a flaky API that fails on attempt 1, then succeeds on attempt 2:
call_counter = {"count": 0}
def flaky_weather_api():
    call_counter["count"] += 1
    if call_counter["count"] == 1:
        raise TimeoutError("503 Weather Station Gateway Timeout")
    return {"city": "Cheyenne", "temp_f": 34.0}

result, retries_used = run_with_backoff(flaky_weather_api)
print(f"Success: {result} (retries used: {retries_used})")
```

#### Step 2: Splitting a Batch into Valid Rows and a Dead-Letter Queue (DLQ)
When processing a list of raw records, wrap per-record validation inside a `try ... except` block inside the loop so a single bad record is diverted to `dlq_records` instead of stopping the loop:

```python
import json

raw_batch = [
    {"route_id": 101, "driver_id": 42, "gallons": 125.0},
    {"route_id": 102, "driver_id": 42, "gallons": -30.0},  # Poison pill: negative gallons!
    {"route_id": None, "driver_id": 99, "gallons": 110.0}, # Poison pill: missing route_id!
    {"route_id": 103, "driver_id": 99, "gallons": 140.0},
]

valid_records = []
dlq_records = []

for row in raw_batch:
    try:
        if row.get("route_id") is None or int(row["route_id"]) <= 0:
            raise ValueError("route_id must be a positive integer")
        if float(row.get("gallons", 0)) <= 0:
            raise ValueError("gallons must be strictly positive (> 0)")
        valid_records.append(row)
    except Exception as err:
        dlq_records.append({
            "raw_payload": row,
            "error_reason": str(err)
        })

print(f"Valid rows: {len(valid_records)} | Quarantined in DLQ: {len(dlq_records)}")
```

#### Step 3: Making Database Writes Idempotent in DuckDB (`INSERT OR REPLACE`)
In DuckDB, if you create a table with a `PRIMARY KEY` (such as `route_id INT PRIMARY KEY`), you can use `INSERT OR REPLACE INTO` so re-running the batch updates existing keys in place without ever creating duplicates:

```python
import duckdb

con = duckdb.connect()
con.sql("""
CREATE TABLE curated_routes (
    route_id INT PRIMARY KEY,
    driver_id INT,
    gallons DOUBLE
);
""")

def idempotent_upsert(con, records: list[dict]):
    for r in records:
        con.execute(
            "INSERT OR REPLACE INTO curated_routes VALUES (?, ?, ?)",
            [r["route_id"], r["driver_id"], r["gallons"]]
        )

# Run the exact same upsert 3 times in a row:
idempotent_upsert(con, valid_records)
idempotent_upsert(con, valid_records)
idempotent_upsert(con, valid_records)

# Verify count is still 2 (NOT 6!):
count = con.sql("SELECT COUNT(*) FROM curated_routes").fetchone()[0]
print(f"Row count after 3 identical runs: {count} (100% Idempotent!)")
```

#### Step 4: Running Tasks in Topological DAG Dependency Order
Finally, how does an orchestrator figure out which task to run first when tasks have prerequisites (`dependencies`)? It loops through the tasks and runs any task whose prerequisites have all finished (`all(dep in completed for dep in task_deps)`):

```python
def resolve_dag_order(dag_dependencies: dict[str, list[str]]) -> list[str]:
    """Returns a valid topological execution order for a dictionary of {task: [prereq_tasks]}."""
    completed = []
    while len(completed) < len(dag_dependencies):
        progressed = False
        for task_name, prereqs in dag_dependencies.items():
            if task_name in completed:
                continue
            if all(p in completed for p in prereqs):
                completed.append(task_name)
                progressed = True
        if not progressed:
            raise RuntimeError("Circular dependency or missing task detected in DAG!")
    return completed

dag = {
    "publish_heartbeat": ["upsert_curated_store"],
    "ingest_raw_batch": [],
    "validate_and_dlq": ["ingest_raw_batch"],
    "upsert_curated_store": ["validate_and_dlq"],
}
print("Resolved DAG Order:", resolve_dag_order(dag))
```

Notice that even though `"publish_heartbeat"` was listed first in the dictionary, `resolve_dag_order` automatically ran `['ingest_raw_batch', 'validate_and_dlq', 'upsert_curated_store', 'publish_heartbeat']` in the right order!

---

### Practice Exercises and Common Questions

Try these three exercises in your GitHub Codespaces sandbox (`units/unit_07_orchestration_and_automation/`) before starting the graded lab:

1. **Exercise 1 (Circular Dependency Detection):** Pass `{"task_a": ["task_b"], "task_b": ["task_a"]}` to `resolve_dag_order()` and confirm that it immediately raises a `RuntimeError` instead of hanging forever.
2. **Exercise 2 (Idempotency Proof):** Run `coding_clinic.py` twice in a row and check the output Parquet row count to verify that running the pipeline multiple times produces the exact same number of rows.
3. **Exercise 3 (Inspecting the GitHub Actions Workflow):** Open `.github/workflows/` or review how a `schedule: - cron: '0 3 * * *'` block triggers a Python orchestrator script inside GitHub Actions.

#### Common Questions & Troubleshooting

* **Question 1: Should I retry a `ValidationError` (like `gallons = -50`) using `run_with_backoff`?**  
  *Answer:* No! A `ValidationError` means the data in that row breaks your schema rules. Waiting 2 seconds and checking `-50 > 0` again will still be false. Only retry **transient infrastructure errors** (like `TimeoutError` or `ConnectionError`), and send **data validation errors** straight to the Dead-Letter Queue (DLQ).

* **Question 2: What does the cron expression `'0 3 * * *'` mean?**  
  *Answer:* The five fields in a cron string represent `Minute (0-59)`, `Hour (0-23)`, `Day of Month (1-31)`, `Month (1-12)`, and `Day of Week (0-6)`. So `'0 3 * * *'` means *"At minute 0 of hour 3 (3:00 AM UTC) every day."*

* **Question 3: Why do we write a `pipeline_heartbeat.json` file at the end of a run?**  
  *Answer:* In production, monitoring systems check the timestamp and metrics inside `pipeline_heartbeat.json`. If the timestamp is more than 24 hours old, or if `dlq_records_quarantined` suddenly spikes from `2` to `5,000`, the monitoring system alerts the on-call engineer immediately.

---

## 2. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical references before beginning your applied lab:

1. **[Dagster Official Documentation: Software-Defined Assets (SDA)](https://docs.dagster.io/concepts/assets/software-defined-assets)**
   *Understand declarative asset orchestration, dependency graphs, partitioning, and data lineage.*

2. **[Prefect Documentation: Flows, Tasks & Retries](https://docs.prefect.io/)**
   *Learn how Python decorators turn functions into observable, retryable workflow tasks.*

3. **[AWS Architecture Center: Making Retries Safe with Idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)**
   *Study how exponential backoff, jitter, and idempotency keys prevent duplicate side effects.*

4. **[Dagster Documentation Overview](https://dagster.io/docs)**
   *Explore how asset-based orchestration compares to traditional clock-based task schedulers.*

5. **[The DataOps Manifesto](https://dataopsmanifesto.org/en/)**
   *Review the core principles for automated testing, observability, and reproducible data pipelines.*

---

## 3. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to see asset-based data orchestrators and automated scheduling in action:

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
