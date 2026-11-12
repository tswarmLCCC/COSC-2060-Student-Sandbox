# Unit 2: Required Readings, Concepts & Video Lectures

Welcome to the instructional reading and study guide for **Unit 2: Anomaly Detection & Polars Pipelines**. This page organizes the week's learning materials into four sections:

1. **Instructor Lecture & Conceptual Deep Dive:** Learn how unsupervised outlier detection works, what our standardized output dataset looks like, why unscaled features distort distance calculations, how Polars processes large tables in parallel, and how to build a Polars pipeline step by step.
2. **Required Readings & Tutorial Guides:** Explore official documentation from the Polars project, Scikit-Learn outlier detection guides, and Apache Arrow memory specifications.
3. **Required Micro-Video Lectures (Embedded):** Watch focused video tutorials demonstrating Polars expressions, LazyFrames, and Apache Arrow.
4. **Institutional Video Lecture Embeds:** Access instructor announcements and lab walkthrough recordings.

*Work through each section in sequence as part of your 150-minute self-study block before starting the applied lab.*

---

## 1. Instructor Lecture & Conceptual Deep Dive

### Finding Outliers When You Have No Labels

In Unit 1, we built a dataset for **supervised learning**: every historical trip in our table had a known answer (`target_delay_mins`) on the far right column so a model could learn to predict delays.

In **Unit 2**, we tackle a very different problem: **what do you do when your data does not have answer labels?**

In day-to-day industry operations, most raw event logs arrive without labels. Nobody sits at a desk tagging fraudulent fuel card swipes, failing wind turbine bearings, or abnormal server traffic in real time. Instead, we have millions of normal records mixed with a tiny fraction of suspicious records. To catch those unusual events automatically, we use **unsupervised anomaly detection**—algorithms that measure how far each record sits from typical behavior.

We also introduce **Polars**, a fast, multithreaded Python DataFrame library written in Rust and built on Apache Arrow. Whenever a dataset grows to hundreds of thousands or millions of rows, Polars lets you filter, group, and standardize columns across all CPU cores without running out of memory.

#### Measurable Learning Objectives
* **Explain** the difference between supervised learning (with a target column <b><i>y</i></b>) and unsupervised anomaly detection (finding outliers across feature columns <b><i>X</i></b> without historical labels).
* **Demonstrate** why unscaled numeric columns distort distance-based models and standardize features using Z-Scores (`z = (x - mean) / std`) and Min-Max scaling.
* **Compare** single-threaded Pandas DataFrames with Polars' multithreaded Apache Arrow execution model and `LazyFrame` query planner.
* **Build** a step-by-step Polars feature pipeline using `pl.scan_parquet()`, `.filter()`, `.with_columns()`, `.over()`, and `.collect()`.
* **Clean and Standardize** commercial fuel card transactions to isolate physical anomalies and feed an unsupervised Isolation Forest model.

---

### What Our Output Table Looks Like and Where the Data Comes From

#### The Purpose
Our goal in Unit 2 is to build a **Standardized Anomaly Feature Matrix** (`anomaly_features.parquet`) from raw commercial fleet fuel card logs. This table feeds both rule-based safety audits and an unsupervised **Isolation Forest** model that scores every fuel purchase from normal (`1`) to anomalous (`-1`).

#### Why Unsupervised Models Need Standardized Features
An unsupervised anomaly detector does not have a target column to guide it. Instead, it compares columns like `gallons_pumped`, `transaction_amount`, and `implied_speed_mph` to see which rows stand out from the crowd.

To do that fairly, our output table must do three things:
1. **Remove corrupted sensor/logging glitches** (such as negative gallon readings or missing card IDs) before calculating averages.
2. **Compute physical context features across consecutive rows**—such as how many hours elapsed since the same driver's previous fuel swipe and how fast the truck would have had to travel between the two fuel stations (`implied_speed_mph`).
3. **Standardize numeric columns onto the same scale (Z-scores)** so a column measured in thousands of dollars does not drown out a column measured in small decimals.

#### Where the Raw Data Comes From (Source Systems)
In a commercial trucking company, fuel transaction logs come from two main systems:
1. **Point-of-Sale (POS) Fuel Card Network (`fuel_transactions.parquet`):** Every time a driver swipes a company fuel card at a travel plaza (Pilot, Love's, TA), the payment processor logs `transaction_id`, `driver_id`, `station_id`, `timestamp`, `gallons`, and `amount_usd`.
2. **Fleet GPS & Terminal Registry (`stations` / telematics coordinates):** Provides the city, state, and mile-marker distance between fuel stations so the pipeline can compute the distance traveled between consecutive swipes.

#### Sample Output Dataset (The Target Shape)
When our Unit 2 Polars pipeline finishes cleaning and standardizing the raw transactions, the output table looks like this:

| trans_id (ID) | driver_id (ID) | gallons (Raw) | implied_speed_mph (Raw) | z_gallons (Scaled <i>X</i><sub>1</sub>) | z_speed (Scaled <i>X</i><sub>2</sub>) | flag_tank_overflow (<i>X</i><sub>3</sub>) | flag_speed_impossible (<i>X</i><sub>4</sub>) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1001** | 42 | 120.0 | 55.2 | -0.45 | -0.28 | `false` | `false` |
| **1002** | 42 | 380.0 | 185.0 | +2.84 | +3.91 | `true` | `true` |
| **1003** | 99 | 110.0 | 52.0 | -0.58 | -0.38 | `false` | `false` |
| **1004** | 42 | 125.0 | 48.0 | -0.39 | -0.51 | `false` | `false` |
| **1005** | 99 | 410.0 | 58.0 | +3.22 | -0.19 | `true` | `false` |

---

### How Fuel Card Fraud Slipped Past a Simple Filter

To see why we need multi-column features and proper scaling, let's look at a real fraud pattern from commercial freight operations.

A trucking company operated 5,000 semi-trucks. Every driver carried a company fuel card. Each month, the company processed 1.2 million fuel card swipes. To watch for theft, the accounting team ran a simple nightly script that flagged any single purchase where `amount_usd > 1200`.

For nearly two years, that simple filter caught almost nothing. Then an external audit uncovered that a group of drivers had stolen **$2.4 million in diesel fuel** using two methods:

1. **Splitting Large Fill-Ups:** A standard Class 8 semi-truck has fuel tanks that hold at most **300 gallons** total. Drivers were pulling up to fuel islands, pumping 250 gallons into their truck, and pumping another 150 gallons into hidden drums inside their trailer (400 gallons total, costing \$1,520). To beat the \$1,200 rule, they simply hung up the nozzle halfway through and swiped the card twice for \$760 each—or pumped 350 gallons when diesel prices dipped just enough to stay under \$1,200.
2. **Cloned Cards Used Across State Lines:** One driver gave a cloned copy of his magnetic fuel card to an accomplice. At **1:15 PM**, the driver fueled his truck in Cheyenne, Wyoming. At **2:00 PM** (45 minutes later), the cloned card was swiped in Dallas, Texas—**950 miles away**.

```
TIMELINE OF CONSECUTIVE SWIPES FOR DRIVER #42:
01:15 PM ── Station WY-01 (Cheyenne, WY) ── 180 Gallons ($684.00)
02:00 PM ── Station TX-22 (Dallas, TX)   ── 210 Gallons ($798.00)
Time Elapsed:      45 minutes (0.75 hours)
Distance Traveled: 950 miles
Implied Speed:     950 miles / 0.75 hours = 1,266 mph!
```

Neither swipe exceeded \$1,200 on its own, so the old filter missed both. Catching this requires looking at **relationships between rows** (distance divided by time between consecutive swipes per driver) and **relationships across columns** (gallons vs. driver average).

When a developer tried to compute those rolling features across 1.2 million rows using a single-threaded Pandas `.apply()` loop, the script used over 8 GB of RAM and crashed the server. That brings us to two core engineering concepts: **feature scaling** and **Polars columnar execution**.

---

### Why Unscaled Features Distort Distance Models

Before feeding numeric columns into an anomaly detector or clustering model, we have to make sure every column is measured on a comparable scale.

Suppose you are comparing two measurements for each person in a medical dataset:
* **Feature 1 (`height_mm`):** Measured in millimeters (for example, `1,750` mm to `1,900` mm).
* **Feature 2 (`weight_tons`):** Measured in metric tons (for example, `0.07` tons to `0.09` tons).

Many anomaly detectors compare rows using straight-line (**Euclidean**) distance:
<p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.75rem; border-radius: 4px;">
  distance = &radic;[ (<i>x</i><sub>1</sub> &minus; <i>y</i><sub>1</sub>)<sup>2</sup> + (<i>x</i><sub>2</sub> &minus; <i>y</i><sub>2</sub>)<sup>2</sup> ]
</p>

Look at what happens when we compare three people using raw, unscaled units:
* **Person A vs. Person B** (Person B is 50 mm—about 2 inches—taller, with the exact same weight):
  `distance = sqrt((1850 - 1800)^2 + (0.08 - 0.08)^2) = sqrt(2500 + 0) = 50.0`
* **Person A vs. Person C** (Person C has the exact same height, but weighs `0.04` tons—half of normal body weight, a severe medical emergency):
  `distance = sqrt((1800 - 1800)^2 + (0.04 - 0.08)^2) = sqrt(0 + 0.0016) = 0.04`

Because millimeters are written in thousands (`1800`) and metric tons are written in tiny decimals (`0.08`), the distance formula treats a normal 2-inch height difference (`50.0`) as **1,250 times larger** than a 50% weight loss (`0.04`)!

```
UNSCALED FEATURES (WARPED RULER):
Height (mm):    [1,750 =============================== 1,900] (Spread = 150)
Weight (tons):  [0.07 = 0.09]                                 (Spread = 0.02)
Result: Height dominates the math; Weight is ignored!

Z-SCORE STANDARDIZED FEATURES (FAIR RULER):
Height (Z):     [-2.0 ======== 0.0 ======== +2.0] (Mean = 0, Std Dev = 1)
Weight (Z):     [-2.0 ======== 0.0 ======== +2.0] (Mean = 0, Std Dev = 1)
Result: A 2-standard-deviation jump in either column has the exact same weight.
```

#### Two Standard Ways to Scale Features
1. **Z-Score Standardization (Zero Mean, Unit Variance):**
   For every value `x` in a column, subtract the column's average (`mean`, written as &mu;) and divide by the column's standard deviation (`std`, written as &sigma;):
   <p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.6rem; border-radius: 4px;">
     <i>z</i> = (<i>x</i> &minus; &mu;) / &sigma;
   </p>
   After Z-score scaling, `0.0` means "exactly average," `+1.0` means "one standard deviation above average," and anything beyond `+3.0` or `-3.0` is an extreme statistical outlier.
2. **Min-Max Normalization (0 to 1 Range):**
   Squeezes all values in a column between `0.0` (the minimum) and `1.0` (the maximum):
   <p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.6rem; border-radius: 4px;">
     <i>x</i><sub>scaled</sub> = (<i>x</i> &minus; <i>x</i><sub>min</sub>) / (<i>x</i><sub>max</sub> &minus; <i>x</i><sub>min</sub>)
   </p>

> **Important Note on Outliers:** Notice that if a raw column has one corrupted sensor glitch—say a fuel pump software bug logs `-999,999` gallons—that single glitch will ruin the `mean`, `std`, `min`, and `max` for the entire table! Always filter out impossible sensor errors **before** computing Z-scores or Min-Max scales.

---

### How Polars Differs from Pandas

Why do data engineers use **Polars** when working with large tabular files in Python?

```
1. PANDAS EXECUTION MODEL:
- Single-Core Execution: Most Pandas operations run on a single CPU thread.
- Eager Step-by-Step Copies: Every time you filter or add a column, Pandas immediately allocates a brand-new copy of the DataFrame in RAM.
- Python String Overhead: Text columns often store separate Python object pointers for every cell.

2. POLARS EXECUTION MODEL (Rust + Apache Arrow):
- Multi-Core Parallelism: Polars automatically splits work across all available CPU cores.
- Apache Arrow Memory: Columns are stored in contiguous byte arrays with zero Python object overhead.
- Lazy Query Optimization (LazyFrame): When you use pl.scan_parquet(), Polars waits until you call .collect() so it can combine filters, skip unused columns, and process the file in a single pass.
```

---

### Step-by-Step Code Ramp-Up: Polars from the Ground Up

If you have never used Polars before, don't worry—its syntax is very similar to SQL. Every transformation uses `pl.col("column_name")` inside a context method like `.select()`, `.filter()`, or `.with_columns()`. Let's build up the syntax step by step.

#### Step 1: Creating a Polars DataFrame and Selecting Columns
In Polars, we import `polars as pl`. To pick specific columns, use `.select()`:

```python
import polars as pl

# Create a small in-memory DataFrame
df = pl.DataFrame({
    "trans_id": [1, 2, 3, 4],
    "driver_id": [101, 101, 102, 102],
    "gallons": [120.0, -5.0, 140.0, 360.0],
    "amount_usd": [456.0, -19.0, 532.0, 1368.0]
})

# Select just trans_id and gallons
print(df.select(["trans_id", "gallons"]))
```

#### Step 2: Filtering Rows with `.filter()`
Unlike Pandas (where you repeat the DataFrame name like `df[df["gallons"] > 0]`), Polars uses `pl.col("...")` inside `.filter()`. To combine multiple conditions, wrap each condition in parentheses and join them with `&` (AND) or `|` (OR):

```python
# Remove corrupted sensor rows where gallons <= 0 or amount_usd <= 0
clean_df = df.filter(
    (pl.col("gallons") > 0) & (pl.col("amount_usd") > 0)
)
print(clean_df)
```

#### Step 3: Adding Engineered Columns with `.with_columns()`
When you want to keep all existing columns and add new calculated columns (just like adding expressions to a SQL `SELECT` list), use `.with_columns([...])` and give each new column a name with `.alias("new_name")`:

```python
with_features = clean_df.with_columns([
    # 1. Simple arithmetic feature: price per gallon
    (pl.col("amount_usd") / pl.col("gallons")).round(2).alias("price_per_gallon"),

    # 2. Boolean flag feature: did gallons exceed a 300-gallon semi-truck tank?
    (pl.col("gallons") > 300.0).alias("flag_tank_overflow"),

    # 3. Z-score standardization of gallons across the table
    ((pl.col("gallons") - pl.col("gallons").mean()) / pl.col("gallons").std()).alias("z_gallons")
])
print(with_features)
```

#### Step 4: Group-Specific Calculations with `.over()` (Polars Window Functions)
Remember `OVER (PARTITION BY driver_id)` from Unit 1 SQL? In Polars, you can compute a driver's personal average or previous row value by adding `.over("driver_id")` to any expression!

```python
driver_features = clean_df.with_columns([
    # Compute each driver's personal average gallons
    pl.col("gallons").mean().over("driver_id").alias("driver_avg_gallons"),

    # Compare this fill-up to the driver's personal average
    (pl.col("gallons") - pl.col("gallons").mean().over("driver_id")).alias("diff_from_driver_avg")
])
print(driver_features)
```

#### Step 5: Using `LazyFrame` (`pl.scan_parquet` and `.collect()`)
When reading a Parquet file in a production pipeline, use `pl.scan_parquet("path.parquet")` instead of `pl.read_parquet()`.
* `pl.scan_parquet()` returns a `LazyFrame`: it checks the column names and types without loading the whole file into RAM yet.
* You chain `.filter()` and `.with_columns()` onto the `LazyFrame`.
* Finally, you call `.collect()` to run the optimized plan and produce the finished `DataFrame`, and `.write_parquet()` to save it:

```python
import polars as pl

# 1. Start a lazy scan (or convert a DataFrame with .lazy())
lazy_pipeline = (
    clean_df.lazy()
    .filter(pl.col("gallons") > 0)
    .with_columns([
        ((pl.col("gallons") - pl.col("gallons").mean()) / pl.col("gallons").std())
        .alias("z_gallons"),
        (pl.col("gallons") > 300.0).alias("flag_tank_overflow")
    ])
)

# 2. Execute the lazy query plan and return a materialized DataFrame
result_df = lazy_pipeline.collect()
print(result_df)
```

---

### Practice Exercises and Common Questions

Try these three short exercises in your GitHub Codespaces sandbox (`units/unit_02_anomaly_detection_engines/`) before starting the graded lab:

1. **Exercise 1 (Inspecting the Query Plan):** In Python, create a `LazyFrame` with `.lazy()`, add a `.filter()` and `.with_columns()`, and print `lazy_pipeline.explain()`. Observe how Polars shows you the optimized query plan before reading the data.
2. **Exercise 2 (Seeing the Effect of Sensor Glitches on Z-Scores):** In `coding_clinic.py`, check what happens to `z_gallons` if you compute the Z-score *before* filtering out negative or `99999.0` sensor error rows versus *after* filtering them out.
3. **Exercise 3 (Group Window Practice):** Using `.over("driver_id")`, add a column that calculates the maximum `gallons` each driver has ever pumped (`pl.col("gallons").max().over("driver_id")`).

#### Common Questions & Troubleshooting

* **Question 1: What happens if I forget to call `.collect()` on a `LazyFrame`?**  
  *Answer:* If you print a `LazyFrame` directly without calling `.collect()`, Python will just print `<LazyFrame ...>` instead of the rows and numbers, because the query hasn't been executed yet. Call `.collect()` whenever you are ready to run the pipeline and get the resulting `DataFrame`.

* **Question 2: Why can't I write `pl.col("gallons") > 0 and pl.col("amount_usd") > 0` using Python's word `and`?**  
  *Answer:* In Python DataFrame libraries (both Polars and Pandas), the word `and` tries to evaluate a whole column as a single True/False value and raises a `TypeError`. Always wrap each comparison in parentheses and join them with the `&` symbol: `(pl.col("gallons") > 0) & (pl.col("amount_usd") > 0)`.

* **Question 3: Why shouldn't I calculate the mean and standard deviation across both training and future test data together?**  
  *Answer:* Just like in Unit 1, using future test rows to calculate your scaling numbers (&mu; and &sigma;) leaks future distribution information into your training data. In production pipelines, you compute the mean and standard deviation on your historical training window and apply those exact numbers to incoming records.

---

## 2. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical references before beginning your applied lab:

1. **[Polars User Guide: Streaming Lazy API](https://docs.pola.rs/user-guide/concepts/streaming/)**
   *Learn how Polars processes datasets larger than available RAM by streaming data in chunks through multithreaded pipelines.*

2. **[Polars User Guide: Expressions & Vectorization](https://docs.pola.rs/user-guide/concepts/expressions-and-contexts/)**
   *Understand how Polars writes declarative columnar transformations executed concurrently across CPU cores.*

3. **[Scikit-Learn User Guide: Novelty and Outlier Detection](https://scikit-learn.org/stable/modules/outlier_detection.html)**
   *Explore the practical foundations of Isolation Forest, Local Outlier Factor (LOF), and One-Class SVM.*

4. **[Apache Arrow In-Memory IPC & Zero-Copy Format](https://arrow.apache.org/docs/python/ipc.html)**
   *Understand the physical binary layout of Arrow record batches and how zero-copy transfer speeds up analytics.*

5. **[Polars Getting Started Guide](https://docs.pola.rs/user-guide/getting-started/)**
   *Review the core syntax patterns (`select`, `filter`, `with_columns`, `group_by`) in Polars.*

---

## 3. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to see Polars DataFrames and columnar execution in practice:

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

## 4. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for Unit 2 will appear in this designated container.</p>
</div>
