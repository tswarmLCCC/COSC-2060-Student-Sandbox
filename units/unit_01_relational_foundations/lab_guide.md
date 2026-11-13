# Unit 1 Applied Lab: The Feature Matrix Builder

> **Course**: COSC 2060 — Modern Data Engineering & AI Infrastructure  
> **Unit**: Unit 1 — Relational Foundations & Feature Tables  
> **Deliverable**: `lab1_starter.py`  
> **Total Points**: 100 Points  
> **Toolchain**: Python 3.10+, DuckDB  
> **New to the Sandbox?** If you haven't created your personal GitHub Codespaces workspace from the template repository yet, open **Getting Started with the Lab Environment** (`getting-started-lab-sandbox.html`) in the *Getting Started - Course Orientation* module first.

---

## 1. Coding Clinic: "I Do, We Do, You Do"

### "I Do" — The Instructor Demonstration: Point-in-Time Temporal Alignment (DuckDB ASOF JOIN)
When joining operational events (such as truck departures) to continuous sensor or weather streams, standard relational `INNER JOIN` or simple timestamp equality will fail because exact timestamps rarely match. Using future observations introduces catastrophic **target leakage**. The professional standard is an **ASOF JOIN**, matching each event strictly to the most recent observation at or before departure:

```python
import duckdb

con = duckdb.connect()

# Departures
con.sql("""
CREATE TABLE departures (
    route_id INT,
    city VARCHAR,
    dep_time TIMESTAMP
);
INSERT INTO departures VALUES 
    (1, 'Cheyenne', '2026-10-15 06:00:00'),
    (2, 'Cheyenne', '2026-10-15 14:00:00');

# Weather observations (intermittent weather station logs)
CREATE TABLE weather_station (
    city VARCHAR,
    obs_time TIMESTAMP,
    precip_in DECIMAL(4,2),
    condition VARCHAR
);
INSERT INTO weather_station VALUES
    ('Cheyenne', '2026-10-15 05:00:00', 0.00, 'Clear'),
    ('Cheyenne', '2026-10-15 12:00:00', 0.45, 'Thunderstorm'),
    ('Cheyenne', '2026-10-15 18:00:00', 1.20, 'Hail');
""")

# ASOF JOIN: Takes the latest weather strictly <= departure time
result = con.sql("""
SELECT 
    d.route_id,
    d.city,
    d.dep_time,
    w.obs_time AS matched_weather_time,
    w.condition,
    w.precip_in
FROM departures d
ASOF JOIN weather_station w
    ON d.city = w.city
    AND d.dep_time >= w.obs_time
ORDER BY d.route_id;
""").df()

print("Point-in-Time Matched Features (Zero Leakage):")
print(result)
```

---

### "We Do" — Guided Class Practice: Rolling History Without Target Leakage
When engineering historical driver features (e.g., rolling average delay), the current trip's outcome must NEVER be included in its own feature calculation. Using `ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING` guarantees that only prior completed trips are considered:

```python
con.sql("""
CREATE TABLE trip_logs (
    driver_id INT,
    trip_id INT,
    dep_time TIMESTAMP,
    delay_mins INT
);
INSERT INTO trip_logs VALUES 
    (101, 1, '2026-10-10 08:00:00', 10),
    (101, 2, '2026-10-11 08:00:00', 25),
    (101, 3, '2026-10-12 08:00:00', 0),
    (101, 4, '2026-10-13 08:00:00', 45);
""")

rolling_features = con.sql("""
SELECT 
    driver_id,
    trip_id,
    dep_time,
    delay_mins AS current_trip_delay,
    COALESCE(
        AVG(delay_mins) OVER (
            PARTITION BY driver_id 
            ORDER BY dep_time 
            ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
        ), 0.0
    ) AS prior_5trip_avg_delay
FROM trip_logs
ORDER BY driver_id, dep_time;
""").df()

print("Leak-Free Rolling Features:")
print(rolling_features)
```

---

### "You Do" — Independent Application: Connecting to the Feature Matrix Builder
Now apply these core patterns to build the complete, multi-table production feature matrix in Section 2 below!

---

## 2. Applied Laboratory Challenges: The Feature Matrix Builder (100 Points)

### Scenario & Business Context
You have been hired as the lead data engineer for **Apex Logistics Inc.**, an interstate shipping company. The machine learning team is preparing to train a gradient-boosted decision tree (GBDT) model to predict delivery delays (`delivery_delay_mins`) before trucks depart their origin terminal.

Your mission is to write a defensive data pipeline script (`lab1_feature_builder.py`) that ingests three messy, unjoined operational tables and outputs a clean, leak-free 2D feature matrix saved as `feature_matrix.parquet` (and `.csv`).

### Database Schemas
Your pipeline will create and populate three tables:

1. **`drivers`**:
   - `driver_id` (INTEGER, Primary Key)
   - `driver_name` (VARCHAR)
   - `hire_date` (DATE)
   - `safety_score` (DECIMAL(3,2))
   - `vehicle_type` (VARCHAR)

2. **`routes`**:
   - `route_id` (INTEGER, Primary Key)
   - `driver_id` (INTEGER, Foreign Key)
   - `origin_city` (VARCHAR)
   - `dest_city` (VARCHAR)
   - `dep_time` (TIMESTAMP)
   - `sched_arrival` (TIMESTAMP)
   - `act_arrival` (TIMESTAMP)
   - `distance_miles` (DECIMAL(6,1))
   - `delivery_delay_mins` (INTEGER, Target Variable)

3. **`weather_observations`**:
   - `station_id` (VARCHAR)
   - `city` (VARCHAR)
   - `obs_time` (TIMESTAMP)
   - `precipitation_in` (DECIMAL(4,2))
   - `visibility_miles` (DECIMAL(4,1))
   - `wind_speed_mph` (INTEGER)
   - `road_condition` (VARCHAR)

---

### Submission Instructions (GitHub-Only Workflow)
1. Edit and test `units/unit_01_relational_foundations/lab1_starter.py` inside your personal `COSC-2060-Student-Sandbox-yourname` repository.
2. Ensure your script runs standalone from the command line (`python units/unit_01_relational_foundations/lab1_starter.py`) without errors and generates `output/feature_matrix.parquet`.
3. Commit and push your changes to your personal GitHub repository:
   ```bash
   git add -A
   git commit -m "Complete Unit 1 Lab"
   git push
   ```
4. In Canvas, submit your **GitHub repository URL** along with a **list of the files you changed** (e.g., `units/unit_01_relational_foundations/lab1_starter.py`). Do not upload `.py` files to Canvas.

---

### Graded Challenges

#### Part 0: Basics Warm-Up — SQL Feature Building Blocks
Before writing the full `ASOF JOIN` and window functions, run `part0_basics_warmup(con)` in `lab1_starter.py` to verify your DuckDB connection, inspect table row counts, extract `dep_hour`, compute an arithmetic ratio (`distance_miles / 55.0`), create a `CASE WHEN` flag (`is_long_haul`), and run a basic `LEFT JOIN` between `routes` and `drivers`.

#### Part 1: DuckDB Environment & Schema Introspection (20 Points)
1. **Engine Verification**: Write DuckDB SQL to inspect the active version and verify in-memory execution.
2. **Schema Ingestion**: Programmatically create the three relational tables and populate them with the provided mock logistics dataset (10 drivers, 30 routes, 50 weather observations).
3. **Integrity Audit**: Write a validation query verifying that no route has `act_arrival < dep_time` (sanity checking the raw operational logs).

#### Part 2: Temporal Point-in-Time Alignment (40 Points)
1. **The As-Of Join**: Construct a clean `ASOF JOIN` that matches each route's `dep_time` with the closest historical weather observation where `obs_time <= dep_time` and `origin_city = city`.
2. **Zero-Leakage Assertion**: Write an automated defensive assertion test that checks every row in the result set. If any row has `weather_obs_time > dep_time`, your script must raise a `RuntimeError("CRITICAL: Temporal data leakage detected!")`.
3. **Missing Weather Fallback**: Use `COALESCE` to handle routes that departed before the first weather station recording of the day, setting default baseline values (`precipitation_in = 0.0`, `visibility_miles = 10.0`, `road_condition = 'Normal'`).

#### Part 3: Feature Engineering & Matrix Export (40 Points)
1. **Rolling Driver Experience Features**:
   - Compute `driver_prior_avg_delay`: Average delay over the driver's prior 5 routes using `ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING`. (Must evaluate to `0.0` for a driver's first trip).
   - Compute `driver_lifetime_trips`: Count of all routes completed prior to the current departure timestamp.
2. **Temporal Extraction**:
   - Extract `dep_hour` (0–23) and `dep_day_of_week` (0–6).
3. **Final 2D Matrix Export**:
   - Select the final feature matrix columns:
     - Entity IDs: `route_id`, `driver_id`
     - Features (<b><i>X</i></b>): `dep_hour`, `dep_day_of_week`, `distance_miles`, `safety_score`, `vehicle_type`, `driver_prior_avg_delay`, `driver_lifetime_trips`, `precipitation_in`, `visibility_miles`, `wind_speed_mph`, `road_condition`
     - Target Label (<b><i>y</i></b>): `target_delay_mins`
   - Export the result directly to Parquet format using DuckDB's `COPY ... TO 'output/feature_matrix.parquet' (FORMAT PARQUET)`.

---

### Copy-and-Paste Starter Template (`lab1_starter.py`)

Copy the code below into a file named `lab1_starter.py` to begin your lab:

```python
"""
====================================================================
COSC 2060: Modern Data Engineering & AI Infrastructure
Unit 1 Applied Lab: The Feature Matrix Builder
Starter Template File (100 Points Total)
====================================================================
Student Name : [YOUR NAME HERE]
Submission   : lab1_starter.py
Due Date     : Friday at 11:59 PM (Midnight MT)
====================================================================
"""
import os
import duckdb

def initialize_database():
    """Initializes in-memory DuckDB and loads raw operational tables."""
    con = duckdb.connect()
    
    print("Loading raw operational logistics data...")
    
    # 1. Drivers Dimension Table
    con.sql("""
    CREATE TABLE drivers (
        driver_id INT PRIMARY KEY,
        driver_name VARCHAR,
        hire_date DATE,
        safety_score DECIMAL(3,2),
        vehicle_type VARCHAR
    );
    INSERT INTO drivers VALUES
        (101, 'Sarah Chen',    '2022-01-15', 0.98, 'Semi-Trailer'),
        (102, 'David Miller',  '2021-06-10', 0.85, 'Box Truck'),
        (103, 'Amina Yusuf',   '2023-04-20', 0.92, 'Semi-Trailer'),
        (104, 'Carlos Gomez',  '2020-11-05', 0.79, 'Flatbed');
    """)
    
    # 2. Routes Transactional Fact Table
    con.sql("""
    CREATE TABLE routes (
        route_id INT PRIMARY KEY,
        driver_id INT,
        origin_city VARCHAR,
        dest_city VARCHAR,
        dep_time TIMESTAMP,
        sched_arrival TIMESTAMP,
        act_arrival TIMESTAMP,
        distance_miles DECIMAL(6,1),
        delivery_delay_mins INT
    );
    INSERT INTO routes VALUES
        (1, 101, 'Cheyenne', 'Denver',   '2026-10-12 06:00:00', '2026-10-12 08:00:00', '2026-10-12 08:15:00', 102.5, 15),
        (2, 101, 'Denver',   'Cheyenne', '2026-10-12 14:00:00', '2026-10-12 16:00:00', '2026-10-12 16:45:00', 102.5, 45),
        (3, 102, 'Salt Lake','Boise',    '2026-10-12 07:30:00', '2026-10-12 13:30:00', '2026-10-12 13:30:00', 345.0, 0),
        (4, 103, 'Cheyenne', 'Casper',   '2026-10-12 09:00:00', '2026-10-12 12:00:00', '2026-10-12 12:20:00', 178.0, 20),
        (5, 101, 'Cheyenne', 'Denver',   '2026-10-13 06:30:00', '2026-10-13 08:30:00', '2026-10-13 08:35:00', 102.5, 5);
    """)
    
    # 3. Weather Observations Asynchronous Sensor Stream
    con.sql("""
    CREATE TABLE weather_observations (
        station_id VARCHAR,
        city VARCHAR,
        obs_time TIMESTAMP,
        precipitation_in DECIMAL(4,2),
        visibility_miles DECIMAL(4,1),
        wind_speed_mph INT,
        road_condition VARCHAR
    );
    INSERT INTO weather_observations VALUES
        ('CHY-1', 'Cheyenne', '2026-10-12 05:00:00', 0.00, 10.0, 12, 'Dry'),
        ('CHY-1', 'Cheyenne', '2026-10-12 08:00:00', 0.25,  4.0, 28, 'Wet'),
        ('CHY-1', 'Cheyenne', '2026-10-12 12:00:00', 0.90,  1.2, 45, 'Snow/Ice'),
        ('DEN-1', 'Denver',   '2026-10-12 06:00:00', 0.00, 10.0,  8, 'Dry'),
        ('DEN-1', 'Denver',   '2026-10-12 13:00:00', 0.10,  6.0, 15, 'Wet'),
        ('SLC-1', 'Salt Lake','2026-10-12 06:30:00', 0.00, 10.0,  5, 'Dry');
    """)
    
    return con


def part0_basics_warmup(con):
    """
    PART 0: Basics Warm-Up (Ground-Up SQL Feature Building)
    Verifies basic DuckDB row counts, arithmetic feature ratios, CASE WHEN flags,
    and a simple LEFT JOIN before moving into ASOF JOIN and window functions.
    """
    print("\n--- Part 0: Basics Warm-Up (SQL Feature Building Blocks) ---")
    driver_count = con.sql("SELECT COUNT(*) FROM drivers").fetchone()[0]
    route_count = con.sql("SELECT COUNT(*) FROM routes").fetchone()[0]
    print(f"Loaded {driver_count} drivers and {route_count} routes.")

    basic_features = con.sql("""
    SELECT
        r.route_id,
        r.origin_city,
        EXTRACT(HOUR FROM r.dep_time) AS dep_hour,
        ROUND(r.distance_miles / 55.0, 2) AS est_drive_hours,
        CASE WHEN r.distance_miles >= 200.0 THEN 1 ELSE 0 END AS is_long_haul,
        COALESCE(d.safety_score, 0.85) AS safety_score
    FROM routes r
    LEFT JOIN drivers d ON r.driver_id = d.driver_id
    ORDER BY r.route_id
    LIMIT 3;
    """).df()
    print("Basic SQL Features Preview (First 3 Routes):")
    print(basic_features)
    return basic_features


def build_feature_matrix(con):
    """
    Constructs the leak-free feature matrix query and returns the DuckDB relation.
    
    TODO: Complete the SQL statement below adhering to all unit requirements:
    1. ASOF JOIN routes with weather_observations on city and dep_time >= obs_time
    2. Rolling window lag with ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
    3. Proper COALESCE defaults for early morning departures
    """
    query = """
    -- [YOUR PIPELINE SQL HERE]
    SELECT 
        r.route_id,
        r.driver_id,
        EXTRACT(HOUR FROM r.dep_time) AS dep_hour,
        r.distance_miles,
        d.safety_score,
        r.delivery_delay_mins AS target_delay_mins
    FROM routes r
    JOIN drivers d ON r.driver_id = d.driver_id
    """
    return con.sql(query)


def verify_no_leakage(con):
    """
    Automated Defensive Audit: Verifies that no weather observation attached
    to a route was recorded AFTER the departure time.
    """
    leakage_check = con.sql("""
    SELECT count(*) AS leak_count
    FROM routes r
    ASOF JOIN weather_observations w
      ON r.origin_city = w.city
     AND r.dep_time >= w.obs_time
    WHERE w.obs_time > r.dep_time;
    """).fetchone()[0]
    
    assert leakage_check == 0, f"LEAKAGE DETECTED: {leakage_check} rows have future weather data!"
    print("PASS: Zero temporal leakage verified. Pipeline is defensive.")


def main():
    print("=" * 60)
    print("Apex Logistics Data Pipeline: Feature Matrix Generator")
    print("=" * 60)
    
    con = initialize_database()
    
    # Run Part 0 Basics Warm-Up first
    part0_basics_warmup(con)
    
    # Run defensive verification
    verify_no_leakage(con)
    
    # Build and preview matrix
    matrix = build_feature_matrix(con)
    print("\nFeature Matrix Sample Preview:")
    matrix.show()
    
    # Export to Parquet
    os.makedirs("output", exist_ok=True)
    matrix.write_parquet("output/feature_matrix.parquet")
    print("Successfully exported feature matrix to output/feature_matrix.parquet")



if __name__ == "__main__":
    main()
```

---

## 3. Grading Rubric & Scoring Criteria (100 Points Total)

| Criteria | Exemplary (Full Points) | Competent (Partial Points) | Developing (Needs Revision) | Points |
|---|---|---|---|---|
| **1. Temporal Leakage Prevention (ASOF Join)** | The `ASOF JOIN` is constructed correctly with `dep_time >= obs_time`. Automated assertions pass with zero future timestamp contamination. | Join executes, but inequality is inverted or calendar dates are used instead of timestamps, causing minor leakage. | Standard `LEFT JOIN` used without time boundaries, introducing catastrophic look-ahead bias. | **30** |
| **2. Rolling Window Isolation (Lag Features)** | Rolling driver statistics strictly utilize `ROWS BETWEEN N PRECEDING AND 1 PRECEDING`. Current row is never included in input feature computation. | Window function partitions correctly, but uses `CURRENT ROW` for feature calculation, causing label leakage. | Window functions omitted or syntax produces runtime errors. | **25** |
| **3. Pipeline Execution & Output Format** | Standalone script executes cleanly without human intervention; outputs valid `output/feature_matrix.parquet` with correct schema. | Script runs, but requires manual file path tweaks or exports only flat uncompressed CSV. | Script fails to execute due to unhandled Python or DuckDB syntax errors. | **20** |
| **4. Defensive Null & Edge Case Handling** | Uses `COALESCE` to provide sensible physical defaults for routes with no prior weather history or first-time drivers. | Leaves unexpected `NULL` values across continuous feature columns. | Script crashes on missing values or unhandled joins. | **15** |
| **5. Code Quality & Standards** | Professional Python/SQL formatting: uppercase SQL keywords, descriptive column aliases, clear docstrings, and modular design. | Minor style violations (mixed case keywords, cryptic column names, missing comments). | Unformatted monolithic script; no documentation or explanatory comments. | **10** |
| **Total** | | | | **100** |
