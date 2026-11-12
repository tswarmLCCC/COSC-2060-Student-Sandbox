# Unit 2: Asynchronous Preparation & Diagnostic Drills
## The Anomaly Engine & Polars Lazy Window Expressions

> **Time Commitment**: ~60 Minutes (Asynchronous Self-Study)  
> **Prerequisites**: Review of [Unit 2 Required Readings & Concepts](study_guide.md)  
> **Target Mastery**: Eager vs. Lazy execution, SIMD multi-threading, Polars `.over()` window expressions, Isolation Forest bounds.

---

## 1. Readiness Self-Check Checklist
Before attempting the diagnostic drills below, verify you have completed the foundational preparation:
- [ ] Studied the differences between Python GIL-locked loops (`groupby.apply`) and Rust multi-threaded expression engines.
- [ ] Understood why allocating thousands of intermediate DataFrames causes high memory fragmentation and GC pressure.
- [ ] Installed and verified `polars` and `scikit-learn` in your local Python 3.10+ virtual environment.

---

## 2. Part 1: Foundational Concept Checks
Test your conceptual grasp of high-throughput time-series anomaly detection. Formulate your answer first, then click the bar to verify your reasoning against the architectural rationale.

<details>
<summary>Question 1: Why does Pandas df.groupby().apply() scale quadratically on large fleet datasets?</summary>

**Architectural Rationale:**
Pandas `groupby().apply()` splits the primary DataFrame into thousands of distinct sub-DataFrames (one per group), allocates a new Python function call on the interpreter stack for each row partition, and runs sequentially inside the Python Global Interpreter Lock (GIL). 

For a fleet of 10,000 delivery vehicles, this triggers 10,000 function dispatches and creates millions of temporary heap objects, destroying CPU cache locality and ballooning memory consumption.
</details>

<details>
<summary>Question 2: What is the architectural difference between eager and lazy execution in Polars?</summary>

**Architectural Rationale:**
- **Eager Execution (`pl.DataFrame`):** Executes every transformation immediately in RAM line-by-line, allocating intermediate arrays for every step regardless of whether downstream operations discard those columns.
- **Lazy Execution (`pl.LazyFrame`):** Builds a symbolic Directed Acyclic Graph (DAG) of transformations called a Logical Plan. Polars optimizes this plan using predicate pushdown (filtering early) and projection pushdown (loading only necessary columns) before compiling to hardware SIMD instructions when `.collect()` is called.
</details>

<details>
<summary>Question 3: How does the Polars .over('vehicle_id') expression eliminate group splitting?</summary>

**Architectural Rationale:**
In Polars, `.over()` calculates window functions in place across partitioned contiguous columnar memory without physically splitting the table into separate sub-tables. 

It keeps the entire dataset in Apache Arrow contiguous arrays and computes rolling statistics across partitions in parallel using Rayon work-stealing threads, avoiding intermediate object allocation entirely.
</details>

<details>
<summary>Question 4: Why is an Isolation Forest well-suited for multivariate sensor anomaly detection?</summary>

**Architectural Rationale:**
Anomalies are "few and different." An Isolation Forest recursively partitions feature space using random orthogonal splits. 

Because outliers exist in sparse regions of the distribution, they require significantly fewer splits to isolate (they terminate near the root of the tree, resulting in a short average path length `h(x)`). In contrast, inliers require deep tree traversal. This allows the model to score anomalies without requiring labeled failure training sets.
</details>

---

## 3. Part 2: Code Execution Order & Syntax Traces

### Trace Drill 1: Spotting Unnecessary Eager Materialization
Examine the Polars pipeline below designed to process 1,000,000 sensor rows:

```python
import polars as pl

# Ingesting large telemetry parquet
df = pl.read_parquet("sensor_telemetry.parquet")

# Step 1: Eager filter
filtered_df = df.filter(pl.col("vibration_hz") > 0.0)

# Step 2: Eager column addition
result_df = filtered_df.with_columns(
    (pl.col("vibration_hz") * 1.5).alias("scaled_vibration")
)

# Step 3: Select final columns
final_df = result_df.select(["vehicle_id", "timestamp", "scaled_vibration"])
```

<details>
<summary>Analyze the Pipeline: What optimization is lost by using pl.read_parquet instead of pl.scan_parquet?</summary>

**Diagnostic Analysis: PROJECTION & PREDICATE PUSHDOWN MISSED**
By using `pl.read_parquet()`, the script eagerly loads **all columns** of `sensor_telemetry.parquet` into uncompressed RAM before filtering!
- If the file has 30 columns, loading all columns wastes gigabytes of memory.
- **Defensive Optimization**: Use `pl.scan_parquet()`. Polars will inspect the query plan, see that only three columns are ever used (`vehicle_id`, `timestamp`, `vibration_hz`), and push the column projection directly into the Parquet file reader. Unused columns are never read from disk.
</details>

### Trace Drill 2: Partitioned Window Expression Syntax
Examine this Polars expression designed to flag sudden spikes in fuel consumption relative to each driver's rolling baseline:

```python
q = (
    pl.scan_parquet("fuel_logs.parquet")
    .with_columns(
        pl.col("gallons")
        .rolling_mean(window_size=5)
        .over("driver_id")
        .alias("driver_rolling_mean")
    )
)
```

<details>
<summary>Predict the Outcome: What happens if fuel_logs.parquet is not pre-sorted by timestamp before computing the rolling mean?</summary>

**Diagnostic Analysis: NONDETERMINISTIC ROLLING WINDOWS**
The `.rolling_mean()` operation operates sequentially along the row order within each partition defined by `.over("driver_id")`.
- If the telemetry events arrive out-of-order or are stored unsorted on disk, the 5-row rolling window averages arbitrary temporal records (e.g., averaging Monday's fill-up with Thursday's fill-up before Wednesday's)!
- **Defensive Fix**: Always ensure the LazyFrame is sorted temporally before applying rolling windows:
  `.sort(["driver_id", "timestamp"])`
</details>

---

## 4. Architecture Traps & Defensive Rules

<div style="background: #f8fafc; border-left: 4px solid #1e3a8a; padding: 1rem 1.25rem; margin: 1.5rem 0; border-radius: 0 4px 4px 0;">
  <h4 style="margin: 0 0 0.5rem 0; color: #1e3a8a;">The Three Golden Rules of Polars Time-Series Pipelines:</h4>
  <ol style="margin: 0; padding-left: 1.25rem; line-height: 1.7;">
    <li><strong>Scan, Don't Read:</strong> Always initiate file ingestion with <code>pl.scan_parquet()</code> to activate the lazy query optimizer and pushdown pruning.</li>
    <li><strong>Sort Before Rolling:</strong> Rolling window expressions across partitions require explicit ordering: <code>.sort(["partition_key", "timestamp"])</code>.</li>
    <li><strong>Never Fall Back to Python Closures:</strong> Avoid <code>.map_elements()</code> or <code>.apply()</code> in Polars. Use native declarative expressions (<code>pl.when().then().otherwise()</code>) to stay in compiled Rust.</li>
  </ol>
</div>

---

## 5. Preparation for Live In-Class Coding Clinic (Slot 2)
In the upcoming synchronous session, we will execute a live **"I Do, We Do" refactoring clinic**:
- **What to Have Open**: Terminal with Python 3.10+ activated, VS Code, and local Jupyter environment.
- **The Clinic Mission**: We will profile Dr. Marcus Vance's Pandas `groupby.apply` script on 600,000 telemetry rows, observe the single-core CPU bottleneck, and live-code a Polars LazyFrame `.over('vehicle_id')` replacement demonstrating an **18.9x multi-threaded speedup** with exact floating-point parity.
