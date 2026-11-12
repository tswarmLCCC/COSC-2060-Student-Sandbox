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
