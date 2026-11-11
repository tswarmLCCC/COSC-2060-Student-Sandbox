# Unit 2: Required Readings, Concepts & Video Lectures

Welcome to the core instructional lecture and study hub for **Unit 2: The Anomaly Engine & Unsupervised Learning Targets**. This page organizes all weekly learning materials into four structured chapters:

1. **Instructor Lecture & Conceptual Deep Dive:** Master the mathematical mechanics of distance metrics, the "Ruler Distortion" mental model, Polars multithreaded Arrow memory layouts, and streaming LazyFrames for anomaly detection.
2. **Required Readings & Authoritative Tutorial Guides:** Study curated official documentation from the Polars Rust project, Scikit-Learn outlier detection guides, and Apache Arrow zero-copy memory specifications.
3. **Required Micro-Video Lectures (Embedded):** Watch high-definition video chapters with verified timestamp navigation to observe high-throughput streaming DataFrames in live Python environments.
4. **Institutional Video Lecture Embeds:** Access campus-specific video recordings and announcements uploaded by your instructor.

*Work through each section in sequence as part of your 150-minute asynchronous self-study allocation before starting the applied laboratory assignment.*

---

## 1. Instructor Lecture & Conceptual Deep Dive

### High-Throughput Feature Pipelines: The Polars Engine & Unsupervised Outliers

#### 1. Unit Overview & Objectives
In Unit 1, we tackled supervised learning targets. You learned how to bridge the gap between relational databases and feature matrices using DuckDB, avoiding look-ahead bias with point-in-time `ASOF` joins.

In **Unit 2**, we pivot to **unsupervised learning targets** and **scale**.

In enterprise industry, the vast majority of raw operational data does **not** arrive with ground-truth labels. Nobody tags fraudulent credit card transactions, failing wind turbine bearings, or network intrusions in real time. Instead, data engineers must construct high-throughput pipelines that clean, normalize, and transform millions of raw event logs into high-dimensional feature spaces where **unsupervised anomaly detection algorithms** (such as Isolation Forests) can mathematically isolate outliers.

Furthermore, we confront the performance limits of traditional Python tools. In introductory machine learning courses, students typically use **Pandas** for everything. On small datasets (10,000 to 50,000 rows), Pandas functions adequately. But when an enterprise pipeline ingests **1,000,000 transactions a day**, Pandas consumes massive amounts of RAM, locks up CPU cores with Python's Global Interpreter Lock (GIL), and crashes with Out-Of-Memory (OOM) errors.

In this unit, you will replace Pandas with **Polars**—a blazing-fast, multithreaded DataFrame library written in Rust and built natively on the Apache Arrow columnar memory model.

**Measurable Learning Objectives:**
* **Analyze** the mathematical mechanics of distance metrics (Euclidean, Manhattan) and articulate why unscaled numerical features distort unsupervised anomaly detection models.
* **Implement** robust data normalization techniques (Min-Max scaling and Z-Score standardization) natively using vectorized Polars expressions.
* **Differentiate** between Pandas' eager object-pointer memory model and Polars' multithreaded Apache Arrow columnar execution architecture.
* **Construct** declarative, leak-free transformation pipelines using Polars **LazyFrames** (`pl.scan_parquet`, expressions, and streaming execution).
* **Ingest and Clean** 1,000,000 commercial fuel transaction records to feed an unsupervised Isolation Forest anomaly detection baseline.

---

#### 2. The Narrative of Data: The Ghost Fuel Card Ring ($2.4M Theft)
To appreciate why scaling and normalization matter, consider an authentic corporate logistics fraud case.

A nationwide freight carrier operated a fleet of 5,000 commercial long-haul trucks. Each driver was issued an automated fleet fuel credit card tied to their employee ID. Drivers swiped their cards at commercial travel centers (Love's, Pilot Flying J, TravelCenters of America) to refuel their Class 8 diesel semi-trucks.

Every month, the company processed approximately **1.2 million fuel transaction records**. To prevent fraud, the accounting department ran a nightly Python script using Pandas. The script calculated basic summary statistics and flagged any transaction where `transaction_amount > $1,200`.

The system seemed fine. For two years, zero major alerts were triggered.

##### The $2.4 Million Discovery
During an external audit, forensic accountants discovered that a syndicate of 14 rogue drivers had stolen **$2.4 million in fuel** over an 18-month period. 

How did they bypass the data pipeline?

1. **The Tank Siphon Exploit**: A standard Class 8 semi-truck holds dual fuel tanks with a combined physical capacity of **300 gallons**. At $3.80 per gallon, a full tank costs approximately **$1,140**. The rogue drivers pulled into travel plazas, pumped 250 gallons into their truck, and then pumped an extra **150 gallons into hidden 55-gallon drums** in their trailer, logging 400 gallons for **$1,520**. But they asked the fuel clerk to split the swipe into two separate charges: **$760 and $760**. The naive Pandas filter (`amount > $1,200`) never blinked.
2. **The Cloned Card Teleportation**: One driver sold cloned duplicates of his fuel card to accomplices in different states. At **1:15 PM**, the driver swiped his card in Cheyenne, Wyoming. At **2:00 PM** (45 minutes later), his cloned card was swiped in Dallas, Texas—**950 miles away**. 
   - A commercial semi-truck has a maximum governed speed of 75 mph. Moving 950 miles in 45 minutes implies an impossible speed of **1,266 mph**!
   - Because the data pipeline analyzed transactions in isolation without calculating time-series velocities across consecutive driver swipes, the fraud went completely undetected.

```
THE TELEPORTATION EXPLOIT:
13:15 PM ── Station ST-WY-01 (Cheyenne, WY) ── 180 Gallons Diesel ($684.00)
14:00 PM ── Station ST-TX-22 (Dallas, TX)   ── 210 Gallons Diesel ($798.00)
Delta Time: 45 minutes (0.75 hours)
Delta Distance: 950 miles
Implied Velocity: 1,266 mph! <── PHYSICAL IMPOSSIBILITY!
```

##### Why Pandas Failed the Engineering Team
When the junior data engineer tried to write a new script in Pandas that sorted the 1.2 million transactions by driver and calculated rolling velocity vectors and z-scores, the script **crashed the server with an Out-of-Memory (OOM) error**. 

Pandas attempted to allocate **8.4 GB of RAM** to hold Python objects, ran a single-threaded Python `.apply()` loop that pegged 1 CPU core at 100% for 45 minutes, and was terminated by the Linux kernel's Out-Of-Memory Killer (`Killed: 9`).

This is why modern data engineering has moved beyond Pandas. We need engines that process millions of records in seconds while mathematically standardizing features for machine learning.

---

#### 3. The Mental Model: "The Ruler Distortion" (Why Scaling Matters)
Before writing code, let's examine why unnormalized features destroy unsupervised anomaly detection algorithms.

Imagine you are designing a surveillance system to detect abnormal physical objects. You measure two features:
* $X_1$: **Height** (measured in millimeters, e.g. 1,750 mm to 1,900 mm).
* $X_2$: **Weight** (measured in metric tons, e.g. 0.07 tons to 0.09 tons).

Now calculate the standard Euclidean distance between Person A (1,800 mm, 0.08 tons) and Person B (1,850 mm, 0.08 tons):
$$d = \sqrt{(1850 - 1800)^2 + (0.08 - 0.08)^2} = \sqrt{2500 + 0} = 50.0$$

Now calculate the distance between Person A (1,800 mm, 0.08 tons) and Person C (1,800 mm, 0.04 tons — an extreme medical anomaly who weighs half as much as normal):
$$d = \sqrt{(1800 - 1800)^2 + (0.04 - 0.08)^2} = \sqrt{0 + 0.0016} = 0.04$$

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

In data engineering pipelines, every numerical column destined for distance-based ML or tree-based anomaly detection must be standardized ($z = \frac{x - \mu}{\sigma}$) or min-max scaled ($x_{scaled} = \frac{x - x_{min}}{x_{max} - x_{min}}$).

---

#### 4. The Architectural Model: Pandas vs. Polars (Apache Arrow)
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

#### 5. Guided Implementation Walkthrough: Vectorized Outlier Detection with Polars

Here is how you build a production-grade, leak-free anomaly detection feature pipeline in Polars:

```python
import polars as pl
import numpy as np

# 1. Initialize LazyFrame scan over raw fuel transaction log
transactions = pl.DataFrame({
    "trans_id": [1001, 1002, 1003, 1004, 1005],
    "driver_id": [42, 42, 99, 42, 99],
    "gallons": [120.0, 380.0, 110.0, 125.0, 410.0],
    "amount_usd": [456.0, 1444.0, 418.0, 475.0, 1558.0],
    "implied_speed_mph": [45.2, 185.0, 52.0, 48.0, 58.0]
})

# 2. Vectorized Polars Expressions for Standardization and Anomaly Scoring
engineered_features = transactions.with_columns([
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

#### 6. Common Traps & Formative Self-Check FAQ

* **Question 1: What is the difference between `pl.DataFrame` and `pl.LazyFrame`?**  
  *Answer:* A `DataFrame` executes computations immediately in memory (eager). A `LazyFrame` (created via `pl.scan_parquet()` or `.lazy()`) does not load data into RAM immediately. Instead, it builds an execution query plan that Polars optimizes before executing when `.collect()` is called.

* **Question 2: Why not compute mean and standard deviation on the whole dataset including test splits?**  
  *Answer:* Computing scaling statistics on the combined dataset causes **data snooping leakage**. Scaling parameters ($\mu$ and $\sigma$) must always be calculated strictly on the training partition and applied identically to the inference partition.

---

## 2. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical specifications before beginning your applied lab:

1. **[Polars User Guide: Streaming Lazy API](https://docs.pola.rs/user-guide/concepts/streaming/)**
   *Learn how Polars processes datasets larger than available RAM by streaming data in chunks through multithreaded pipelines.*

2. **[Polars User Guide: Expressions & Vectorization](https://docs.pola.rs/user-guide/concepts/expressions/)**
   *Understand how Polars writes declarative columnar transformations executed concurrently across CPU cores without Python overhead.*

3. **[Scikit-Learn User Guide: Novelty and Outlier Detection](https://scikit-learn.org/stable/modules/outlier_detection.html)**
   *Master the theoretical and practical foundations of Isolation Forest, Local Outlier Factor (LOF), and One-Class SVM.*

4. **[Apache Arrow In-Memory IPC & Zero-Copy Format](https://arrow.apache.org/docs/python/ipc.html)**
   *Understand the physical binary layout of Arrow record batches and how zero-copy transfer eliminates serialization overhead.*

5. **[Polars vs. Pandas Architectural Benchmark](https://docs.pola.rs/user-guide/getting-started/)**
   *Explore the core design differences, memory footprint comparisons, and performance benchmarks between Polars and Pandas.*

---

## 3. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to observe high-performance DataFrames and outlier detection algorithms in practice:

### Polars: The Next Big Python Data Science Library <span style="font-size: 0.9em; color: #64748b;">(Full Walkthrough - 12:45)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Polars Python Tutorial" src="https://www.youtube.com/embed/VHqn7ufiilE" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=VHqn7ufiilE" target="_blank" rel="noopener">Open video segment in new tab (12:45)</a></p>

### Apache Arrow: Zero-Copy In-Memory Analytics <span style="font-size: 0.9em; color: #64748b;">(Architecture Overview - 9:30)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Apache Arrow Architecture" src="https://www.youtube.com/embed/5gXn5fLkbM0?start=180" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=5gXn5fLkbM0&amp;t=180s" target="_blank" rel="noopener">Open video segment in new tab (3:00)</a></p>

### DuckDB & Polars: Modern Data Stack Synergy <span style="font-size: 0.9em; color: #64748b;">(Full Video - 10:15)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Modern Data Stack with Polars" src="https://www.youtube.com/embed/uHm6FEb2Re4" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=uHm6FEb2Re4" target="_blank" rel="noopener">Open video segment in new tab (2:12)</a></p>

---

## 4. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for Unit 2 will appear in this designated container.</p>
</div>
