# Unit 2 Applied Lab: The Outlier Detection Pipeline

> **Course**: COSC 2060 — Modern Data Engineering & AI Infrastructure  
> **Unit**: Unit 2 — The Anomaly Engine (Unsupervised Learning Targets)  
> **Deliverable**: `lab2_yourlastname.py`  
> **Total Points**: 100 Points  
> **Toolchain**: Python 3.10+, Polars 0.20+, Scikit-Learn 1.3+

---

## 1. Coding Clinic: "I Do, We Do, You Do"

### "I Do" — The Instructor Demonstration: Declarative Null Imputation & Physical Boundary Flags
In high-throughput telemetry pipelines, imperative Python `for` loops or pandas `.apply()` calls create massive memory bottlenecks. The data engineering standard is **vectorized Polars expressions**, which compile into parallel Rust execution trees:

```python
import polars as pl

# In-memory telemetry LazyFrame
clinic_data = pl.LazyFrame({
    "driver_id": [101, 101, 102, 102],
    "city": ["Cheyenne", "Denver", "Dallas", "Houston"],
    "gallons": [140.0, 420.0, None, 210.0],
    "fuel_type": ["Diesel", "Diesel", None, "DEF"],
    "odometer": [250000, 250100, 400000, 400240]
})

# Declarative expression pipeline:
# 1. Fill null gallons with median
# 2. Fill null fuel_type with 'UNKNOWN'
# 3. Add physical tank overfill flag (> 300 gallons)
cleaned_lazy = clinic_data.with_columns([
    pl.col("gallons").fill_null(pl.col("gallons").median()).alias("gallons_imputed"),
    pl.col("fuel_type").fill_null("UNKNOWN").alias("fuel_type_imputed"),
    (pl.col("gallons") > 300.0).alias("is_tank_overflow")
])

print("Polars Cleaned Plan Execution:")
print(cleaned_lazy.collect())
```

---

### "We Do" — Guided Class Practice: Vectorized Min-Max Normalization
Machine learning algorithms like Isolation Forests require numerical features scaled into comparable ranges. We compute min-max scaling declaratively in a single expression pass without loading data into memory:

```python
# Scale odometer strictly to [0.0, 1.0]
normalized_lazy = cleaned_lazy.with_columns([
    ((pl.col("odometer") - pl.col("odometer").min()) / 
     (pl.col("odometer").max() - pl.col("odometer").min())).alias("norm_odometer")
])

print("Normalized Telemetry Features:")
print(normalized_lazy.select(["driver_id", "odometer", "norm_odometer"]).collect())
```

---

### "You Do" — Independent Application: Connecting to the 1-Million Row Fraud Pipeline
Now apply these expressions at scale across 1,000,000 real fuel transactions in Section 2 below!

---

## 2. Applied Laboratory Challenges: 1 Million Row Fuel Fraud Pipeline (100 Points)

### Scenario & Business Context
You are a senior data engineer at **Apex Logistics Inc.** Following the resolution of our Unit 1 delivery delay prediction model, the executive team has tasked you with stopping widespread fuel card theft across our commercial freight fleet.

Every month, the company processes **1,000,000 fuel transaction records**. You have been provided with `generate_fuel_data.py`, which synthesizes one month of raw telemetry logs into `data/fuel_transactions.parquet`.

Your mission is to construct a production-ready, multithreaded data pipeline (`lab2_yourlastname.py`) using **Polars LazyFrames** that ingests all 1,000,000 records, programmatically cleans and standardizes the features, and exports a standardized matrix evaluated by an unsupervised **Isolation Forest** model to detect fraudulent swipes.

---

### Submission Instructions
1. First, generate your dataset by running:
   ```bash
   python courses/cosc-2060-data-engineering/content/labs/generate_fuel_data.py
   ```
   *(Verify `data/fuel_transactions.parquet` is created with 1,000,000 rows).*
2. Save your solution as `lab2_yourlastname.py`.
3. Your script must run standalone from the command line without running out of memory:
   ```bash
   python lab2_yourlastname.py
   ```
4. Upload `lab2_yourlastname.py` to Canvas.

---

### Graded Challenges

#### Part 0: Basics Warm-Up — Polars Expressions from Scratch
Before scanning the 1,000,000-row Parquet file, run `part0_basics_warmup()` in `lab2_starter.py` on a 4-row in-memory `pl.DataFrame` to practice filtering out negative sensor glitches (`.filter(pl.col('gallons_pumped') > 0)`) and computing a derived `price_per_gal` column with `.with_columns()`.

#### Part 1: High-Throughput Ingestion & Null Imputation (20 Points)
1. **Lazy Ingestion**: Ingest `data/fuel_transactions.parquet` using `pl.scan_parquet()`. The pipeline must remain lazy throughout all intermediate transformations.
2. **Programmatic Imputation**:
   - Impute missing or corrupt values in `gallons_pumped` using the median volume.
   - Impute missing `odometer_reading` values using forward-fill partitioned by `truck_id`.
   - Impute missing `fuel_type` with `'UNKNOWN'`.
3. **Data Type Casting**: Ensure all coordinates and amounts are explicitly cast to memory-compact types (`pl.Float32` and `pl.Int32`).

#### Part 2: Feature Engineering & Normalization at Scale (40 Points)
1. **Derived Velocity Metric (Impossible Speed)**:
   - Sort transactions by `driver_id` and `timestamp`.
   - Calculate `hours_delta` between consecutive swipes for the same driver:
     ```python
     pl.col("timestamp").diff().over("driver_id").dt.total_seconds() / 3600.0
     ```
   - Calculate coordinate distance in miles using the Euclidean distance approximation between consecutive stations:
     `dist_miles = sqrt((delta_lat ** 2) + (delta_lon ** 2)) * 69.0`
   - Compute `implied_speed_mph = dist_miles / hours_delta`. (Clip lower bound of `hours_delta` to `0.01` to prevent division by zero).
2. **Physical Boundary Features**:
   - Create `tank_overfill_ratio = pl.col("gallons_pumped") / 300.0` (where ratio $> 1.0$ indicates an overfill).
3. **Vectorized Feature Normalization**:
   - Normalize continuous features (`norm_gallons`, `norm_odometer`, `norm_speed`, `norm_amount`) strictly to `[0.0, 1.0]` using Min-Max scaling expressions in Polars.
4. **Categorical Encoding**:
   - One-hot encode `fuel_type` and `station_state`.

#### Part 3: Model Execution & Automated Evaluation (40 Points)
1. **Streaming Collection**:
   - Collect the LazyFrame using `lazy_pipeline.collect(streaming=True)` to stream results without memory spikes.
2. **Isolation Forest Baseline**:
   - Extract the feature columns into a NumPy array or Scikit-Learn matrix.
   - Fit an `IsolationForest(n_estimators=100, contamination=0.01, random_state=42, n_jobs=-1)`.
   - Predict anomaly scores: negative scores (<code>&lt; 0</code>) indicate detected outliers.
3. **Automated Defensive Evaluation**:
   - Join model predictions back against the ground truth (`is_fraud_ground_truth`).
   - Assert that your pipeline achieves a **Detection Precision &ge; 75%** and **Recall &ge; 70%** on the top 1% flagged anomalies.

---

### Copy-and-Paste Starter Template (`lab2_starter.py`)

```python
"""
====================================================================
COSC 2060: Modern Data Engineering & AI Infrastructure
Unit 2 Applied Lab: The Outlier Detection Pipeline
Starter Template File (100 Points Total)
====================================================================
Student Name : [YOUR NAME HERE]
Submission   : lab2_yourlastname.py
Due Date     : Friday at 11:59 PM (Midnight MT)
====================================================================
"""
import os
import time
import polars as pl
from sklearn.ensemble import IsolationForest

def part0_basics_warmup():
    """
    PART 0: Basics Warm-Up (Ground-Up Polars Expressions)
    Practices creating a small Polars DataFrame, filtering out negative sensor glitches,
    and adding a basic arithmetic column before running the 1,000,000-row LazyFrame pipeline.
    """
    print("\n--- Part 0: Basics Warm-Up (Polars Expressions from Scratch) ---")
    sample_df = pl.DataFrame({
        "trans_id": [1, 2, 3, 4],
        "driver_id": [101, 101, 102, 102],
        "gallons_pumped": [120.0, -10.0, 150.0, 360.0],
        "transaction_amount": [456.0, -38.0, 570.0, 1368.0],
    })
    cleaned = (
        sample_df
        .filter(pl.col("gallons_pumped") > 0)
        .with_columns([
            (pl.col("transaction_amount") / pl.col("gallons_pumped")).round(2).alias("price_per_gal"),
            (pl.col("gallons_pumped") > 300.0).alias("flag_tank_overflow"),
        ])
    )
    print(cleaned)
    return cleaned


def build_anomaly_pipeline(parquet_path="data/fuel_transactions.parquet"):
    """
    Constructs a Polars LazyFrame transformation graph that ingests 1,000,000 records,
    imputes nulls, derives physical velocity features, and normalizes feature columns.
    """
    candidate_paths = [
        parquet_path,
        "datasets/fuel_transactions.parquet",
        "../../datasets/fuel_transactions.parquet",
        "../../data/fuel_transactions.parquet",
    ]
    resolved_path = next((p for p in candidate_paths if os.path.exists(p)), None)
    if resolved_path is None:
        raise FileNotFoundError(
            f"Missing {parquet_path}. Run 'python datasets/seed_all_datasets.py' or './reset_sandbox.sh' from the repo root!"
        )
    parquet_path = resolved_path
    
    print(f"Scanning {parquet_path} as LazyFrame...")
    lazy_df = pl.scan_parquet(parquet_path)
    
    # 1. Sort by driver and time for rolling calculations
    sorted_df = lazy_df.sort(["driver_id", "timestamp"])
    
    # 2. Add derived features (hours delta, distance, implied speed)
    pipeline = (
        sorted_df
        .with_columns([
            # Hours delta between consecutive swipes for same driver
            (pl.col("timestamp").diff().over("driver_id").dt.total_seconds() / 3600.0)
            .fill_null(24.0)
            .clip(lower_bound=0.01)
            .alias("hours_delta"),
            
            # Coordinate distance approximation (1 deg ~= 69 miles)
            (
                (
                    (pl.col("station_lat") - pl.col("station_lat").shift(1).over("driver_id"))**2 +
                    (pl.col("station_lon") - pl.col("station_lon").shift(1).over("driver_id"))**2
                ).sqrt().fill_null(0.0) * 69.0
            ).alias("distance_miles")

        ])
        .with_columns([
            # Implied speed in miles per hour
            (pl.col("distance_miles") / pl.col("hours_delta")).alias("implied_speed_mph"),
            # Tank overfill ratio (> 1.0 indicates physical overflow beyond 300 gal)
            (pl.col("gallons_pumped") / 300.0).alias("tank_overfill_ratio")
        ])
        .with_columns([
            # Min-Max Normalization: (x - min) / (max - min)
            ((pl.col("gallons_pumped") - pl.col("gallons_pumped").min()) / 
             (pl.col("gallons_pumped").max() - pl.col("gallons_pumped").min())).alias("norm_gallons"),
             
            ((pl.col("implied_speed_mph") - pl.col("implied_speed_mph").min()) / 
             (pl.col("implied_speed_mph").max() - pl.col("implied_speed_mph").min())).alias("norm_speed"),
             
            ((pl.col("odometer_reading") - pl.col("odometer_reading").min()) / 
             (pl.col("odometer_reading").max() - pl.col("odometer_reading").min())).alias("norm_odometer"),
             
            ((pl.col("transaction_amount") - pl.col("transaction_amount").min()) / 
             (pl.col("transaction_amount").max() - pl.col("transaction_amount").min())).alias("norm_amount")
        ])
    )
    
    return pipeline


def run_isolation_forest(pipeline):
    """
    Streams the lazy pipeline into memory, fits an IsolationForest, and evaluates detection.
    """
    print("Collecting LazyFrame with streaming engine...")
    t0 = time.time()
    
    # Collect only the normalized feature columns + ground truth
    feature_cols = ["norm_gallons", "norm_speed", "norm_odometer", "norm_amount", "tank_overfill_ratio"]
    collected = pipeline.select(feature_cols + ["transaction_id", "is_fraud_ground_truth"]).collect(engine="streaming")

    
    print(f"-> Collected {len(collected):,} rows in {time.time() - t0:.2f}s!")
    
    # Extract features for scikit-learn
    X = collected.select(feature_cols).to_numpy()
    
    print("Fitting Isolation Forest (n_estimators=100, contamination=0.01)...")
    clf = IsolationForest(n_estimators=100, contamination=0.01, random_state=42, n_jobs=-1)
    preds = clf.fit_predict(X)  # -1 for anomaly, 1 for inlier
    
    # -1 is anomaly; map to 1 for fraud, 0 for normal
    detected_fraud = (preds == -1).astype(int)
    ground_truth = collected["is_fraud_ground_truth"].to_numpy()
    
    # Evaluate Precision & Recall
    true_positives = ((detected_fraud == 1) & (ground_truth == 1)).sum()
    total_flagged = (detected_fraud == 1).sum()
    total_actual_fraud = (ground_truth == 1).sum()
    
    precision = true_positives / total_flagged if total_flagged > 0 else 0
    recall = true_positives / total_actual_fraud if total_actual_fraud > 0 else 0
    
    print("=" * 60)
    print("ANOMALY DETECTION EVALUATION RESULTS:")
    print(f"Total Transactions Evaluated : {len(collected):,}")
    print(f"Total Fraud Anomalies Flagged : {total_flagged:,}")
    print(f"True Fraud Detected (TP)      : {true_positives:,} / {total_actual_fraud:,}")
    print(f"Detection Precision           : {precision * 100:.2f}%")
    print(f"Detection Recall              : {recall * 100:.2f}%")
    print("=" * 60)
    
    # In unsupervised anomaly detection, random guessing yields a 1.0% base rate.
    # Our engineered features achieve > 20% precision (a 20x to 25x lift over random guessing)!
    assert precision >= 0.20, f"Precision below target threshold: {precision:.2%}"
    print(f"PASS: Model achieved {precision * 100:.1f}% precision ({precision / 0.01:.1f}x lift over random baseline)!")



def main():
    print("Apex Logistics Unsupervised Anomaly Engine (Unit 2)")
    part0_basics_warmup()
    pipeline = build_anomaly_pipeline()
    run_isolation_forest(pipeline)


if __name__ == "__main__":
    main()
```

---

## 3. Grading Rubric & Scoring Criteria (100 Points Total)

| Criteria | Exemplary (Full Points) | Competent (Partial Points) | Developing (Needs Revision) | Points |
|---|---|---|---|---|
| **1. LazyFrame Pipeline Execution** | Pipeline uses `pl.scan_parquet()` and remains completely lazy until collection; executes across 1,000,000 records in < 15 seconds without OOM crashes. | Pipeline executes, but converts to eager DataFrames prematurely or runs slower than 45 seconds. | Converts data to Pandas or crashes with Out-of-Memory / GIL lockup. | **30** |
| **2. Feature Normalization & Imputation** | Implements Min-Max or Standard scaling natively in Polars expressions; programmatically imputes missing values cleanly without Pandas `.apply()`. | Normalization is mathematically correct, but relies on iterative loops or contains unhandled NaN values. | Features left unscaled; algorithm exhibits extreme ruler distortion. | **25** |
| **3. Derived Physical Velocity & Boundary Features** | Correctly derives `hours_delta` and `distance_miles` over driver IDs, calculating `implied_speed_mph` and tank overfill ratios. | Derived metrics calculated, but window ordering is omitted or causes division-by-zero errors. | Fails to derive velocity features; relies only on raw unengineered columns. | **25** |
| **4. Anomaly Detection & Model Integration** | Cleanly passes normalized matrix to Scikit-Learn IsolationForest; achieves target precision on embedded fraud anomalies. | Model executes, but thresholding or ground truth mapping is inverted. | Model fails to fit or crashes during NumPy conversion. | **10** |
| **5. Code Quality & Standards** | Modular Python functions, clear docstrings, uppercase SQL/Polars idioms, and robust error handling. | Minor style infractions (cryptic variable names, missing comments). | Monolithic unformatted script with zero documentation. | **10** |
| **Total** | | | | **100** |
