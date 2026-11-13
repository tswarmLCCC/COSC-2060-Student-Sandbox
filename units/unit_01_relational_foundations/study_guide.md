# Unit 1: Required Readings, Concepts & Video Lectures

Welcome to the core instructional lecture and study hub for **Unit 1: The Relational Foundation & Supervised Learning Targets**. This page organizes all weekly learning materials into five structured sections:

1. **Unit Overview & Objectives:** Review the architectural context and measurable learning objectives for this unit.
2. **Instructor Lecture & Conceptual Deep Dive (Ribbon Slices 2a–2h):** Master the target feature matrix format, operational source systems, bottom-up SQL feature engineering, supervised learning mechanics, physical columnar memory layouts, look-ahead bias, window lagging, and point-in-time `ASOF JOIN` syntax authored specifically for this unit.
3. **Required Readings & Authoritative Tutorial Guides:** Study curated official documentation and engineering deep-dives from DuckDB, Apache Arrow, and columnar data architecture sources.
4. **Required Micro-Video Lectures (Embedded):** Watch high-definition video chapters with verified timestamp navigation to observe columnar execution and temporal joins in live environments.
5. **Institutional Video Lecture Embeds:** Access campus-specific video recordings and announcements uploaded by your instructor.

*Work through each section in sequence as part of your 150-minute asynchronous self-study allocation before starting the applied laboratory assignment.*

---



## 1. Unit Overview & Objectives
Welcome to **COSC 2060: Modern Data Engineering & AI Infrastructure**.

When most people first see machine learning or data science examples, they are handed a clean, static, single-table flat CSV file (like Iris, Titanic, or California Housing). They split that pre-made file into <b><i>X</i></b> (features) and <b><i>y</i></b> (target labels), call `model.fit(X_train, y_train)`, and evaluate test accuracy.

In your introductory SQL coursework (**CMAP 1815**), you queried normalized transactional databases. You wrote `SELECT`, `WHERE`, `GROUP BY`, `ORDER BY`, and standard `INNER JOIN` or `LEFT JOIN` statements to generate human-readable invoices, inventory summaries, and management reports.

**This unit is the bridge between those two worlds.**

In production AI systems, clean flat CSVs do not magically exist on a hard drive waiting to be modeled. Real enterprise data lives in normalized transactional tables and sensor streams that are continually modified by live operations. Before any machine learning model can be trained or run in production, a **data engineer** must design and build the pipeline that transforms those raw operational tables into a clean, structured **feature matrix**.

Even more importantly, when you write a SQL query for a human manager, a human can spot an obvious anomaly on a report. When you build a dataset for an algorithm, the model trusts every number blindly. If you naively join operational tables using basic SQL equality joins, you will commit the cardinal sin of machine learning data engineering: **temporal data leakage** (also known as *look-ahead bias*). Your model will achieve 99% accuracy in your notebook, but will fail catastrophically the moment it is deployed to live production.

We will build everything from the ground up. First, we will examine the exact shape of the output dataset we are trying to build this week and the source systems where the raw data originates. Next, we will learn how to engineer features in SQL step by step, how supervised learning uses those columns, why temporal data leakage happens, how columnar databases like **DuckDB** and **Apache Parquet** work under the hood, and how to write defensive window functions and `ASOF JOIN` queries in Python.

**Measurable Learning Objectives:**
* **Describe** the structure of a flat 2D feature matrix (<b><i>X</i></b> input features and <b><i>y</i></b> target labels) and trace how raw records flow from operational source systems into an analytical dataset.
* **Construct** foundational SQL features from the ground up using arithmetic expressions, `CASE WHEN` indicator flags, `LEFT JOIN` lookups, and partitioned window functions.
* **Differentiate** between row-oriented OLTP database architectures (e.g., PostgreSQL) and columnar-oriented OLAP engines (e.g., DuckDB, Apache Arrow, Apache Parquet) in terms of disk I/O, cache line utilization, and analytical scan performance.
* **Identify and Diagnose** temporal data leakage and look-ahead bias in multi-table relational joins.
* **Construct** point-in-time joins using DuckDB's native `ASOF JOIN` syntax to guarantee zero future data leaks into historical feature rows.
* **Implement** defensive rolling window aggregations and lag features using SQL window functions (`PARTITION BY`, `ORDER BY`, `ROWS BETWEEN N PRECEDING AND 1 PRECEDING`).

---

## 2a. What Our Output Table Looks Like and Where the Data Comes From

Before writing a single line of SQL or Python, a data engineer always starts by answering two questions: **What does the finished dataset need to look like?** and **Which source systems hold the raw ingredients?**

### The Purpose
Our goal in Unit 1 is to build a **Flat Tabular Feature Matrix** saved as a `feature_matrix.parquet` file. Specifically, we are helping a national freight logistics company (**Apex Logistics**) predict how many minutes late a delivery truck will arrive (`target_delay_mins`) **at the exact moment the truck is getting ready to depart its origin terminal**.

### Why Models Need a Single Flat Table
In an operational database, data is normalized across many separate tables (drivers, routes, weather stations) so information isn't duplicated. However, standard machine learning algorithms (such as linear regression, random forests, and gradient-boosted decision trees like XGBoost) cannot browse across multiple database tables or follow foreign keys on their own.

Instead, a supervised learning model requires a **single, flat two-dimensional grid**:
* **Every row** represents one specific decision point in time (one scheduled truck departure).
* **Every input column (called a feature, grouped together as <i>X</i>)** is a numeric or categorical measurement that was already known *at or before* the moment that truck left the terminal.
* **The final column (called the target label, written as <i>y</i>)** is the actual historical outcome we want the model to learn to predict (`target_delay_mins`).

### Where the Raw Data Comes From (Source Systems)
In a real freight company, the raw data does not sit in one neat file. It arrives from three separate operational systems that record events on completely different schedules:

1. **Human Resources & Fleet Registry Database (`drivers` table):** Updated occasionally by HR staff when drivers are hired or complete annual safety inspections. Stores `driver_id`, `hire_date`, `safety_score`, and `vehicle_type`.
2. **Dispatch Operational Database (`routes` table):** Updated by terminal dispatch software whenever a shipment is scheduled, departs (`dep_time`), and reaches its destination (`act_arrival`, `delivery_delay_mins`).
3. **External Weather Sensor Stream (`weather_observations` table):** Automated weather station telemetry (`obs_time`, `precipitation_in`, `visibility_miles`, `wind_speed_mph`, `road_condition`) pulled from NOAA airport weather stations. Weather stations do not know when trucks depart; they simply log an observation on their own schedule (every hour, or whenever storm conditions change rapidly).

### Sample Output Dataset (The Target Shape)
When our Unit 1 pipeline finishes combining, lagging, and cleaning those three sources, the finished output table looks like this:

| route_id (ID) | dep_hour (<i>X</i><sub>1</sub>) | distance_miles (<i>X</i><sub>2</sub>) | safety_score (<i>X</i><sub>3</sub>) | driver_prior_avg_delay (<i>X</i><sub>4</sub>) | precipitation_in (<i>X</i><sub>5</sub>) | visibility_miles (<i>X</i><sub>6</sub>) | road_condition (<i>X</i><sub>7</sub>) | target_delay_mins (<i>y</i>) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **101** | 6 | 102.5 | 0.98 | 0.0 | 0.00 | 10.0 | Dry | **15** |
| **102** | 14 | 102.5 | 0.98 | 15.0 | 0.10 | 6.0 | Wet | **45** |
| **103** | 7 | 345.0 | 0.85 | 0.0 | 0.00 | 10.0 | Dry | **0** |
| **104** | 9 | 178.0 | 0.92 | 0.0 | 0.25 | 4.0 | Wet | **20** |
| **105** | 6 | 102.5 | 0.98 | 30.0 | 0.00 | 10.0 | Dry | **5** |
| **106** | 18 | 215.0 | 0.79 | 12.5 | 0.90 | 1.2 | Snow/Ice | **85** |

> **Companion Reference:** Whenever you want to compare this flat tabular matrix with the other five data shapes we will build across the course (unsupervised time-series matrices, 3D image tensors, RAG text chunks, Pydantic API contracts, and MCP JSON-RPC schemas), open **The Shapes of AI Data: A Companion Guide** in the *Getting Started - Course Orientation* module.

---

## 2b. Building Features in SQL from the Ground Up

Before we talk about advanced joins or data leakage, let's start at the beginning: **What is a feature, and how do we build features using SQL?**

A **feature** is simply a measurable clue—stored as a column in our table—that helps a model estimate an outcome. **Feature engineering** is the craft of using domain knowledge and SQL (or Python) to turn raw operational columns (like timestamps, distances, and historical logs) into informative numbers.

If you know how to write a basic `SELECT` query from CMAP 1815, you already know the foundation of feature engineering. Let's walk through the four primary ways data engineers build features in SQL, starting with the simplest.

### 1. Extracting Numbers from Timestamps and Arithmetic Ratios
Raw timestamps like `'2026-10-12 07:30:00'` are difficult for a mathematical model to compare directly, because every calendar date only happens once. However, the **hour of the day** (`7` for 7:00 AM rush hour) or the **day of the week** repeats every week and strongly predicts traffic congestion. We can also combine numeric columns using simple arithmetic:

```sql
SELECT
    route_id,
    dep_time,
    -- Extract the hour of departure (0 to 23) as a numeric feature
    EXTRACT(HOUR FROM dep_time) AS dep_hour,
    -- Extract day of week (0 = Sunday ... 6 = Saturday)
    EXTRACT(DOW FROM dep_time) AS dep_day_of_week,
    distance_miles,
    -- Compute an estimated driving time feature assuming a 55 mph highway average
    ROUND(distance_miles / 55.0, 2) AS est_drive_hours
FROM routes;
```

### 2. Creating Yes/No Indicator Flags with `CASE WHEN`
Often we want to highlight a specific operational threshold—such as whether a trip departs during peak morning rush hour or whether a route is a long-haul trip over 250 miles. In SQL, we turn conditions into `1` (True) and `0` (False) using `CASE WHEN`:

```sql
SELECT
    route_id,
    distance_miles,
    CASE
        WHEN EXTRACT(HOUR FROM dep_time) BETWEEN 7 AND 9 THEN 1
        ELSE 0
    END AS is_morning_rush,
    CASE
        WHEN distance_miles >= 250.0 THEN 1
        ELSE 0
    END AS is_long_haul
FROM routes;
```

### 3. Attaching Static Entity Attributes with `LEFT JOIN`
Our `routes` table only records `driver_id`. To include features about the driver's safety record or truck class, we join the `drivers` table using a `LEFT JOIN`:

```sql
SELECT
    r.route_id,
    r.driver_id,
    r.distance_miles,
    COALESCE(d.safety_score, 0.85) AS safety_score,
    COALESCE(d.vehicle_type, 'Standard_Semi') AS vehicle_type
FROM routes r
LEFT JOIN drivers d
  ON r.driver_id = d.driver_id;
```

Why do data engineers use `LEFT JOIN` with `COALESCE` instead of `INNER JOIN`? Because `routes` is our primary event table. If a newly hired driver's record hasn't synced from HR yet, an `INNER JOIN` would silently delete that route row from the dataset. A `LEFT JOIN` preserves every route row, and `COALESCE` replaces any missing `NULL` value with a safe baseline default (`0.85`).

### 4. Summarizing Past Behavior with SQL Window Functions (`OVER`)
What if we want a feature that captures a driver's recent track record—for example, their average delay across their previous 3 trips?

In CMAP 1815, you used `GROUP BY driver_id` to collapse a table into one summary row per driver. When building a feature matrix, however, we cannot collapse the rows—we need one row per route, with that driver's historical average *up to that trip* attached as a column.

SQL **window functions** (`OVER (...)`) let us compute an aggregation across a group of rows (`PARTITION BY driver_id`) ordered chronologically (`ORDER BY dep_time`) without collapsing the table:

```sql
SELECT
    route_id,
    driver_id,
    dep_time,
    delivery_delay_mins,
    -- Calculate the average delay of this driver's previous 3 trips BEFORE this trip
    COALESCE(
        AVG(delivery_delay_mins) OVER (
            PARTITION BY driver_id
            ORDER BY dep_time
            ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
        ),
        0.0
    ) AS driver_prior_3trip_avg_delay
FROM routes;
```

Look closely at the window frame `ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING`:
* `PARTITION BY driver_id` tells SQL to keep each driver's history in its own separate bucket.
* `ORDER BY dep_time` sorts that driver's trips from oldest to newest.
* `ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING` tells SQL: *"Average the 3 rows immediately before the current row (`3 PRECEDING` through `1 PRECEDING`), and stop one row short of the current trip."*
* Why stop at `1 PRECEDING` instead of including `CURRENT ROW`? Because when a truck is preparing to depart on Trip #4, Trip #4 hasn't happened yet! Including the current row's outcome inside its own input feature would be cheating. And on a driver's very first trip, there are no preceding rows, so `AVG(...)` returns `NULL` and `COALESCE(..., 0.0)` turns that `NULL` into `0.0`.

---

## 2c. How Supervised Learning Uses Features and Targets

You do not need prior machine learning coursework to understand how a **supervised learning** model uses the table we just built.

Imagine you are training a new human dispatcher. You hand them a binder of 10,000 completed trips from last year. On the left side of each page are the facts that were known when the truck left the yard: the departure hour, the route distance, the driver's safety score, the driver's prior average delay, and the weather at departure. In machine learning, those input columns are called the **feature matrix**, denoted by a capital <b><i>X</i></b>.

On the far right column of each page is what actually happened at the end of the trip: `target_delay_mins`. That single outcome column is called the **target variable** (or *label*), denoted by a lowercase <b><i>y</i></b>.

1. **During Training (Learning from History):** We pass thousands of historical rows where both <b><i>X</i></b> and <b><i>y</i></b> are known into a modeling library like `scikit-learn` or `XGBoost`. The algorithm studies how combinations of input features <b><i>X</i></b> (for example, `road_condition = 'Snow/Ice'` combined with `distance_miles > 200`) relate to the final delay <b><i>y</i></b>.
2. **During Live Prediction (Inference):** Tomorrow morning at 7:00 AM, a truck is scheduled to leave Cheyenne for Denver. Obviously, we do not know <b><i>y</i></b> (`target_delay_mins`) yet—the truck hasn't departed! Our data pipeline assembles a single row of current input features <b><i>X</i></b> (7:00 AM departure hour, 102.5 miles, the driver's prior delay average, and the latest Cheyenne weather station reading as of 7:00 AM) and hands <b><i>X</i></b> to the trained model. The model outputs its prediction for <b><i>y</i></b>.

This two-stage lifecycle establishes the fundamental rule of feature engineering:

> **The Point-in-Time Rule:** Every single feature column in <b><i>X</i></b> must only use information that was already recorded and available at or before the exact timestamp the prediction is made (`dep_time`).

---

## 2d. Why the $10M Delivery Model Failed (How Future Data Leaks into Training Tables)

To understand why data engineering is a distinct discipline from both software development and data science—and what happens when the Point-in-Time Rule is violated—consider an authentic industry failure.

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

### The Catastrophic Deployment Failure
On day one of live operation, the model's accuracy collapsed to **51%**—no better than flipping a coin. Shipments were delayed across the country, warehouses were left unstaffed, and the company lost an estimated \$10 million in contractual service level penalties.

What happened?

Look closely at the join condition:
```sql
ON r.origin_city = w.city AND r.dep_time::DATE = w.obs_time::DATE
```

Truck #104 departed Chicago at **7:15 AM** on a sunny morning. At **5:30 PM** that afternoon, a sudden severe blizzard struck Chicago, dumping 6 inches of snow. The weather monitoring station logged `precipitation_in = 6.0` and `road_condition = 'Snow/Ice'` at 6:00 PM.

Because the query joined purely on the **calendar date** (`dep_time::DATE = obs_time::DATE`), the evening blizzard data was attached to the morning truck's departure record. When the model was being trained, it looked at Truck #104 and saw "6 inches of snow at origin" and learned that snow equals delays.

In the real world at **7:15 AM**, that blizzard had not happened yet. The live model at departure time only had access to the 6:00 AM reading ("Clear skies, dry roads"). The model had been trained on the future.

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

## 2e. How Row and Column Databases Store Data — Row Filing vs. Columnar Straws

In your introductory SQL course, you used transactional databases like **PostgreSQL** or **SQLite**. In this course, we introduce **DuckDB**, **Apache Arrow**, and **Apache Parquet**. Why?

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

### The "Filing Cabinet vs. Drinking Straw" Analogy
* **Row-Store (PostgreSQL):** Imagine a warehouse of 10,000 filing folders. Each folder contains all details about one shipment (driver, vehicle, origin, fuel, delay). If your manager asks: *"What is our average delay?"*, you must walk to every single cabinet, pull out every folder, flip past 15 pages of driver info, read the delay number, and put the folder back.
* **Column-Store (DuckDB):** Imagine 5 long drinking straws. One straw contains only route IDs; another contains only delay numbers. To answer the manager's question, you pick up the "delay numbers" straw and dump all numbers directly onto the calculator. You never touch, load, or pay I/O costs for the other attributes.

DuckDB executes analytical queries 10x to 100x faster than traditional row engines on single-node laptops because it operates in-memory using **vectorized execution** over columnar data chunks. Likewise, when we save our finished dataset to disk, we export it as an **Apache Parquet** (`.parquet`) file rather than a `.csv` file: Parquet preserves exact column data types (`INT`, `DOUBLE`, `TIMESTAMP`) and compresses each column into fast, self-contained binary blocks.

---

## 2f. Defensive Query Evolution — From Leakage to Native ASOF JOIN

How do we solve the temporal leakage problem in SQL when joining irregular sensor streams (`weather_observations`) to event tables (`routes`)? Let's trace the engineering progression through three concrete steps.

### Step 1: The Failed Naive Join
When joining an event table (`routes`) to an observation table (`weather_observations`), a naive `JOIN ... ON date = date` leaks evening observations into morning departures:
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

### Step 2: The Window Function Workaround (Standard SQL)
Before modern analytical engines introduced temporal primitives, data engineers had to write complex subqueries using `ROW_NUMBER()` with strict lookback boundaries:
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
* **Why this works:** The condition `w.obs_time <= r.dep_time` guarantees that no weather record recorded after the truck left can ever enter the candidate set. Sorting `w.obs_time DESC` and taking `rank_order = 1` extracts the *latest known observation prior to departure*.  
* **The Limitation:** On large tables, computing an inequality join followed by a window sort over millions of partitions consumes immense RAM and CPU time.

### Step 3: DuckDB's Native `ASOF JOIN`
DuckDB provides native support for **`ASOF JOIN`**—a specialized physical operator engineered specifically for point-in-time event matching:

```sql
-- PRODUCTION DUCKDB ASOF JOIN: ELEGANT, DEFENSIVE, VECTORIZED
SELECT 
    r.route_id,
    r.driver_id,
    r.origin_city,
    r.dep_time,
    w.obs_time AS weather_obs_time,
    COALESCE(w.precipitation_in, 0.0) AS precipitation_in,
    COALESCE(w.visibility_miles, 10.0) AS visibility_miles,
    COALESCE(w.road_condition, 'Dry') AS road_condition,
    r.delivery_delay_mins AS target_delay
FROM routes r
ASOF LEFT JOIN weather_observations w
  ON r.origin_city = w.city
 AND r.dep_time >= w.obs_time;
```

* **How `ASOF JOIN` Operates:** For every route departure on the left, DuckDB searches the weather observations on the right that match the exact equality condition (`r.origin_city = w.city`) and picks the single row with the **maximum `obs_time` that is less than or equal to `r.dep_time`**.
* **Zero Temporal Leakage:** Because `r.dep_time >= w.obs_time`, it is mathematically impossible for an observation recorded at 6:00 PM to attach to a 7:15 AM departure.
* **Engine Performance:** Instead of building a massive Cartesian product and sorting window partitions, DuckDB uses a parallelized merge-join algorithm that scans pre-sorted columnar buffers in a single pass.

---

## 2g. Step-by-Step Code Ramp-Up & Guided Implementation Walkthrough (Python + DuckDB)

Let's build up the Python and DuckDB syntax you will use in this week's lab from the very first line of code, and then execute a complete end-to-end verification walkthrough.

### Step 1: Running Your First DuckDB Query in Python
DuckDB runs directly inside your Python script—there is no separate database server to install or configure. You import `duckdb`, call `duckdb.connect()`, and pass any SQL string to `con.sql(...)` or `con.execute(...)`:

```python
import duckdb

# Create an in-memory DuckDB database connection
con = duckdb.connect(database=":memory:")

# Run a simple SQL query and display the formatted table in the terminal
con.sql("SELECT 'Hello from DuckDB' AS greeting, 42 * 2 AS answer").show()
```

### Step 2: Creating Tables and Fetching Results as DataFrames or Scalars
You can execute `CREATE TABLE` and `INSERT INTO` statements using `con.execute(...)` or `con.sql(...)`. To inspect a `SELECT` result as a Pandas DataFrame, call `.df()` (or `.fetchdf()`). To grab a single scalar number (such as a row count for an assertion check), call `.fetchone()[0]`:

```python
con.execute("""
CREATE TABLE sample_trips (
    trip_id INT,
    driver_id INT,
    dep_time TIMESTAMP,
    delay_mins INT
);
INSERT INTO sample_trips VALUES
    (1, 101, '2026-10-10 08:00:00', 10),
    (2, 101, '2026-10-11 08:00:00', 20),
    (3, 101, '2026-10-12 08:00:00', 45);
""")

# Fetch a single scalar value (total number of rows)
row_count = con.sql("SELECT COUNT(*) FROM sample_trips").fetchone()[0]
print(f"Total trips loaded: {row_count}")

# Convert a query result to a DataFrame and print it
df = con.sql("SELECT * FROM sample_trips ORDER BY dep_time").df()
print(df)
```

### Step 3: Computing Leak-Free Rolling History with `ROWS BETWEEN`
Next, let's compute two historical driver features on `sample_trips`:
1. `driver_prior_avg_delay`: The driver's average delay across up to 5 prior trips (`ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING`), defaulting to `0.0` on their very first trip.
2. `driver_lifetime_trips`: How many trips this driver completed *before* the current trip (`COUNT(trip_id) OVER (... ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)`).

```python
history_df = con.sql("""
SELECT
    trip_id,
    driver_id,
    dep_time,
    delay_mins AS current_trip_delay,
    COALESCE(
        AVG(delay_mins) OVER (
            PARTITION BY driver_id
            ORDER BY dep_time
            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
        ),
        0.0
    ) AS driver_prior_avg_delay,
    COUNT(trip_id) OVER (
        PARTITION BY driver_id
        ORDER BY dep_time
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    ) AS driver_lifetime_trips
FROM sample_trips
ORDER BY driver_id, dep_time;
""").df()

print(history_df)
```

Trace what happens on each row for Driver 101:
* **Trip 1 (Oct 10):** There are no prior trips (`1 PRECEDING` does not exist). `driver_prior_avg_delay` is `0.0`, and `driver_lifetime_trips` is `0`.
* **Trip 2 (Oct 11):** Only Trip 1 (`delay = 10`) is in the prior window. `driver_prior_avg_delay` is `10.0`, and `driver_lifetime_trips` is `1`.
* **Trip 3 (Oct 12):** Trips 1 and 2 (`10` and `20`) are in the prior window. `driver_prior_avg_delay` is `15.0`, and `driver_lifetime_trips` is `2`. Notice that Trip 3's own 45-minute delay is never leaked into its input features!

### Step 4: Guided End-to-End Implementation Walkthrough (`ASOF JOIN` + Parquet Export)
Here is how you execute the complete defensive `ASOF JOIN` pipeline in Python using DuckDB's zero-copy relational API and export the result to Apache Parquet:

```python
import duckdb
import os

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

# 4. Execute the defensive ASOF LEFT JOIN
feature_rel = con.sql("""
SELECT 
    r.route_id,
    r.origin_city,
    r.dep_time,
    w.obs_time AS matched_weather_time,
    COALESCE(w.precipitation_in, 0.0) AS precipitation_in,
    COALESCE(w.road_condition, 'Dry') AS road_condition,
    r.delivery_delay_mins
FROM routes r
ASOF LEFT JOIN weather_observations w
  ON r.origin_city = w.city
 AND r.dep_time >= w.obs_time
ORDER BY r.route_id;
""")

# 5. Inspect as a DataFrame and export to Apache Parquet
feature_matrix = feature_rel.fetchdf()
print(feature_matrix)

os.makedirs("output", exist_ok=True)
feature_rel.write_parquet("output/feature_matrix.parquet")
```

**Verification Output:**
```
   route_id origin_city            dep_time matched_weather_time  precipitation_in road_condition  delivery_delay_mins
0       101     Chicago 2026-10-24 07:15:00  2026-10-24 06:00:00               0.0            Dry                   12
1       102     Chicago 2026-10-24 18:30:00  2026-10-24 17:30:00               4.5       Blizzard                   85
```

Notice that Route 101 (departed 07:15) was matched with the 06:00 observation (Dry, 0.0" rain), while Route 102 (departed 18:30) was matched with the 17:30 observation (Blizzard, 4.5" rain). The temporal boundaries are mathematically sound.

---

## 2h. Practice Exercises & Formative Self-Check FAQ

Try these three quick exercises in your GitHub Codespaces sandbox (`units/unit_01_relational_foundations/`) before starting the graded lab:

1. **Exercise 1 (Direct Parquet Querying):** Open a terminal in your sandbox and run `python -c "import duckdb; duckdb.sql('SELECT * FROM \"datasets/unit_01_routes.parquet\" LIMIT 5').show()"`. Observe how DuckDB reads a Parquet file directly inside a SQL `FROM` clause without needing `CREATE TABLE` first.
2. **Exercise 2 (Window Frame Experiment):** In `coding_clinic.ipynb`, temporarily change `ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING` to `ROWS BETWEEN 5 PRECEDING AND CURRENT ROW` and re-run the script. Compare the numbers in `prior_5trip_avg_delay` and notice how `CURRENT ROW` leaks the current trip's outcome into the feature column. Change it back to `1 PRECEDING`.
3. **Exercise 3 (Early Morning Departure Test):** Add a route that departs at `04:00:00` (before the earliest `06:00:00` weather observation) and compare `ASOF JOIN` vs. `ASOF LEFT JOIN`. Verify that `ASOF LEFT JOIN` preserves the route row while `COALESCE` fills in the default weather values.

### Common Traps & Formative Self-Check FAQ

* **Question 1: What happens if there is no weather observation prior to a route departure?**  
  *Answer:* If a truck departs at 5:00 AM and the earliest sensor observation in the database is at 6:00 AM, no weather row satisfies `r.dep_time >= w.obs_time`. A plain inner `ASOF JOIN` will drop that route row, whereas `ASOF LEFT JOIN` preserves the route row and returns `NULL` for all columns originating from the right-hand table (`matched_weather_time`, `precipitation_in`, etc.). In your ML pipeline, you handle these NULLs using `COALESCE(w.precipitation_in, 0.0)` or backward imputation.

* **Question 2: Can I use the shorthand `USING` syntax for ASOF joins?**  
  *Answer:* Yes, when both tables share identical column names, but remember DuckDB's rule: **the last column listed in the `USING` clause is always treated as the temporal inequality (`>=`)**, and all preceding columns require exact equality (`=`). For example: `ASOF JOIN weather USING (city, timestamp);`. When column names differ (such as `dep_time` vs. `obs_time`), use the explicit `ON r.origin_city = w.city AND r.dep_time >= w.obs_time` syntax.

* **Question 3: Why shouldn't I just use `LAG()` over the entire table?**  
  *Answer:* The `LAG()` window function operates within a single table and requires rows to be strictly ordered in an identical sequence. Because truck routes and weather sensors live in two separate tables—and sensor observations arrive at irregular intervals (e.g., every 15 minutes during storms, every 2 hours during clear skies)—`LAG(1)` cannot align two tables across continuous physical timestamps. `ASOF JOIN` matches across tables by exact timestamp boundary regardless of arrival intervals.

* **Question 4: Which way does the `>=` sign point in `ASOF JOIN`?**  
  *Answer:* Always ask yourself: *"Which event happens later on the clock?"* The truck departure (`r.dep_time`) must happen **at or after** the weather observation (`w.obs_time`), so `r.dep_time >= w.obs_time` (or equivalently `w.obs_time <= r.dep_time`).

---

## 3. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical specifications before beginning your applied lab:

1. **[DuckDB Official Documentation: ASOF JOIN Query Syntax](https://duckdb.org/docs/guides/sql_features/asof_join)**
   *Understand the formal syntax specifications, inequality operators, equality constraints, and NULL match behaviors for DuckDB's native point-in-time join engine.*

2. **[DuckDB Engineering Blog: Fuzzy Temporal Lookups](https://duckdb.org/2023/09/15/asof-joins-fuzzy-temporal-lookups.html)**
   *Study the architectural internals of how DuckDB plans and executes ASOF joins using parallelized merge pipelines instead of expensive Cartesian products.*

3. **[Apache Arrow In-Memory Columnar Format](https://arrow.apache.org/overview/)**
   *Learn how modern analytical engines organize columnar buffers in physical RAM to enable zero-copy data transfer and SIMD hardware acceleration.*

4. **[DuckDB Parquet Ingestion & Pushdown Optimization](https://duckdb.org/docs/data/parquet/overview)**
   *Discover how columnar queries achieve 100x performance gains by reading Parquet files directly from disk while skipping irrelevant columns and byte ranges.*

5. **[DuckDB Window Functions Reference](https://duckdb.org/docs/sql/window_functions)**
   *Review the complete syntax for SQL analytical window frames (`PARTITION BY`, `ORDER BY`, `ROWS BETWEEN N PRECEDING AND 1 PRECEDING`) used for defensive lag engineering.*

---

## 4. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to observe columnar data engines and temporal joins executed in live engineering environments:

### DuckDB in 100 Seconds <span style="font-size: 0.9em; color: #64748b;">(Fireship - 2:12)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="DuckDB in 100 Seconds" src="https://www.youtube.com/embed/uHm6FEb2Re4" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=uHm6FEb2Re4" target="_blank" rel="noopener">Open video in new tab (2:12)</a></p>

### Row vs. Column Storage Models: Why Columnar Databases Are Faster <span style="font-size: 0.9em; color: #64748b;">(Better Stack - 7:45)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Row vs Columnar Databases" src="https://www.youtube.com/embed/VGdMembUCC0" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=VGdMembUCC0" target="_blank" rel="noopener">Open video in new tab (7:45)</a></p>

### SQL ASOF Join Tutorial in DuckDB & Snowflake <span style="font-size: 0.9em; color: #64748b;">(Bill Wallis - Full Walkthrough)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="SQL ASOF Join Tutorial" src="https://www.youtube.com/embed/zWY36adlP_c" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=zWY36adlP_c" target="_blank" rel="noopener">Open video in new tab</a></p>

### Feature Engineering: Point-in-Time Correctness & Avoiding Data Leakage <span style="font-size: 0.9em; color: #64748b;">(CodeEmporium - Core Concepts)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="What is Data Leakage in Machine Learning" src="https://www.youtube.com/embed/cApPa55X2JU" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=cApPa55X2JU" target="_blank" rel="noopener">Open video in new tab</a></p>

---

## 5. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for this unit will appear in this designated container.</p>
</div>
