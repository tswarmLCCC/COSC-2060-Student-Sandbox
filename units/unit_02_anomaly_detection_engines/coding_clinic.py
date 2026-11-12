"""
====================================================================
COSC 2060: Modern Data Engineering & AI Infrastructure
Unit 2 Synchronous Coding Clinic ("I Do, We Do, You Do")
Topic: The Anomaly Engine & Vectorized LazyFrames
====================================================================
Run this script from the terminal to execute the live class walkthrough
demonstrations:
    python units/unit_02_anomaly_detection_engines/coding_clinic.py
====================================================================
"""


# ====================================================================
# PART 0: BASICS WARM-UP — POLARS SELECT, FILTER & WITH_COLUMNS
# ====================================================================
print("\n>>> Executing PART 0: BASICS WARM-UP (Polars Expressions from Scratch)...")
import polars as pl

warmup_df = pl.DataFrame({
    "trans_id": [1, 2, 3],
    "gallons": [100.0, -5.0, 200.0],
    "amount_usd": [380.0, -19.0, 760.0]
})
# 1. Filter out negative sensor glitches with .filter(pl.col(...) > 0)
# 2. Add a basic calculated column with .with_columns()
warmup_clean = (
    warmup_df
    .filter(pl.col("gallons") > 0)
    .with_columns([
        (pl.col("amount_usd") / pl.col("gallons")).round(2).alias("price_per_gallon")
    ])
)
print("Part 0 Warm-Up — Basic Polars Filter & Calculated Column:")
print(warmup_clean)


# ====================================================================
# PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION
# ====================================================================
print("\n>>> Executing PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION...")

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


# ====================================================================
# PART 2: 'WE DO' — GUIDED CLASS PRACTICE
# ====================================================================
print("\n>>> Executing PART 2: 'WE DO' — GUIDED CLASS PRACTICE...")
# Scale odometer strictly to [0.0, 1.0]
normalized_lazy = cleaned_lazy.with_columns([
    ((pl.col("odometer") - pl.col("odometer").min()) / 
     (pl.col("odometer").max() - pl.col("odometer").min())).alias("norm_odometer")
])

print("Normalized Telemetry Features:")
print(normalized_lazy.select(["driver_id", "odometer", "norm_odometer"]).collect())

