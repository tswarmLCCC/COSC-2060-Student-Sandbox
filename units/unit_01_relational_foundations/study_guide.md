# Unit 1: Required Readings, Concepts & Video Lectures

Welcome to the instructional reading and study guide for **Unit 1: Relational Foundations & Feature Tables**. This page organizes the week's learning materials into four sections:

1. **Instructor Lecture & Conceptual Deep Dive:** Learn what a machine learning feature table looks like, where operational source data comes from, how to build features in SQL from the ground up, how supervised learning works, and how to prevent future data from leaking into training datasets using DuckDB.
2. **Required Readings & Tutorial Guides:** Explore official documentation and practical guides on DuckDB, Apache Parquet, window functions, and point-in-time joins.
3. **Required Micro-Video Lectures (Embedded):** Watch short, focused video walkthroughs covering columnar storage, DuckDB, and temporal joins.
4. **Institutional Video Lecture Embeds:** Access instructor announcements and lab walkthrough recordings.

*Work through each section in sequence as part of your 150-minute self-study block before starting the applied lab.*

---

## 1. Instructor Lecture & Conceptual Deep Dive

### Moving from Database Reports to AI Datasets

Welcome to **COSC 2060: Modern Data Engineering & AI Infrastructure**.

In **CMAP 1815** and your introductory programming coursework, you learned how to store data in normalized relational tables and query them with SQL. You wrote `SELECT`, `WHERE`, `GROUP BY`, and `JOIN` statements to answer business questions and build reports for human readers—such as monthly sales summaries, customer invoices, or inventory checklists.

In this course, we use those exact same SQL and Python foundations for a new purpose: **building datasets that software systems and machine learning models consume automatically.**

When you write a query for a human manager, a human can spot an obvious mistake on a report. When you build a dataset to train a predictive model, the algorithm trusts every number in your table blindly. Even a subtle timing mistake in a SQL `JOIN` can feed future information into historical rows—a bug called **temporal data leakage** (or *look-ahead bias*) that makes a model look accurate during testing but fail in day-to-day operations.

We will start from the ground up. First, we will look at the exact shape of the output table we are trying to build this week and the operational systems where the raw data starts. Next, we will learn how to create basic features in SQL step by step, how supervised learning uses those columns, and how to use **DuckDB** and **Apache Parquet** to build fast, leak-free datasets.

#### Measurable Learning Objectives
* **Describe** the structure of a flat tabular feature matrix (<b><i>X</i></b> input features and <b><i>y</i></b> target variable) and trace how raw records flow from operational source systems into an analytical dataset.
* **Construct** foundational SQL features from scratch using arithmetic expressions, `CASE WHEN` indicator flags, `LEFT JOIN` lookups, and partitioned window functions.
* **Differentiate** between row-oriented databases (such as PostgreSQL) and column-oriented engines (such as DuckDB and Apache Parquet) in terms of disk reads and scan speed.
* **Identify** temporal data leakage in multi-table joins and window calculations.
* **Implement** leak-free rolling window lags (`ROWS BETWEEN N PRECEDING AND 1 PRECEDING`) and point-in-time `ASOF JOIN` queries in DuckDB.

---

### What Our Output Table Looks Like and Where the Data Comes From

Before writing any code, a data engineer always starts with two questions: **What does the finished dataset need to look like?** and **What source systems hold the raw ingredients?**

#### The Purpose
Our goal in Unit 1 is to build a **Flat Tabular Feature Matrix** saved as a `feature_matrix.parquet` file. Specifically, we are helping a freight logistics company (**Apex Logistics**) predict how many minutes late a delivery truck will arrive (`target_delay_mins`) **at the exact moment the truck is getting ready to depart its origin terminal**.

#### Why Models Need a Single Flat Table
In a relational database, data is split across many separate tables (drivers, routes, weather stations) to avoid repeating information. However, standard machine learning models (such as linear regression, random forests, and gradient-boosted trees) cannot browse across multiple database tables or follow foreign keys on their own.

Instead, a model requires a **single, flat two-dimensional grid**:
* **Every row** represents one specific decision point in time (one scheduled truck departure).
* **Every input column (called a feature, grouped together as <i>X</i>)** is a numeric or categorical measurement that was already known *before* that truck left the terminal.
* **The final column (called the target label, written as <i>y</i>)** is the actual outcome we want the model to learn to predict (`target_delay_mins`).

#### Where the Raw Data Comes From (Source Systems)
In a real freight company, the raw data does not sit in one neat file. It comes from three separate operational systems that record data on completely different schedules:

1. **Human Resources & Fleet Database (`drivers` table):** Updated occasionally by HR staff when drivers are hired or complete safety inspections. Stores `driver_id`, `hire_date`, `safety_score`, and `vehicle_type`.
2. **Dispatch Operational Database (`routes` table):** Updated by terminal dispatch software whenever a trip is scheduled, departs (`dep_time`), and finishes (`act_arrival`, `delivery_delay_mins`).
3. **External Weather Sensor Stream (`weather_observations` table):** Automated weather station readings (`obs_time`, `precipitation_in`, `visibility_miles`, `wind_speed_mph`, `road_condition`) pulled from NOAA airport weather stations. Weather stations do not know when trucks depart; they simply log an observation every hour or whenever weather conditions change.

#### Sample Output Dataset (The Target Shape)
When our Unit 1 pipeline finishes combining and cleaning those three sources, the output table looks like this:

| route_id (ID) | dep_hour (<i>X</i><sub>1</sub>) | distance_miles (<i>X</i><sub>2</sub>) | safety_score (<i>X</i><sub>3</sub>) | driver_prior_avg_delay (<i>X</i><sub>4</sub>) | precipitation_in (<i>X</i><sub>5</sub>) | visibility_miles (<i>X</i><sub>6</sub>) | road_condition (<i>X</i><sub>7</sub>) | target_delay_mins (<i>y</i>) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **101** | 6 | 102.5 | 0.98 | 0.0 | 0.00 | 10.0 | Dry | **15** |
| **102** | 14 | 102.5 | 0.98 | 15.0 | 0.10 | 6.0 | Wet | **45** |
| **103** | 7 | 345.0 | 0.85 | 0.0 | 0.00 | 10.0 | Dry | **0** |
| **104** | 9 | 178.0 | 0.92 | 0.0 | 0.25 | 4.0 | Wet | **20** |
| **105** | 6 | 102.5 | 0.98 | 30.0 | 0.00 | 10.0 | Dry | **5** |
| **106** | 18 | 215.0 | 0.79 | 12.5 | 0.90 | 1.2 | Snow/Ice | **85** |

> **Reference Guide:** Whenever you want to compare this tabular matrix format with the data shapes we will build in later units (time-series windows, image tensors, JSONL chunks, and API schemas), open **The Shapes of AI Data: A Companion Guide** in the *Getting Started - Course Orientation* module.

---

### Building Features in SQL from the Ground Up

What is **feature engineering**? A **feature** is simply a measurable clue—represented as a column in a table—that helps a model estimate an outcome. **Feature engineering** is the process of using domain knowledge and SQL or Python to transform raw operational columns (like timestamps, distances, and historical logs) into clear, informative numbers.

If you know how to write a `SELECT` statement from CMAP 1815, you already know the building blocks of feature engineering. Let's walk through the four fundamental ways we build features in SQL, starting with the simplest.

#### 1. Extracting Numbers from Timestamps and Arithmetic Ratios
Raw timestamps like `'2026-10-12 07:30:00'` are hard for a mathematical model to compare directly, because every day's date is brand new. However, the **hour of the day** (`7` for 7:00 AM rush hour) or the **day of the week** repeats every week and strongly affects traffic. We can also combine two columns with basic math:

```sql
SELECT
    route_id,
    dep_time,
    -- Extract the hour of departure (0 to 23) as a numeric feature
    EXTRACT(HOUR FROM dep_time) AS dep_hour,
    -- Extract day of week (0 = Sunday ... 6 = Saturday)
    EXTRACT(DOW FROM dep_time) AS dep_day_of_week,
    distance_miles,
    -- Compute an estimated driving time feature assuming 55 mph average
    ROUND(distance_miles / 55.0, 2) AS est_drive_hours
FROM routes;
```

#### 2. Creating Yes/No Indicator Flags with `CASE WHEN`
Often we want to highlight a specific condition—such as whether a trip departs during morning rush hour or whether a route is a long-haul trip over 250 miles. In SQL, we turn conditions into `1` (True) and `0` (False) using `CASE WHEN`:

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

#### 3. Attaching Static Attributes with `LEFT JOIN`
Our `routes` table only stores `driver_id`. To give our dataset information about the driver's safety record or truck type, we join the `drivers` table using a standard `LEFT JOIN`:

```sql
SELECT
    r.route_id,
    r.driver_id,
    r.distance_miles,
    d.safety_score,
    d.vehicle_type
FROM routes r
LEFT JOIN drivers d
  ON r.driver_id = d.driver_id;
```

Why use `LEFT JOIN` instead of `INNER JOIN`? Because in data engineering, `routes` is our primary event table. If a driver record is missing from HR's table, an `INNER JOIN` would silently delete the route row—hiding missing data. A `LEFT JOIN` keeps every route and fills missing columns with `NULL`, which we can then replace with a sensible default using `COALESCE(d.safety_score, 0.85)`.

#### 4. Summarizing Past Behavior with Window Functions (`OVER`)
What if we want a feature that measures a driver's recent track record, such as their average delay on previous trips?

In CMAP 1815, you used `GROUP BY driver_id` to calculate one summary row per driver. But for our feature matrix, we don't want to collapse the table into one row per driver—we need to keep one row per route and attach the driver's historical average up to that point in time. SQL **window functions** let us calculate an average across a group of rows (`PARTITION BY driver_id`) ordered by time (`ORDER BY dep_time`) without collapsing the rows:

```sql
SELECT
    route_id,
    driver_id,
    dep_time,
    delivery_delay_mins,
    -- Calculate average delay of the driver's previous 3 trips BEFORE this trip
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

Look closely at the line `ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING`:
* `PARTITION BY driver_id` tells SQL to calculate each driver's history separately.
* `ORDER BY dep_time` sorts that driver's trips from oldest to newest.
* `ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING` tells SQL: *"Look at the 3 trips immediately before the current row (`3 PRECEDING` through `1 PRECEDING`), and stop one row short of the current trip."*
* Why stop at `1 PRECEDING` instead of `CURRENT ROW`? Because when a truck is about to depart on Trip #4, Trip #4 hasn't happened yet! Including the current row's delay inside its own input feature would be cheating. And if it is a driver's very first trip, there are no preceding rows, so `AVG(...)` returns `NULL` and `COALESCE(..., 0.0)` turns that `NULL` into `0.0`.

---

### How Supervised Learning Uses Features and Targets

You do not need any prior machine learning coursework to succeed in this class. Let's demystify how a **supervised learning** model uses the table we just built.

Imagine you are training a new dispatcher. You hand them a binder of 10,000 completed trips from last year. On the left side of each page are the facts that were known when the truck left the yard: the departure hour, the route distance, the driver's safety score, the driver's prior average delay, and the weather at departure. In machine learning, those input columns are called the **feature matrix**, denoted by a capital <b><i>X</i></b>.

On the far right column of each page is what actually happened at the end of the trip: `target_delay_mins`. That single outcome column is called the **target variable** (or *label*), denoted by a lowercase <b><i>y</i></b>.

1. **During Training (Learning from History):** We feed thousands of historical rows where both <b><i>X</i></b> and <b><i>y</i></b> are known into a Python library like `scikit-learn`. The algorithm studies how combinations of input features <b><i>X</i></b> (for example, `road_condition = 'Snow/Ice'` combined with `distance_miles > 200`) relate to the final delay <b><i>y</i></b>.
2. **During Live Prediction (Inference):** Tomorrow morning at 7:00 AM, a truck is scheduled to leave Cheyenne for Denver. Obviously, we do not know <b><i>y</i></b> (`target_delay_mins`) yet—the truck hasn't left! Our data pipeline assembles a single row of current input features <b><i>X</i></b> (7:00 AM departure hour, 102.5 miles, driver's prior delay average, and the latest Cheyenne weather station reading as of 7:00 AM) and hands <b><i>X</i></b> to the trained model. The model outputs its prediction for <b><i>y</i></b>.

This two-step process reveals the golden rule of feature engineering:

> **The Point-in-Time Rule:** Every single feature column in <b><i>X</i></b> must only use information that was already recorded and available at or before the moment the prediction is made (`dep_time`).

---

### How Future Data Leaks into Training Tables

To see what happens when the Point-in-Time Rule is broken, consider a real-world failure from the freight industry.

A freight carrier wanted to predict whether scheduled shipments would be delayed by more than 30 minutes (`delivery_delay_mins > 30`) so dispatchers could reroute urgent cargo before departure. A developer connected to the company's database and joined the `routes` table to the `weather_observations` table using a standard SQL date join:

```sql
-- PROBLEMATIC QUERY: Joins on calendar date instead of timestamp!
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

When they trained a model on the resulting table, it scored **99.4% accuracy** on historical test data. Everyone celebrated and put the model into live operation.

#### Why the Model Failed in Live Dispatch
In live operation, the model's accuracy dropped to **51%**—no better than guessing. Why?

Look at the join condition:
```sql
ON r.origin_city = w.city AND r.dep_time::DATE = w.obs_time::DATE
```

Suppose Truck #104 departed Chicago at **7:15 AM** on a clear morning. Later that evening at **5:30 PM**, a heavy blizzard hit Chicago, dropping 6 inches of snow. The airport weather station recorded `precipitation_in = 6.0` and `road_condition = 'Snow/Ice'` at **6:00 PM**.

Because the SQL query joined purely on the **calendar date** (`dep_time::DATE = obs_time::DATE`), the 6:00 PM blizzard reading was matched to the 7:15 AM departure. During training, the model saw historical rows with evening snowstorms attached to morning trips.

In real life at **7:15 AM**, that evening blizzard had not happened yet. When the model ran live at 7:15 AM, the only weather reading available was the 6:00 AM observation (`Clear skies, dry roads`).

```
TIMELINE OF EVENTS ON OCTOBER 24:
06:00 AM ── Weather Station Logs: "Clear skies, dry roads"
07:15 AM ── Truck #104 Departs Chicago  <── PREDICTION MUST HAPPEN HERE
12:00 PM ── Truck #104 arrives at destination
05:30 PM ── Heavy blizzard hits Chicago
06:00 PM ── Weather Station Logs: "Blizzard, 6.0 inches snow"

WHAT THE CALENDAR-DATE SQL JOIN DID:
Attached the 06:00 PM blizzard reading to the 07:15 AM departure!
```

This mistake is called **temporal data leakage** (or *look-ahead bias*). Whenever historical training queries accidentally grab records with timestamps later than the event timestamp, the training dataset contains information from the future. As data engineers, our job is to write SQL queries that enforce strict timestamp boundaries (`w.obs_time <= r.dep_time`).

---

### How Row and Column Databases Store Data

In CMAP 1815, you worked with transactional databases like **PostgreSQL** or **SQLite**. In COSC 2060, we use **DuckDB** and **Apache Parquet**. Why do data engineers use a different database engine for analytics and AI feature pipelines?

The difference comes down to how bytes are arranged on disk and in memory.

```
TABLE: routes (route_id INT, driver_id INT, origin_city VARCHAR, distance_miles DOUBLE, delay_mins DOUBLE)

1. ROW-ORIENTED STORAGE (OLTP - PostgreSQL / SQLite / MySQL):
[101, 12, 'Chicago', 102.5, 15.0] [102, 19, 'Denver', 345.0, 0.0] ...
- Physical Layout: All columns for Row 1 are stored side-by-side, followed by all columns for Row 2.
- Best For: Looking up or updating one single customer order or truck route by ID (Online Transaction Processing, or OLTP).
- Bottleneck for Analytics: To compute AVG(delay_mins) across 10 million routes, the computer must read every column of every row from disk into memory, even though 80% of the columns are not needed.

2. COLUMN-ORIENTED STORAGE (OLAP - DuckDB / Apache Parquet / Apache Arrow):
[route_id: 101, 102, ...] [distance_miles: 102.5, 345.0, ...] [delay_mins: 15.0, 0.0, ...]
- Physical Layout: All values for a single column are stored together in contiguous memory blocks.
- Best For: Scanning, filtering, and aggregating specific feature columns across millions of rows (Online Analytical Processing, or OLAP).
- Advantage for Analytics: To compute AVG(delay_mins), DuckDB reads ONLY the delay_mins block from disk and processes thousands of numbers at once using vectorized CPU instructions.
```

#### The Filing Cabinet vs. Drinking Straw Comparison
* **Row-Oriented Database (Filing Cabinet):** Imagine 10,000 paper file folders in a cabinet. Each folder holds 15 pages about one trip. If you want to find the average delay across all 10,000 trips, you have to pull out all 10,000 folders, flip past 14 pages in each folder to read the delay number, and put the folder back.
* **Column-Oriented Database (Drinking Straw):** Imagine each column is stored in its own dedicated tube—one tube holds only route IDs, another holds only distances, and another holds only delay numbers. When you ask for `AVG(delay_mins)`, DuckDB grabs only the `delay_mins` tube and ignores the rest.

When we save our finished dataset at the end of a pipeline, we export it as an **Apache Parquet** (`.parquet`) file rather than a `.csv` file. Unlike a text CSV file—which forgets whether a column is an integer, float, or timestamp and forces the computer to parse every character row by row—a Parquet file stores data in compressed columnar blocks with exact data types preserved.

---

### Step-by-Step Code Ramp-Up: DuckDB, Rolling Windows, and ASOF JOIN

Let's build up the Python and DuckDB syntax you will use in this week's lab from the very first line of code.

#### Step 1: Running Your First DuckDB Query in Python
DuckDB runs directly inside your Python script—there is no separate database server to install or start. You import `duckdb`, call `duckdb.connect()`, and pass any SQL string to `con.sql(...)`:

```python
import duckdb

# Create an in-memory DuckDB database connection
con = duckdb.connect()

# Run a simple SQL query and print the formatted table to the terminal
con.sql("SELECT 'Hello from DuckDB' AS greeting, 42 * 2 AS answer").show()
```

#### Step 2: Creating Tables and Converting Query Results to DataFrames
You can execute `CREATE TABLE` and `INSERT INTO` statements using `con.sql(...)`. If you want to inspect the result of a `SELECT` query as a Pandas DataFrame, add `.df()` at the end. If you want to grab a single number (like a row count for a safety check), add `.fetchone()[0]`:

```python
con.sql("""
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

#### Step 3: Computing Leak-Free Rolling History with `ROWS BETWEEN`
Now let's compute two historical driver features on `sample_trips`:
1. `driver_prior_avg_delay`: The driver's average delay across up to 5 prior trips (`ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING`), defaulting to `0.0` on their first trip.
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

Let's trace what happens on each row for Driver 101:
* **Trip 1 (Oct 10):** There are no prior trips (`1 PRECEDING` does not exist). `driver_prior_avg_delay` is `0.0`, and `driver_lifetime_trips` is `0`.
* **Trip 2 (Oct 11):** Only Trip 1 (`delay = 10`) is in the prior window. `driver_prior_avg_delay` is `10.0`, and `driver_lifetime_trips` is `1`.
* **Trip 3 (Oct 12):** Trips 1 and 2 (`10` and `20`) are in the prior window. `driver_prior_avg_delay` is `15.0`, and `driver_lifetime_trips` is `2`. Notice that Trip 3's own 45-minute delay is never leaked into its input features!

#### Step 4: Matching Irregular Sensor Timestamps with `ASOF JOIN`
Finally, how do we match a truck departure (`routes.dep_time`) to the most recent weather reading (`weather_observations.obs_time`) in that city without ever grabbing a future weather reading?

In standard SQL, you would have to write a complicated subquery with `ROW_NUMBER() OVER (PARTITION BY route_id ORDER BY obs_time DESC)` and filter where `obs_time <= dep_time`. DuckDB gives us a built-in command designed specifically for this: **`ASOF JOIN`**.

An `ASOF JOIN` ("As-Of Join") asks: *"As of the exact timestamp on the left table (`r.dep_time`), what was the most recent row on the right table (`w.obs_time`) for that city?"*

```python
import duckdb

con = duckdb.connect()

# 1. Create the routes table (truck departures)
con.sql("""
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

# 2. Create the weather_observations table (hourly/irregular sensor logs)
con.sql("""
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

# 3. Use ASOF LEFT JOIN so every route is kept and matched to the latest prior weather
feature_matrix = con.sql("""
SELECT 
    r.route_id,
    r.origin_city,
    r.dep_time,
    w.obs_time AS matched_weather_time,
    COALESCE(w.precipitation_in, 0.0) AS precipitation_in,
    COALESCE(w.road_condition, 'Normal') AS road_condition,
    r.delivery_delay_mins AS target_delay_mins
FROM routes r
ASOF LEFT JOIN weather_observations w
  ON r.origin_city = w.city
 AND r.dep_time >= w.obs_time
ORDER BY r.route_id;
""").df()

print(feature_matrix)
```

**Output:**
```
   route_id origin_city            dep_time matched_weather_time  precipitation_in road_condition  target_delay_mins
0       101     Chicago 2026-10-24 07:15:00  2026-10-24 06:00:00               0.0            Dry                 12
1       102     Chicago 2026-10-24 18:30:00  2026-10-24 17:30:00               4.5       Blizzard                 85
```

Look at the two conditions in `ASOF LEFT JOIN`:
1. `ON r.origin_city = w.city`: The city must match exactly (`=`).
2. `AND r.dep_time >= w.obs_time`: The departure timestamp must be **greater than or equal to** the weather observation timestamp (`>=`). DuckDB automatically picks the single closest weather reading at or before `dep_time`.
3. Why `ASOF LEFT JOIN` with `COALESCE`? If a truck leaves at 4:30 AM before the first weather reading of the day (6:00 AM), there is no prior weather row. `ASOF LEFT JOIN` keeps the truck route in our dataset with `NULL` weather columns, and `COALESCE` fills in safe baseline defaults (`0.0` precipitation, `'Normal'` road conditions).

#### Step 5: Exporting to Apache Parquet
Once your query returns a DuckDB relation, exporting it to a Parquet file takes a single method call:

```python
import os

os.makedirs("output", exist_ok=True)
rel = con.sql("SELECT * FROM routes")
rel.write_parquet("output/feature_matrix.parquet")
```

---

### Practice Exercises and Common Questions

Try these three quick exercises in your GitHub Codespaces sandbox (`units/unit_01_relational_foundations/`) before starting the graded lab:

1. **Exercise 1 (Inspecting Parquet Metadata):** Open a terminal in your sandbox and run `python -c "import duckdb; duckdb.sql('SELECT * FROM \"datasets/unit_01_routes.parquet\" LIMIT 5').show()"`. Observe how DuckDB reads a Parquet file directly inside a SQL `FROM` clause without needing `CREATE TABLE` first.
2. **Exercise 2 (Window Frame Experiment):** In `coding_clinic.py`, temporarily change `ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING` to `ROWS BETWEEN 5 PRECEDING AND CURRENT ROW` and re-run the script. Compare the numbers in `prior_5trip_avg_delay` and notice how `CURRENT ROW` leaks the current trip's outcome into the feature column. Change it back to `1 PRECEDING`.
3. **Exercise 3 (Early Morning Departure Test):** Add a route that departs at `04:00:00` (before the `05:00:00` weather observation) and compare `ASOF JOIN` vs. `ASOF LEFT JOIN`. Verify that `ASOF LEFT JOIN` preserves the route row while `COALESCE` fills in the default weather values.

#### Common Questions & Troubleshooting

* **Question 1: What happens if a truck departs at 5:00 AM and the earliest weather observation in the table is at 6:00 AM?**  
  *Answer:* Because 6:00 AM is in the future relative to 5:00 AM, no weather row satisfies `r.dep_time >= w.obs_time`. If you use a plain inner `ASOF JOIN`, that 5:00 AM route row is dropped from the results. If you use `ASOF LEFT JOIN`, the route row is kept with `NULL` for the weather columns, which you can fill using `COALESCE(w.precipitation_in, 0.0)`.

* **Question 2: Which way does the `>=` sign point in `ASOF JOIN`?**  
  *Answer:* Always ask yourself: *"Which event happens later on the clock?"* The truck departure (`r.dep_time`) must happen **at or after** the weather observation (`w.obs_time`), so `r.dep_time >= w.obs_time` (or equivalently `w.obs_time <= r.dep_time`).

* **Question 3: Why shouldn't I just use `LAG(precipitation_in, 1)` instead of `ASOF JOIN`?**  
  *Answer:* `LAG()` only looks at the previous row within a single table. Trucks and weather sensors live in two different tables and record rows at completely different times (a city might log 24 weather readings on a day with only 2 truck departures). `ASOF JOIN` aligns two separate tables across continuous timestamps.

---

## 2. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical references before beginning your applied lab:

1. **[DuckDB Official Documentation: ASOF JOIN Query Syntax](https://duckdb.org/docs/guides/sql_features/asof_join)**
   *Understand the syntax specifications, inequality operators, equality constraints, and NULL match behaviors for DuckDB's native point-in-time join engine.*

2. **[DuckDB Engineering Blog: Fuzzy Temporal Lookups](https://duckdb.org/2023/09/15/asof-joins-fuzzy-temporal-lookups.html)**
   *Study how DuckDB plans and executes ASOF joins using parallelized merge pipelines instead of expensive cross-joins.*

3. **[Apache Arrow In-Memory Columnar Format](https://arrow.apache.org/overview/)**
   *Learn how modern analytical engines organize columnar buffers in physical RAM to enable fast scans and hardware acceleration.*

4. **[DuckDB Parquet Ingestion & Pushdown Optimization](https://duckdb.org/docs/data/parquet/overview)**
   *See how columnar queries achieve high performance by reading Parquet files directly from disk while skipping unneeded columns.*

5. **[DuckDB Window Functions Reference](https://duckdb.org/docs/sql/window_functions)**
   *Review the complete syntax for SQL analytical window frames (`PARTITION BY`, `ORDER BY`, `ROWS BETWEEN N PRECEDING AND 1 PRECEDING`) used for historical lag features.*

---

## 3. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to see columnar data engines and temporal joins in action:

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

## 4. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for this unit will appear in this designated container.</p>
</div>
