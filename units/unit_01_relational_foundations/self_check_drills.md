# Unit 1: Asynchronous Preparation & Diagnostic Drills
## The Relational Foundation & Look-Ahead Bias Prevention

> **Time Commitment**: ~60 Minutes (Asynchronous Self-Study)  
> **Prerequisites**: Review of [Unit 1 Required Readings & Concepts](study_guide.md)  
> **Target Mastery**: Temporal event ordering, OLTP vs. OLAP memory layouts, DuckDB `ASOF JOIN` mechanics.

---

## 1. Readiness Self-Check Checklist
Before attempting the diagnostic drills below, verify you have completed the foundational preparation:
- [ ] Studied the filing cabinet vs. drinking straw physical memory mental model (row vs. columnar storage).
- [ ] Grasped the root cause of the $10M logistics delivery delay failure (calendar date join vs. point-in-time timestamp matching).
- [ ] Verified local Python 3.10+ installation with `duckdb` and `pyarrow`.

---

## 2. Part 1: Foundational Concept Checks
Test your conceptual grasp of temporal relational engineering. Formulate your answer first, then click the bar to verify your reasoning against the architectural rationale.

<details>
<summary>Question 1: Why does a standard SQL equality join on date cause look-ahead bias in machine learning?</summary>

**Architectural Rationale:**
A condition like `ON departure::DATE = observation::DATE` matches every event occurring on a calendar day with every sensor observation logged on that same calendar day. 

If a truck departs at **7:15 AM** and a severe blizzard is logged at **5:30 PM**, the equality join attaches the 5:30 PM blizzard to the 7:15 AM departure row. When a model trains on this row, it "learns" from future weather observations that were physically impossible to know at departure time. In production at 7:15 AM, the blizzard has not happened yet, so the model receives clear-sky data and fails.
</details>

<details>
<summary>Question 2: What is the physical memory difference between OLTP (PostgreSQL) and OLAP (DuckDB)?</summary>

**Architectural Rationale:**
- **OLTP (Row-Oriented):** Contiguously stores complete row tuples `[id, name, city, delay, fuel]` on 8KB disk pages. Fetching a single customer record is lightning fast, but calculating `AVG(delay)` over 10 million rows requires loading 100% of all table bytes into RAM, discarding 80% of unused columns.
- **OLAP (Column-Oriented):** Contiguously stores each attribute in separate columnar arrays `[delay_1, delay_2, delay_3, ...]`. Computing `AVG(delay)` requires streaming **only** the `delay` column into CPU cache lines, enabling hardware SIMD (Single Instruction, Multiple Data) vectorization with zero I/O waste.
</details>

<details>
<summary>Question 3: In an ASOF JOIN, what happens if an event occurs before the earliest observation?</summary>

**Architectural Rationale:**
In DuckDB, `ASOF JOIN` searches for the maximum right-hand timestamp that is $\le$ the left-hand timestamp. If a vehicle departs at 05:00 AM and the earliest weather observation logged in the database is at 06:00 AM, there is no historical observation satisfying `05:00 >= obs_time`. 

DuckDB returns `NULL` for all columns originating from the right-hand table. Production pipelines must defensively handle these NULLs using `COALESCE` with domain-appropriate physical defaults (e.g., normal road conditions, 0.0 rain) or forward imputation.
</details>

<details>
<summary>Question 4: Why is DuckDB referred to as an "in-process" analytical engine?</summary>

**Architectural Rationale:**
Unlike client-server database systems (PostgreSQL, MySQL, Snowflake) that require running a separate daemon process, managing network sockets, and serializing query results over TCP, DuckDB runs directly inside your Python runtime process (like SQLite). 

It operates directly on shared memory buffers (Apache Arrow / NumPy arrays) with zero network overhead and zero memory duplication.
</details>

---

## 3. Part 2: Code Execution Order & Syntax Traces

### Trace Drill 1: Identifying the Leakage Vector
Examine the SQL query below intended to prepare training features for an airline arrival delay model:

```sql
SELECT 
    f.flight_id,
    f.scheduled_departure,
    m.maintenance_code,
    f.arr_delay_mins
FROM flights f
LEFT JOIN maintenance_events m
  ON f.tail_number = m.tail_number
WHERE m.event_time <= f.actual_arrival;
```

<details>
<summary>Analyze the Query: Does this query prevent look-ahead bias? Explain why or why not.</summary>

**Diagnostic Analysis: CRITICAL LEAKAGE BUG**
The filter `WHERE m.event_time <= f.actual_arrival` is a catastrophic look-ahead leak!
- The prediction target is `arr_delay_mins`, which must be predicted **before or at departure time** (`scheduled_departure`).
- Filtering by `<= f.actual_arrival` allows maintenance events that occurred **in-flight** (or during arrival taxiing) to enter the feature set.
- **Defensive Fix**: Change the temporal constraint to `WHERE m.event_time <= f.scheduled_departure` and rank by `event_time DESC` (or use DuckDB `ASOF JOIN`).
</details>

### Trace Drill 2: Rolling Window Lag Boundaries
Examine this window feature calculation designed to compute a driver's prior safety record:

```sql
SELECT 
    trip_id,
    driver_id,
    dep_time,
    AVG(hard_braking_events) OVER (
        PARTITION BY driver_id 
        ORDER BY dep_time
        ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
    ) AS driver_risk_score
FROM driver_telemetry;
```

<details>
<summary>Spot the Bug: What architectural error exists in the window frame specification?</summary>

**Diagnostic Analysis: CURRENT ROW CONTAMINATION**
- The frame `ROWS BETWEEN 3 PRECEDING AND CURRENT ROW` includes the current trip's `hard_braking_events` in the risk score feature!
- At departure time, the current trip has not occurred yet, meaning the current trip's driving behavior cannot be known. Including `CURRENT ROW` leaks the outcome into the input features.
- **Defensive Fix**: The frame MUST be:
  `ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING`
  This guarantees that only strictly completed prior trips inform the feature calculation.
</details>

---

## 4. Architecture Traps & Defensive Rules

<div style="background: #f8fafc; border-left: 4px solid #1e3a8a; padding: 1rem 1.25rem; margin: 1.5rem 0; border-radius: 0 4px 4px 0;">
  <h4 style="margin: 0 0 0.5rem 0; color: #1e3a8a;">The Three Golden Rules of Point-in-Time Joins:</h4>
  <ol style="margin: 0; padding-left: 1.25rem; line-height: 1.7;">
    <li><strong>The Cutoff Rule:</strong> Every feature row has an immutable cutoff timestamp ($t_{\text{cutoff}}$). Any data point logged at $t > t_{\text{cutoff}}$ is toxic waste and must be mathematically excluded.</li>
    <li><strong>The Preceding Rule:</strong> Rolling feature windows must terminate at <code>1 PRECEDING</code>, never <code>CURRENT ROW</code>.</li>
    <li><strong>The Coalesce Rule:</strong> Always wrap right-table fields in <code>COALESCE</code> to defend downstream ML estimators from unhandled NULLs caused by pre-observation departures.</li>
  </ol>
</div>

---

## 5. Preparation for Live In-Class Coding Clinic (Slot 2)
In the upcoming synchronous session, we will execute a live **"I Do, We Do" refactoring clinic**:
- **What to Have Open**: Terminal with Python 3.10+ activated, VS Code, and local Jupyter environment.
- **The Clinic Mission**: We will inspect Dr. Elena Rostova's naive Pandas `merge_asof` prototype, profile its single-core CPU bottleneck on 300,000 records, and live-code a vectorized DuckDB `ASOF LEFT JOIN` replacement yielding a **4.4x speedup** with 100% mathematical output parity.
