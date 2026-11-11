# Unit 1: Required Readings, Concepts & Video Lectures

Welcome to the core instructional lecture and study hub for **Unit 1: The Relational Foundation & Supervised Learning Targets**. This page organizes all weekly learning materials into four structured chapters:

1. **Instructor Lecture & Conceptual Deep Dive:** Master the physical memory layout, look-ahead bias mechanics, window lagging, and point-in-time `ASOF JOIN` syntax authored specifically for this unit.
2. **Required Readings & Authoritative Tutorial Guides:** Study curated official documentation and engineering deep-dives from DuckDB, Apache Arrow, and columnar data architecture sources.
3. **Required Micro-Video Lectures (Embedded):** Watch high-definition video chapters with verified timestamp navigation to observe columnar execution and temporal joins in live environments.
4. **Institutional Video Lecture Embeds:** Access campus-specific video recordings and announcements uploaded by your instructor.

*Work through each section in sequence as part of your 150-minute asynchronous self-study allocation before starting the applied laboratory assignment.*

---

## 1. Instructor Lecture & Conceptual Deep Dive

### Asking Questions of Temporal Data: Relational Foundations for AI

#### 1. Unit Overview & Objectives
Welcome to **COSC 2060: Modern Data Engineering & AI Infrastructure**. 

In your introductory machine learning coursework, you were provided a clean, static, single-table flat CSV file (like Iris, Titanic, or California Housing). You split data into $X$ (features) and $y$ (target labels), called `model.fit(X_train, y_train)`, evaluated test accuracy, and plotted ROC curves.

In your introductory SQL coursework, you queried normalized transactional databases. You wrote `SELECT`, `WHERE`, `ORDER BY`, and standard `INNER JOIN` statements to generate human-readable invoices and management reports.

**This unit is the bridge between those two disciplines.**

In production AI systems, clean flat CSVs do not exist. Real enterprise data lives in normalized transactional tables that are continually modified by live operations. If you naively join those tables using basic SQL equality joins, you will commit the cardinal sin of machine learning data engineering: **temporal data leakage** (also known as *look-ahead bias*). Your model will achieve 99% accuracy in your notebook, but will fail catastrophically the moment it is deployed to live production.

By the end of this unit, you will master the art of transforming raw transactional databases into leak-free machine learning feature matrices using modern columnar analytical SQL.

**Measurable Learning Objectives:**
* **Differentiate** between row-oriented OLTP database architectures (e.g., PostgreSQL) and columnar-oriented OLAP engines (e.g., DuckDB, Apache Arrow) in terms of disk I/O, cache line utilization, and analytical scan performance.
* **Identify and Diagnose** temporal data leakage and look-ahead bias in multi-table relational joins.
* **Construct** point-in-time joins using DuckDB's native `ASOF JOIN` syntax to guarantee zero future data leaks into historical feature rows.
* **Implement** defensive rolling window aggregations and lag features using SQL window functions (`PARTITION BY`, `ORDER BY`, `ROWS BETWEEN N PRECEDING AND 1 PRECEDING`).
* **Generate** a production-ready, flat 2D feature matrix ($X, y$) from raw, messy relational logistics tables.

---

#### 2. The Narrative of Data: Why the $10M Delivery Model Failed
To understand why data engineering is a distinct discipline from both software development and data science, consider an authentic industry failure.

A national freight logistics carrier employed hundreds of drivers moving freight between major distribution hubs. They wanted to predict whether a scheduled shipment would experience a severe delivery delay (`delivery_delay_mins > 30`) so dispatchers could reroute cargo proactively.

The company hired a machine learning scientist. The scientist opened a Jupyter notebook, connected to the company's PostgreSQL database, and wrote a standard SQL query:

```sql
-- NAIVE, CATASTROPHIC SQL QUERY (DO NOT USE IN PRODUCTION)
SELECT 
    r.route_id,
    r.driver_id,
    r.origin_city,
    r.dep_time::DATE AS route_date,
    r.distance_miles,
    w.precipitation_in,
    w.visibility_miles,
    w.road_condition,
    r.delivery_delay_mins AS target_delay
FROM routes r
LEFT JOIN weather_observations w
  ON r.origin_city = w.city
 AND r.dep_time::DATE = w.obs_time::DATE;
```

The scientist trained an XGBoost model on this dataset. The results were astounding: **99.4% ROC-AUC score**. The executive team was thrilled and deployed the model to live dispatch.

##### The Catastrophic Deployment Failure
On day one of live operation, the model's accuracy collapsed to **51%**—no better than flipping a coin. Shipments were delayed across the country, warehouses were left unstaffed, and the company lost an estimated $10 million in contractual service level penalties.

What happened?

Look closely at the join condition:
```sql
ON r.origin_city = w.city AND r.dep_time::DATE = w.obs_time::DATE
```

Truck #104 departed Chicago at **7:15 AM** on a sunny morning. At **5:30 PM** that afternoon, a sudden severe blizzard struck Chicago, dumping 6 inches of snow. The weather monitoring station logged `precipitation_in = 6.0` and `road_condition = 'Snow/Ice'` at 6:00 PM.

Because the query joined purely on the **calendar date** (`dep_time::DATE = obs_time::DATE`), the evening blizzard data was attached to the morning truck's departure record. When the model was being trained, it looked at Truck #104 and saw "6 inches of snow at origin" and correctly learned that snow equals delays. 

In the real world at **7:15 AM**, that blizzard had not happened yet. The live model at departure time only had access to the 7:00 AM reading ("Clear skies, dry roads"). The model had been trained on the future.

```
REALITY TIMELINE:
06:00 AM ── Weather Observation: "Clear skies, dry roads"
07:15 AM ── Truck #104 Departs Chicago  <── LIVE INFERENCE TAKES PLACE HERE!
12:00 PM ── Truck #104 is 300 miles away
05:30 PM ── Severe Blizzard hits Chicago!
06:00 PM ── Weather Observation: "Blizzard, 6 inches snow, road closed"

WHAT NAIVE SQL JOIN DID:
Attached the 06:00 PM Blizzard to the 07:15 AM Departure! (LOOK-AHEAD BIAS)
```

This is **look-ahead bias** (temporal data leakage). A machine learning model will ruthlessly exploit any hint from the future if you feed it to it during training. As a data engineer, your primary responsibility is defensive: **you must construct data pipelines that mathematically prevent future knowledge from leaking into past events.**

---

#### 3. The Physical Mental Model: Row Filing vs. Columnar Straws
In your introductory SQL course, you used **PostgreSQL**. In this course, we introduce **DuckDB** and **Apache Arrow**. Why?

To understand the difference, consider how data is stored physically on your computer's storage drive (SSD or NVMe) and in RAM:

```
TABLE: routes (route_id INT, driver_id INT, origin_city VARCHAR, distance_miles DOUBLE, delay_mins DOUBLE)

1. ROW-ORIENTED (OLTP - PostgreSQL / SQLite):
[route_id, driver_id, origin_city, distance_miles, delay_mins] [route_id, driver_id, origin_city, distance_miles, delay_mins] ...
- Physical Layout: Tuples are stored contiguously on disk pages.
- Ideal Workload: Fetching or inserting a single complete customer record (OLTP).
- The Bottleneck: An analytical aggregation like AVG(delay_mins) must read 100% of the entire table from disk into RAM, discarding 80% of the bytes.

2. COLUMN-ORIENTED (OLAP - DuckDB / Parquet / Apache Arrow):
[delay_mins_1, delay_mins_2, delay_mins_3, ...] [distance_1, distance_2, distance_3, ...]
- Physical Layout: Each column is stored contiguously in memory chunks.
- Ideal Workload: Scanning, filtering, and aggregating specific feature columns over millions of rows.
- The Advantage: To compute AVG(delay_mins), the engine reads ONLY that column. Vectorized CPU instructions (SIMD) process thousands of values per clock cycle.
```

##### The "Filing Cabinet vs. Drinking Straw" Analogy
* **Row-Store (PostgreSQL):** Imagine a warehouse of 10,000 filing folders. Each folder contains all details about one shipment (driver, vehicle, origin, fuel, delay). If your manager asks: *"What is our average delay?"*, you must walk to every single cabinet, pull out every folder, flip past 15 pages of driver info, read the delay number, and put the folder back.
* **Column-Store (DuckDB):** Imagine 5 long drinking straws. One straw contains only route IDs; another contains only delay numbers. To answer the manager's question, you pick up the "delay numbers" straw and dump all numbers directly onto the calculator. You never touch, load, or pay I/O costs for the other attributes.

DuckDB executes analytical queries 10x to 100x faster than traditional row engines on single-node laptops because it operates in-memory using **vectorized execution** over columnar data chunks.

---

#### 4. Defensive Query Evolution: From Leakage to Native ASOF JOIN
How do we solve the temporal leakage problem in SQL? Let's trace the engineering progression through three concrete steps.

##### Step 1: The Failed Naive Join
When joining an event table (`routes`) to an observation table (`weather`), a naive `JOIN ... ON date = date` leaks evening observations into morning departures:
```sql
-- DANGEROUS: Leaks future weather into morning departures
SELECT 
    r.route_id,
    r.dep_time,
    w.obs_time,
    w.precipitation_in
FROM routes r
JOIN weather_observations w
  ON r.origin_city = w.city
 AND r.dep_time::DATE = w.obs_time::DATE;
```

##### Step 2: The Window Function Workaround (Standard SQL)
Before modern engines introduced temporal primitives, data engineers had to write complex window functions with strict lookback boundaries:
```sql
-- DEFENSIVE SQL USING WINDOW FUNCTIONS (PREVENTS LOOK-AHEAD BIAS)
WITH ranked_weather AS (
    SELECT 
        r.route_id,
        r.dep_time,
        w.obs_time,
        w.precipitation_in,
        ROW_NUMBER() OVER (
            PARTITION BY r.route_id 
            ORDER BY w.obs_time DESC
        ) AS rank_order
    FROM routes r
    JOIN weather_observations w
      ON r.origin_city = w.city
     AND w.obs_time <= r.dep_time  -- STRICT TEMPORAL BOUNDARY
)
SELECT route_id, dep_time, obs_time, precipitation_in
FROM ranked_weather
WHERE rank_order = 1;
```
*Why this works:* The condition `w.obs_time <= r.dep_time` guarantees that no weather record recorded after the truck left can ever enter the candidate set. Sorting `w.obs_time DESC` and taking `rank_order = 1` extracts the *latest known observation prior to departure*.  
*The Limitation:* On large tables, computing a cross-join followed by a window sort over millions of partitions consumes immense RAM and CPU time.

##### Step 3: DuckDB's Native `ASOF JOIN`
DuckDB provides native support for **ASOF joins**—a specialized physical operator engineered specifically for point-in-time event matching:

```sql
-- PRODUCTION DUCKDB ASOF JOIN: ELEGANT, DEFENSIVE, VECTORIZED
SELECT 
    r.route_id,
    r.driver_id,
    r.origin_city,
    r.dep_time,
    w.obs_time AS weather_obs_time,
    w.precipitation_in,
    w.visibility_miles,
    w.road_condition,
    r.delivery_delay_mins AS target_delay
FROM routes r
ASOF JOIN weather_observations w
  ON r.origin_city = w.city
 AND r.dep_time >= w.obs_time;
```

* **How `ASOF JOIN` Operates:** For every route departure on the left, DuckDB searches the weather observations on the right that match the exact equality condition (`r.origin_city = w.city`) and picks the single row with the **maximum `obs_time` that is less than or equal to `r.dep_time`**.
* **Zero Temporal Leakage:** Because `r.dep_time >= w.obs_time`, it is mathematically impossible for an observation recorded at 6:00 PM to attach to a 7:15 AM departure.
* **Engine Performance:** Instead of building a massive Cartesian product and sorting window partitions, DuckDB uses a parallelized merge-join algorithm that scans pre-sorted columnar buffers in a single pass.

---

#### 5. Guided End-to-End Implementation Walkthrough (Python + DuckDB)
Here is how you execute this defensive pipeline in Python using DuckDB's zero-copy relational API:

```python
import duckdb
import datetime

# 1. Connect to an in-memory DuckDB instance
con = duckdb.connect(database=":memory:")

# 2. Create the routes table (events requiring prediction)
con.execute("""
CREATE TABLE routes (
    route_id INT,
    origin_city VARCHAR,
    dep_time TIMESTAMP,
    delivery_delay_mins INT
);
INSERT INTO routes VALUES
(101, 'Chicago', '2026-10-24 07:15:00', 12),
(102, 'Chicago', '2026-10-24 18:30:00', 85);
""")

# 3. Create the weather observations table (sensor logs)
con.execute("""
CREATE TABLE weather_observations (
    city VARCHAR,
    obs_time TIMESTAMP,
    precipitation_in DOUBLE,
    road_condition VARCHAR
);
INSERT INTO weather_observations VALUES
('Chicago', '2026-10-24 06:00:00', 0.0, 'Dry'),
('Chicago', '2026-10-24 12:00:00', 0.1, 'Wet'),
('Chicago', '2026-10-24 17:30:00', 4.5, 'Blizzard');
""")

# 4. Execute the defensive ASOF join
feature_matrix = con.execute("""
SELECT 
    r.route_id,
    r.origin_city,
    r.dep_time,
    w.obs_time AS matched_weather_time,
    w.precipitation_in,
    w.road_condition,
    r.delivery_delay_mins
FROM routes r
ASOF JOIN weather_observations w
  ON r.origin_city = w.city
 AND r.dep_time >= w.obs_time
ORDER BY r.route_id;
""").fetchdf()

print(feature_matrix)
```

**Verification Output:**
```
   route_id origin_city            dep_time matched_weather_time  precipitation_in road_condition  delivery_delay_mins
0       101     Chicago 2026-10-24 07:15:00  2026-10-24 06:00:00               0.0            Dry                   12
1       102     Chicago 2026-10-24 18:30:00  2026-10-24 17:30:00               4.5       Blizzard                   85
```

Notice that Route 101 (departed 07:15) was matched with the 06:00 observation (Dry, 0.0" rain), while Route 102 (departed 18:30) was matched with the 17:30 observation (Blizzard, 4.5" rain). The temporal boundaries are mathematically sound.

---

#### 6. Common Traps & Formative Self-Check FAQ

* **Question 1: What happens if there is no weather observation prior to a route departure?**  
  *Answer:* If a truck departs at 5:00 AM and the earliest sensor observation in the database is at 6:00 AM, DuckDB returns `NULL` for all columns originating from the right-hand table (`matched_weather_time`, `precipitation_in`, etc.). In your ML pipeline, you must handle these NULLs using backward imputation or default sentinel values.

* **Question 2: Can I use the shorthand `USING` syntax for ASOF joins?**  
  *Answer:* Yes, but remember DuckDB's rule: **the last column listed in the `USING` clause is always treated as the temporal inequality (`>=`)**, and all preceding columns require exact equality (`=`). For example: `ASOF JOIN weather USING (city, timestamp);`.

* **Question 3: Why shouldn't I just use `LAG()` over the entire table?**  
  *Answer:* The `LAG()` window function requires rows to be strictly ordered in an identical sequence. If sensor observations arrive at irregular intervals (e.g., every 15 minutes during storms, every 2 hours during clear skies), `LAG(1)` does not guarantee a fixed time window. `ASOF JOIN` matches by continuous physical timestamp regardless of arrival intervals.

---

## 2. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical specifications before beginning your applied lab:

1. **[DuckDB Official Documentation: ASOF JOIN Query Syntax](https://duckdb.org/docs/sql/query_syntax/asof_join)**
   *Understand the formal syntax specifications, inequality operators, equality constraints, and NULL match behaviors for DuckDB's native point-in-time join engine.*

2. **[DuckDB Engineering Blog: Fuzzy Temporal Lookups](https://duckdb.org/2023/09/15/asof-join-fuzzy-temporal-lookups.html)**
   *Study the architectural internals of how DuckDB plans and executes ASOF joins using parallelized merge pipelines instead of expensive Cartesian products.*

3. **[Apache Arrow In-Memory Columnar Format](https://arrow.apache.org/overview/)**
   *Learn how modern analytical engines organize columnar buffers in physical RAM to enable zero-copy data transfer and SIMD hardware acceleration.*

4. **[DuckDB Parquet Ingestion & Pushdown Optimization](https://duckdb.org/docs/data/parquet/overview)**
   *Discover how columnar queries achieve 100x performance gains by reading Parquet files directly from disk while skipping irrelevant columns and byte ranges.*

5. **[DuckDB Window Functions Reference](https://duckdb.org/docs/sql/window_functions)**
   *Review the complete syntax for SQL analytical window frames (`PARTITION BY`, `ORDER BY`, `ROWS BETWEEN N PRECEDING AND 1 PRECEDING`) used for defensive lag engineering.*

---

## 3. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to observe columnar data engines and temporal joins executed in live engineering environments:

### DuckDB in 100 Seconds <span style="font-size: 0.9em; color: #64748b;">(Full Video - 2:12)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="DuckDB in 100 Seconds" src="https://www.youtube.com/embed/uHm6FEb2Re4" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=uHm6FEb2Re4" target="_blank" rel="noopener">Open video segment in new tab (2:12)</a></p>

### Row vs. Column Storage Models & Compression <span style="font-size: 0.9em; color: #64748b;">(Starts at 15:20)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Row vs Column Storage Models - CMU Database Group" src="https://www.youtube.com/embed/5gXn5fLkbM0?start=920" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=5gXn5fLkbM0&amp;t=920s" target="_blank" rel="noopener">Open video segment in new tab (15:20)</a></p>

### SQL ASOF Join Tutorial in DuckDB & Snowflake <span style="font-size: 0.9em; color: #64748b;">(Full Walkthrough - 8:45)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="SQL ASOF Join Tutorial" src="https://www.youtube.com/embed/zy89zKipsQg" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=zy89zKipsQg" target="_blank" rel="noopener">Open video segment in new tab (8:45)</a></p>

### Feature Engineering: Point-in-Time Correctness & Avoiding Data Leakage <span style="font-size: 0.9em; color: #64748b;">(Full Video - 11:30)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Feature Engineering and Point in Time Correctness" src="https://www.youtube.com/embed/T1dJfh1KlYA" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=T1dJfh1KlYA" target="_blank" rel="noopener">Open video segment in new tab (11:30)</a></p>

---

## 4. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for this unit will appear in this designated container.</p>
</div>
