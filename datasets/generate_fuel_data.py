"""
====================================================================
COSC 2060: Modern Data Engineering & AI Infrastructure
Unit 2: Synthetic Logistics Fuel Transaction Generator
====================================================================
Generates 1,000,000 realistic commercial fleet fuel transaction records
with embedded fraud anomalies (~1% contamination rate) directly into
a high-performance Parquet file in under 10 seconds.

Usage:
    python datasets/generate_fuel_data.py
====================================================================
"""
import os
import shutil
import time
import duckdb


def generate_fuel_dataset(output_path="datasets/fuel_transactions.parquet", num_records=1_000_000):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    print(f"Generating {num_records:,} synthetic commercial fuel transactions...")
    start_time = time.time()

    con = duckdb.connect()

    # Leverage DuckDB's in-process vectorized engine to generate 1M records in < 5 seconds
    con.sql(f"""
    CREATE OR REPLACE TABLE raw_fuel AS
    WITH base_generator AS (
        SELECT 
            range::BIGINT + 1 AS transaction_id,
            -- Random timestamps across September 2026
            TIMESTAMP '2026-09-01 00:00:00' + 
                INTERVAL (CAST(FLOOR(random() * 2592000) AS INT)) SECOND AS timestamp,
            -- 400 active drivers (101 to 500)
            CAST(101 + FLOOR(random() * 400) AS INT) AS driver_id,
            -- 400 active commercial trucks (1001 to 1400)
            CAST(1001 + FLOOR(random() * 400) AS INT) AS truck_id,
            -- Stations across major western freight hubs
            (CASE CAST(FLOOR(random() * 5) AS INT)
                WHEN 0 THEN 'ST-WY-01'
                WHEN 1 THEN 'ST-CO-14'
                WHEN 2 THEN 'ST-UT-08'
                WHEN 3 THEN 'ST-TX-22'
                ELSE 'ST-NE-05'
             END) AS station_id,
            -- Station coordinates
            (CASE CAST(FLOOR(random() * 5) AS INT)
                WHEN 0 THEN 'Cheyenne'
                WHEN 1 THEN 'Denver'
                WHEN 2 THEN 'Salt Lake'
                WHEN 3 THEN 'Dallas'
                ELSE 'Omaha'
             END) AS station_city,
            -- Random base odometer reading (150,000 to 750,000 miles)
            CAST(150000 + FLOOR(random() * 600000) AS BIGINT) AS odometer_reading,
            -- Injected fraud flag (~1% contamination rate)
            (CASE WHEN random() < 0.010 THEN 1 ELSE 0 END) AS is_fraud_ground_truth,
            random() AS fraud_pattern_selector
        FROM range({num_records})
    )
    SELECT 
        transaction_id,
        timestamp,
        driver_id,
        truck_id,
        station_id,
        station_city,
        -- Coordinates mapped to cities
        (CASE station_city
            WHEN 'Cheyenne'  THEN 41.1399::FLOAT
            WHEN 'Denver'    THEN 39.7392::FLOAT
            WHEN 'Salt Lake' THEN 40.7608::FLOAT
            WHEN 'Dallas'    THEN 32.7767::FLOAT
            ELSE 41.2565::FLOAT
         END) AS station_lat,
        (CASE station_city
            WHEN 'Cheyenne'  THEN -104.8202::FLOAT
            WHEN 'Denver'    THEN -104.9903::FLOAT
            WHEN 'Salt Lake' THEN -111.8910::FLOAT
            WHEN 'Dallas'    THEN -96.7970::FLOAT
            ELSE -95.9345::FLOAT
         END) AS station_lon,
        -- State
        (CASE station_city
            WHEN 'Cheyenne'  THEN 'WY'
            WHEN 'Denver'    THEN 'CO'
            WHEN 'Salt Lake' THEN 'UT'
            WHEN 'Dallas'    THEN 'TX'
            ELSE 'NE'
         END) AS station_state,
        -- Fuel type: 90% Diesel, 8% DEF (Diesel Exhaust Fluid), 2% Regular Gas
        (CASE 
            WHEN random() < 0.90 THEN 'Diesel'
            WHEN random() < 0.98 THEN 'DEF'
            ELSE 'Regular_Gas'
         END) AS fuel_type,
        -- Gallons pumped:
        -- Normal: 50 to 240 gallons (semi tank capacity = 300)
        -- Fraud Pattern 1: Tank Capacity Violation (350 to 580 gallons pumped into secondary drums)
        (CASE 
            WHEN is_fraud_ground_truth = 1 AND fraud_pattern_selector < 0.40 
            THEN CAST(350.0 + random() * 230.0 AS FLOAT)
            ELSE CAST(50.0 + random() * 190.0 AS FLOAT)
         END) AS gallons_pumped,
        -- Price per gallon (market rates)
        CAST(3.45 + random() * 0.85 AS FLOAT) AS unit_price,
        odometer_reading,
        is_fraud_ground_truth
    FROM base_generator;
    """)

    # Export directly to Parquet with Snappy compression
    con.sql(f"""
    COPY (
        SELECT 
            transaction_id,
            timestamp,
            driver_id,
            truck_id,
            station_id,
            station_city,
            station_state,
            station_lat,
            station_lon,
            fuel_type,
            ROUND(gallons_pumped, 2)::FLOAT AS gallons_pumped,
            ROUND(unit_price, 2)::FLOAT AS unit_price,
            ROUND(gallons_pumped * unit_price, 2)::FLOAT AS transaction_amount,
            odometer_reading,
            is_fraud_ground_truth
        FROM raw_fuel
        ORDER BY timestamp ASC
    ) TO '{output_path}' (FORMAT PARQUET, COMPRESSION SNAPPY);
    """)

    # Also mirror to data/fuel_transactions.parquet for convenience when running from root
    os.makedirs("data", exist_ok=True)
    if os.path.abspath(output_path) != os.path.abspath("data/fuel_transactions.parquet"):
        shutil.copy2(output_path, "data/fuel_transactions.parquet")

    elapsed = time.time() - start_time
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"-> SUCCESS: Generated {num_records:,} rows in {elapsed:.2f} seconds!")
    print(f"-> Output file: {output_path} ({file_size_mb:.2f} MB)")

    # Audit summary
    summary = con.sql(f"""
    SELECT 
        count(*) AS total_rows,
        sum(is_fraud_ground_truth) AS fraud_rows,
        round(sum(is_fraud_ground_truth)::FLOAT / count(*) * 100, 2) AS fraud_pct,
        round(avg(gallons_pumped), 2) AS avg_gallons,
        round(max(gallons_pumped), 2) AS max_gallons
    FROM '{output_path}';
    """).fetchall()[0]
    print(f"-> Audit: Total = {summary[0]:,}, Fraud Records = {summary[1]:,} ({summary[2]}%), Max Gallons = {summary[4]}")


if __name__ == "__main__":
    generate_fuel_dataset()

