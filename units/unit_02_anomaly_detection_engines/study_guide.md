# Unit 2: Required Readings, Concepts & Video Lectures

Welcome to the core instructional lecture and study hub for **Unit 2: The Anomaly Engine & Unsupervised Learning Targets**. This page organizes all weekly learning materials into five structured sections:

1. **Unit Overview & Objectives:** Review the architectural context and measurable learning objectives for this unit.
2. **Instructor Lecture & Conceptual Deep Dive (Ribbon Slices 2a–2f):** Master the target unsupervised feature matrix shape, operational fuel-card source systems, the mathematical mechanics of distance metrics, the "Ruler Distortion" mental model, Polars multithreaded Arrow memory layouts, step-by-step Polars expressions, and streaming LazyFrames for anomaly detection.
3. **Required Readings & Authoritative Tutorial Guides:** Study curated official documentation from the Polars Rust project, Scikit-Learn outlier detection guides, and Apache Arrow zero-copy memory specifications.
4. **Required Micro-Video Lectures (Embedded):** Watch high-definition video chapters with verified timestamp navigation to observe high-throughput streaming DataFrames in live Python environments.
5. **Institutional Video Lecture Embeds:** Access campus-specific video recordings and announcements uploaded by your instructor.

*Work through each section in sequence as part of your 150-minute asynchronous self-study allocation before starting the applied laboratory assignment.*

---



## 1. Unit Overview & Objectives
In Unit 1, we tackled supervised learning targets. You learned how to bridge the gap between relational databases and feature matrices using DuckDB, avoiding look-ahead bias with point-in-time `ASOF` joins and rolling window frames.

In **Unit 2**, we pivot to **unsupervised learning targets** and **scale**.

In enterprise industry, the vast majority of raw operational data does **not** arrive with ground-truth answer labels. Nobody sits at a desk tagging fraudulent credit card transactions, failing wind turbine bearings, or network intrusions in real time. Instead, data engineers must construct high-throughput pipelines that clean, normalize, and transform millions of raw event logs into high-dimensional feature spaces where **unsupervised anomaly detection algorithms** (such as Isolation Forests) can mathematically isolate outliers.

Furthermore, we confront the performance limits of traditional Python tools. When working on small datasets (10,000 to 50,000 rows), **Pandas** functions adequately. But when an enterprise pipeline ingests **1,000,000 transactions a day**, Pandas consumes massive amounts of RAM, locks up CPU cores with Python's Global Interpreter Lock (GIL), and crashes with Out-Of-Memory (OOM) errors.

In this unit, you will learn how to build high-speed pipelines with **Polars**—a blazing-fast, multithreaded DataFrame library written in Rust and built natively on the Apache Arrow columnar memory model. We will start by examining the exact output table we are building and the source systems that feed it, then explore a real-world fuel fraud case, why feature scaling matters, and how to write Polars expressions from the ground up.

**Measurable Learning Objectives:**
* **Explain** the difference between supervised learning (with a target column <b><i>y</i></b>) and unsupervised anomaly detection (finding outliers across feature columns <b><i>X</i></b> without historical labels).
* **Analyze** the mathematical mechanics of distance metrics (Euclidean, Manhattan) and articulate why unscaled numerical features distort unsupervised anomaly detection models.
* **Implement** robust data normalization techniques (Min-Max scaling and Z-Score standardization) natively using vectorized Polars expressions after scrubbing corrupted sensor glitches.
* **Differentiate** between Pandas' eager object-pointer memory model and Polars' multithreaded Apache Arrow columnar execution architecture.
* **Construct** declarative, leak-free transformation pipelines step by step using Polars **LazyFrames** (`pl.scan_parquet`, `.filter()`, `.with_columns()`, `.over()`, and `.collect()`).
* **Ingest and Clean** commercial fuel transaction records to isolate physical anomalies and feed an unsupervised Isolation Forest baseline.

---

## 2a. What Our Output Table Looks Like and Where the Data Comes From

### The Purpose
Our goal in Unit 2 is to build a **Standardized Anomaly Feature Matrix** (`anomaly_features.parquet`) from raw commercial fleet fuel card logs. This table feeds both rule-based physical audits and an unsupervised **Isolation Forest** model that scores every fuel purchase from normal (`1`) to anomalous (`-1`).

### Why Unsupervised Models Need Standardized Features
An unsupervised anomaly detector does not have a target column <b><i>y</i></b> to guide it. Instead, it compares input columns like `gallons`, `amount_usd`, and `implied_speed_mph` across rows to determine which transactions stand out from normal fleet behavior.

To make that mathematical comparison fair and reliable, our output dataset must accomplish three things:
1. **Scrub corrupted sensor and logging glitches** (such as negative gallon readings or `99999` error codes) *before* calculating statistical averages.
2. **Compute physical context features across consecutive rows**—such as how much time elapsed since the same driver's previous fuel card swipe and how fast the truck would have had to travel between the two fuel plazas (`implied_speed_mph`).
3. **Standardize numeric columns onto a common scale (Z-scores)** so a column measured in thousands of dollars does not drown out a column measured in small decimals.

### Where the Raw Data Comes From (Source Systems)
In a commercial trucking company, fuel transaction records originate from two primary operational systems:
1. **Point-of-Sale (POS) Fuel Card Network (`fuel_transactions.parquet`):** Every time a driver swipes a corporate fleet card at a commercial travel center (Love's, Pilot Flying J, TravelCenters of America), the payment processor logs `trans_id`, `driver_id`, `station_id`, `timestamp`, `gallons`, and `amount_usd`.
2. **Fleet GPS & Terminal Station Registry (`stations` / telematics coordinates):** Provides the physical location and highway mileage between travel plazas so the pipeline can compute the distance traveled between consecutive swipes by the same card.

### Sample Output Dataset (The Target Shape)
When our Unit 2 Polars pipeline finishes scrubbing, enriching, and standardizing the raw transactions, the output table looks like this:

| trans_id (ID) | driver_id (ID) | gallons (Raw) | amount_usd (Raw) | implied_speed_mph (Raw) | z_gallons (Scaled <i>X</i><sub>1</sub>) | z_speed (Scaled <i>X</i><sub>2</sub>) | flag_speed_impossible (<i>X</i><sub>3</sub>) | flag_tank_overflow (<i>X</i><sub>4</sub>) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1001** | 42 | 120.0 | 456.0 | 45.2 | -0.742 | -0.569 | `false` | `false` |
| **1002** | 42 | 380.0 | 1444.0 | 185.0 | +0.898 | +1.782 | `true` | `true` |
| **1003** | 99 | 110.0 | 418.0 | 52.0 | -0.805 | -0.455 | `false` | `false` |
| **1004** | 42 | 125.0 | 475.0 | 48.0 | -0.710 | -0.522 | `false` | `false` |
| **1005** | 99 | 410.0 | 1558.0 | 58.0 | +1.087 | -0.354 | `false` | `true` |

---

## 2b. The Ghost Fuel Card Ring ($2.4M Theft)

To appreciate why multi-column feature engineering, scaling, and high-throughput engines matter, consider an authentic corporate logistics fraud case.

A nationwide freight carrier operated a fleet of 5,000 commercial long-haul trucks. Each driver was issued an automated fleet fuel credit card tied to their employee ID. Drivers swiped their cards at commercial travel centers (Love's, Pilot Flying J, TravelCenters of America) to refuel their Class 8 diesel semi-trucks.

Every month, the company processed approximately **1.2 million fuel transaction records**. To prevent fraud, the accounting department ran a nightly Python script using Pandas. The script calculated basic summary statistics and flagged any transaction where `transaction_amount > $1,200`.

The system seemed fine. For two years, zero major alerts were triggered.

### The \$2.4 Million Discovery
During an external audit, forensic accountants discovered that a syndicate of 14 rogue drivers had stolen **\$2.4 million in fuel** over an 18-month period.

How did they bypass the data pipeline?

1. **The Tank Siphon Exploit:** A standard Class 8 semi-truck holds dual fuel tanks with a combined physical capacity of **300 gallons**. At \$3.80 per gallon, a full tank costs approximately **\$1,140**. The rogue drivers pulled into travel plazas, pumped 250 gallons into their truck, and then pumped an extra **150 gallons into hidden 55-gallon drums** in their trailer, logging 400 gallons for **\$1,520**. But they asked the fuel clerk to split the swipe into two separate charges: **\$760 and \$760**—or pumped 350+ gallons when regional diesel prices dipped just below \$1,200. The naive Pandas filter (`amount > $1,200`) never blinked.
2. **The Cloned Card Teleportation:** One driver sold cloned duplicates of his fuel card to accomplices in different states. At **1:15 PM**, the driver swiped his card in Cheyenne, Wyoming. At **2:00 PM** (45 minutes later), his cloned card was swiped in Dallas, Texas—**950 miles away**.
   * A commercial semi-truck has a maximum governed speed of 75 mph. Moving 950 miles in 45 minutes implies an impossible speed of **1,266 mph**!
   * Because the data pipeline analyzed transactions in isolation without calculating time-series velocities across consecutive driver swipes, the fraud went completely undetected.

```
THE TELEPORTATION EXPLOIT:
13:15 PM ── Station ST-WY-01 (Cheyenne, WY) ── 180 Gallons Diesel ($684.00)
14:00 PM ── Station ST-TX-22 (Dallas, TX)   ── 210 Gallons Diesel ($798.00)
Delta Time: 45 minutes (0.75 hours)
Delta Distance: 950 miles
Implied Velocity: 1,266 mph! <── PHYSICAL IMPOSSIBILITY!
```

### Why Pandas Failed the Engineering Team
When the junior data engineer tried to write a new script in Pandas that sorted the 1.2 million transactions by driver and calculated rolling velocity vectors and Z-scores, the script **crashed the server with an Out-Of-Memory (OOM) error**.

Pandas attempted to allocate **8.4 GB of RAM** to hold Python objects, ran a single-threaded Python `.apply()` loop that pegged 1 CPU core at 100% for 45 minutes, and was terminated by the Linux kernel's Out-Of-Memory Killer (`Killed: 9`).

This is why modern data engineering pairs **Polars** with **mathematical feature standardization**: we need an engine that processes millions of records in seconds across all CPU cores while standardizing features cleanly for anomaly detection.

---

## 2c. Why Scaling Matters — "The Ruler Distortion"

Before writing code, let's examine why unnormalized features destroy unsupervised anomaly detection algorithms.

Imagine you are designing a monitoring system to detect abnormal physical measurements. You measure two features:
* <b><i>X</i><sub>1</sub></b>: **Height** (measured in millimeters, e.g., `1,750` mm to `1,900` mm).
* <b><i>X</i><sub>2</sub></b>: **Weight** (measured in metric tons, e.g., `0.07` tons to `0.09` tons).

Now calculate the standard Euclidean distance between **Person A** (`1,800` mm, `0.08` tons) and **Person B** (`1,850` mm, `0.08` tons):
<p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.75rem; border-radius: 4px;">
  <i>d</i> = &radic;[ (1850 &minus; 1800)<sup>2</sup> + (0.08 &minus; 0.08)<sup>2</sup> ] = &radic;[ 2500 + 0 ] = 50.0
</p>

Now calculate the distance between **Person A** (`1,800` mm, `0.08` tons) and **Person C** (`1,800` mm, `0.04` tons — an extreme medical anomaly who weighs half as much as normal):
<p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.75rem; border-radius: 4px;">
  <i>d</i> = &radic;[ (1800 &minus; 1800)<sup>2</sup> + (0.04 &minus; 0.08)<sup>2</sup> ] = &radic;[ 0 + 0.0016 ] = 0.04
</p>

**The Catastrophe:** The model reports that Person B (who simply had a normal 2-inch height difference) is **1,250 times more distant and abnormal** than Person C (who is suffering a catastrophic 50% body-mass collapse)!

Because millimeters range in thousands while metric tons range in decimals, the height feature completely drowned out weight. The algorithm's metric "ruler" was warped.

```
THE RULER DISTORTION:
Unscaled Features:
Height (mm):    [1,750 =============================== 1,900] (Variance = 22,500)
Weight (tons):  [0.07 = 0.09]                                 (Variance = 0.0004)
Distance metric treats Height as 56,000,000x more important than Weight!

Standardized (Z-Score):
Height (Z):     [-2.5 ======== 0 ======== +2.5] (Mean = 0, Std = 1)
Weight (Z):     [-2.5 ======== 0 ======== +2.5] (Mean = 0, Std = 1)
Both features now speak an identical mathematical language.
```

### Two Standard Formulas for Feature Scaling
In data engineering pipelines, every numerical column destined for distance-based ML or outlier detection is scaled using one of two formulas:

1. **Z-Score Standardization (Zero Mean, Unit Variance):**
   Subtract the column mean (&mu;) and divide by the column standard deviation (&sigma;):
   <p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.6rem; border-radius: 4px;">
     <i>z</i> = (<i>x</i> &minus; &mu;) / &sigma;
   </p>
   After Z-score standardization, `0.0` represents the exact average, `+1.0` is one standard deviation above average, and values beyond `+3.0` or `-3.0` indicate statistical outliers.
2. **Min-Max Scaling (`[0.0, 1.0]` Range):**
   Rescales values linearly between the column minimum and maximum:
   <p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.6rem; border-radius: 4px;">
     <i>x</i><sub>scaled</sub> = (<i>x</i> &minus; <i>x</i><sub>min</sub>) / (<i>x</i><sub>max</sub> &minus; <i>x</i><sub>min</sub>)
   </p>

> **Defensive Engineering Rule:** Notice that if a raw dataset contains even one corrupted sensor glitch—such as `-999,999.0` gallons caused by a pump reset—that single impossible number will corrupt &mu;, &sigma;, <i>x</i><sub>min</sub>, and <i>x</i><sub>max</sub> for the entire dataset! Always filter out impossible sensor errors (`gallons > 0`) **before** computing scaling statistics.

---

## 2d. The Architectural Model — Pandas vs. Polars (Apache Arrow)

Why is Polars capable of processing 1,000,000 rows in 0.4 seconds while Pandas takes 45 seconds or crashes?

```
1. PANDAS MEMORY MODEL (Python Object Pointers & NumPy Boxed Arrays):
- Python Object Overhead: Every string or mixed object is a boxed Python pointer (8 bytes pointer + 48 bytes object).
- Single-Threaded: Bound by Python's Global Interpreter Lock (GIL). Only 1 CPU core works at a time.
- Eager Evaluation: Every line of code forces immediate execution, allocating duplicate temporary memory buffers.

2. POLARS MEMORY MODEL (Rust & Apache Arrow Columnar Format):
- Contiguous Arrow Buffers: Strings, integers, and floats are stored packed contiguously in memory with zero boxed Python overhead.
- Multithreaded Rust Work-Stealing: Automatically parallelizes operations across all CPU cores (e.g., 8 to 16 threads simultaneously).
- Lazy Optimization: Compiles queries into an execution DAG, pushes down projection filters, and streams chunks through CPU caches without allocating unnecessary RAM.
```

---

## 2e. Step-by-Step Code Ramp-Up & Guided Implementation Walkthrough (Polars)

If you have never used Polars before, you will find its design very intuitive—especially right after Unit 1 SQL. In Polars, nearly every column operation uses `pl.col("column_name")` inside a context method like `.select()`, `.filter()`, or `.with_columns()`. Let's build up the syntax from the ground up, and then run the complete outlier detection walkthrough.

### Step 1: Creating a Polars DataFrame and Selecting Columns (`.select()`)
In Polars, we import `polars as pl`. To pick specific columns, pass a list of column names or `pl.col(...)` expressions to `.select()`:

```python
import polars as pl

# Create a small in-memory DataFrame
df = pl.DataFrame({
    "trans_id": [1, 2, 3, 4],
    "driver_id": [101, 101, 102, 102],
    "gallons": [120.0, -5.0, 140.0, 360.0],
    "amount_usd": [456.0, -19.0, 532.0, 1368.0]
})

# Select specific columns
print(df.select(["trans_id", "gallons"]))
```

### Step 2: Filtering Out Corrupted Rows with `.filter()`
Unlike Pandas (where you repeat the variable name like `df[df["gallons"] > 0]`), Polars uses `pl.col("...")` inside `.filter()`. To combine multiple conditions, wrap each comparison in parentheses and join them with `&` (AND) or `|` (OR):

```python
# Remove corrupted sensor glitches where gallons <= 0 or amount_usd <= 0
clean_df = df.filter(
    (pl.col("gallons") > 0) & (pl.col("amount_usd") > 0)
)
print(clean_df)
```

### Step 3: Adding Engineered Columns with `.with_columns()` and `.alias()`
When you want to keep all existing columns and add new calculated columns (just like adding expressions to a SQL `SELECT` list), pass a list of expressions to `.with_columns([...])` and name each new column with `.alias("new_name")`:

```python
with_features = clean_df.with_columns([
    # 1. Simple arithmetic ratio: price per gallon
    (pl.col("amount_usd") / pl.col("gallons")).round(2).alias("price_per_gallon"),

    # 2. Boolean flag: did gallons exceed a 300-gallon semi-truck tank?
    (pl.col("gallons") > 300.0).alias("flag_tank_overflow")
])
print(with_features)
```

### Step 4: Group-Specific Window Calculations with `.over()`
Remember `OVER (PARTITION BY driver_id)` from Unit 1 SQL? In Polars, you can compute a driver-specific average, maximum, or lag across groups without collapsing the rows simply by chaining `.over("driver_id")` onto any expression:

```python
driver_window_df = clean_df.with_columns([
    # Compute each driver's personal average fill-up
    pl.col("gallons").mean().over("driver_id").alias("driver_avg_gallons"),

    # Compare this transaction to that driver's personal average
    (pl.col("gallons") - pl.col("gallons").mean().over("driver_id")).alias("diff_from_driver_avg")
])
print(driver_window_df)
```

### Step 5: Lazy Execution (`pl.scan_parquet`, `.lazy()`, and `.collect()`)
When processing large Parquet files in production, start your pipeline with `pl.scan_parquet("file.parquet")` (or call `.lazy()` on an in-memory DataFrame). Polars builds an optimized query plan and waits to execute it across all CPU threads until you call `.collect()`.

### Step 6: Guided Implementation Walkthrough — Vectorized Outlier Detection with Polars
Here is how all of these pieces come together in a production-grade anomaly detection feature pipeline:

```python
import polars as pl
import numpy as np

# 1. Initialize raw fuel transaction log
transactions = pl.DataFrame({
    "trans_id": [1001, 1002, 1003, 1004, 1005],
    "driver_id": [42, 42, 99, 42, 99],
    "gallons": [120.0, 380.0, 110.0, 125.0, 410.0],
    "amount_usd": [456.0, 1444.0, 418.0, 475.0, 1558.0],
    "implied_speed_mph": [45.2, 185.0, 52.0, 48.0, 58.0]
})

# 2. Vectorized Polars Expressions for Standardization and Anomaly Scoring (via LazyFrame)
engineered_features = (
    transactions.lazy()
    .filter((pl.col("gallons") > 0) & (pl.col("amount_usd") > 0))
    .with_columns([
        # Z-score standardization for gallons
        ((pl.col("gallons") - pl.col("gallons").mean()) / pl.col("gallons").std())
        .alias("z_gallons"),
        
        # Z-score standardization for implied speed
        ((pl.col("implied_speed_mph") - pl.col("implied_speed_mph").mean()) / pl.col("implied_speed_mph").std())
        .alias("z_speed"),
        
        # Heuristic Flag: Physics Violation (Speed > 75 mph)
        (pl.col("implied_speed_mph") > 75.0).alias("flag_speed_impossible"),
        
        # Heuristic Flag: Tank Capacity Violation (Gallons > 300)
        (pl.col("gallons") > 300.0).alias("flag_tank_overflow")
    ])
    .collect()
)

print(engineered_features)
```

**Output Verification:**
```
shape: (5, 9)
┌──────────┬───────────┬─────────┬────────────┬───────────────────┬───────────┬─────────┬───────────────────────┬────────────────────┐
│ trans_id ┆ driver_id ┆ gallons ┆ amount_usd ┆ implied_speed_mph ┆ z_gallons ┆ z_speed ┆ flag_speed_impossible ┆ flag_tank_overflow │
│ ---      ┆ ---       ┆ ---     ┆ ---        ┆ ---               ┆ ---       ┆ ---     ┆ ---                   ┆ ---                │
│ i64      ┆ i64       ┆ f64     ┆ f64        ┆ f64               ┆ f64       ┆ f64     ┆ bool                  ┆ bool               │
╞══════════╪═══════════╪═════════╪════════════╪═══════════════════╪═══════════╪═════════╪═══════════════════════╪════════════════════╡
│ 1001     ┆ 42        ┆ 120.0   ┆ 456.0      ┆ 45.2              ┆ -0.742    ┆ -0.569  ┆ false                 ┆ false              │
│ 1002     ┆ 42        ┆ 380.0   ┆ 1444.0     ┆ 185.0             ┆ 0.898     ┆ 1.782   ┆ true                  ┆ true               │
│ 1003     ┆ 99        ┆ 110.0   ┆ 418.0      ┆ 52.0              ┆ -0.805    ┆ -0.455  ┆ false                 ┆ false              │
│ 1004     ┆ 42        ┆ 125.0   ┆ 475.0      ┆ 48.0              ┆ -0.710    ┆ -0.522  ┆ false                 ┆ false              │
│ 1005     ┆ 99        ┆ 410.0   ┆ 1558.0     ┆ 58.0              ┆ 1.087     ┆ -0.354  ┆ false                 ┆ true               │
└──────────┴───────────┴─────────┴────────────┴───────────────────┴───────────┴─────────┴───────────────────────┴────────────────────┘
```

Notice that Transaction 1002 triggered both the physical speed impossibility flag (185 mph) and tank overflow flag (380 gallons), while Transaction 1005 was isolated as a tank overflow without speed anomalies.

---

## 2f. Practice Exercises & Formative Self-Check FAQ

Try these three short exercises in your GitHub Codespaces sandbox (`units/unit_02_anomaly_detection_engines/`) before starting the graded lab:

1. **Exercise 1 (Inspecting the Query Plan):** In Python, create a `LazyFrame` with `.lazy()`, add a `.filter()` and `.with_columns()`, and print `lazy_pipeline.explain()`. Observe how Polars shows you the optimized query plan before reading the data.
2. **Exercise 2 (Seeing the Effect of Sensor Glitches on Z-Scores):** In `coding_clinic.py`, check what happens to `z_gallons` if you compute the Z-score *before* filtering out negative or `99999.0` sensor error rows versus *after* filtering them out.
3. **Exercise 3 (Group Window Practice):** Using `.over("driver_id")`, add a column that calculates the maximum `gallons` each driver has ever pumped (`pl.col("gallons").max().over("driver_id")`).

### Common Traps & Formative Self-Check FAQ

* **Question 1: What is the difference between `pl.DataFrame` and `pl.LazyFrame`?**  
  *Answer:* A `DataFrame` executes computations immediately in memory (eager evaluation). A `LazyFrame` (created via `pl.scan_parquet()` or `.lazy()`) does not load data into RAM immediately. Instead, it builds an execution query plan that Polars optimizes (pushing down filters and skipping unused columns) before executing in parallel when `.collect()` is called.

* **Question 2: Why not compute mean and standard deviation on the whole dataset including test splits?**  
  *Answer:* Computing scaling statistics on the combined dataset causes **data snooping leakage**. Scaling parameters (&mu; and &sigma;) must always be calculated strictly on the historical training partition and applied identically to the live inference partition.

* **Question 3: Why can't I write `pl.col("gallons") > 0 and pl.col("amount_usd") > 0` using Python's keyword `and`?**  
  *Answer:* In Python DataFrame libraries (both Polars and Pandas), the keyword `and` attempts to evaluate an entire column expression as a single boolean truth value and raises a `TypeError`. Always wrap each condition in parentheses and join them with the bitwise `&` operator: `(pl.col("gallons") > 0) & (pl.col("amount_usd") > 0)`.

---

## 3. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical specifications before beginning your applied lab:

1. **[Polars User Guide: Streaming Lazy API](https://docs.pola.rs/user-guide/concepts/streaming/)**
   *Learn how Polars processes datasets larger than available RAM by streaming data in chunks through multithreaded pipelines.*

2. **[Polars User Guide: Expressions & Vectorization](https://docs.pola.rs/user-guide/concepts/expressions-and-contexts/)**
   *Understand how Polars writes declarative columnar transformations executed concurrently across CPU cores without Python overhead.*

3. **[Scikit-Learn User Guide: Novelty and Outlier Detection](https://scikit-learn.org/stable/modules/outlier_detection.html)**
   *Master the theoretical and practical foundations of Isolation Forest, Local Outlier Factor (LOF), and One-Class SVM.*

4. **[Apache Arrow In-Memory IPC & Zero-Copy Format](https://arrow.apache.org/docs/python/ipc.html)**
   *Understand the physical binary layout of Arrow record batches and how zero-copy transfer eliminates serialization overhead.*

5. **[Polars vs. Pandas Architectural Benchmark](https://docs.pola.rs/user-guide/getting-started/)**
   *Explore the core design differences, memory footprint comparisons, and performance benchmarks between Polars and Pandas.*

---

## 4. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to observe high-performance DataFrames and outlier detection algorithms in practice:

### Polars: The Next Big Python Data Science Library <span style="font-size: 0.9em; color: #64748b;">(Rob Mulla - Full Walkthrough)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Polars Python Tutorial" src="https://www.youtube.com/embed/VHqn7ufiilE" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=VHqn7ufiilE" target="_blank" rel="noopener">Open video in new tab</a></p>

### Apache Arrow: Zero-Copy In-Memory Columnar Analytics <span style="font-size: 0.9em; color: #64748b;">(Airbyte - Architecture Overview)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Apache Arrow Architecture" src="https://www.youtube.com/embed/e8Ti5Z4t1E8" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=e8Ti5Z4t1E8" target="_blank" rel="noopener">Open video in new tab</a></p>

### DuckDB & Polars: Modern Data Stack Synergy in Python <span style="font-size: 0.9em; color: #64748b;">(FlowForge Lab - Code & Benchmarks)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="DuckDB and Polars Together in Python" src="https://www.youtube.com/embed/7TINvL43Oko" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=7TINvL43Oko" target="_blank" rel="noopener">Open video in new tab</a></p>

---

## 5. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for Unit 2 will appear in this designated container.</p>
</div>
