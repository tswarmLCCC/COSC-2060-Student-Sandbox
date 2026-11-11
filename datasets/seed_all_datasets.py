"""
====================================================================
COSC 2060: Modern Data Engineering & AI Infrastructure
Master Sandbox Dataset Seeder (seed_all_datasets.py)
====================================================================
Populates all starter datasets required across Units 1 through 8:
  1. Unit 1: datasets/apex_logistics.duckdb (drivers, routes, weather_observations)
  2. Unit 2: datasets/fuel_transactions.parquet & data/fuel_transactions.parquet (1M rows)
  3. Unit 3: datasets/raw_fleet_images/ (synthetic 16:9 & 4:3 inspection photos)
  4. Unit 4: datasets/maintenance_logs.txt (raw unstructured shop bay repair logs)

Usage:
    python datasets/seed_all_datasets.py
====================================================================
"""
import os
import json
import duckdb
import numpy as np
import cv2
from generate_fuel_data import generate_fuel_dataset


def seed_unit1_duckdb(db_path="datasets/apex_logistics.duckdb"):
    """Seeds the persistent DuckDB operational database for Unit 1."""
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)

    print(f"[1/4] Seeding Unit 1 DuckDB database at {db_path}...")
    con = duckdb.connect(db_path)

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
    con.close()
    print("   -> Seeded tables: drivers (4), routes (5), weather_observations (6).")


def seed_unit3_vision_images(img_dir="datasets/raw_fleet_images"):
    """Generates multi-resolution synthetic gate camera inspection images for Unit 3."""
    print(f"[3/4] Generating Unit 3 synthetic inspection images in {img_dir}...")
    os.makedirs(img_dir, exist_ok=True)

    # Image 1: 16:9 widescreen 1920x1080
    img1 = np.full((1080, 1920, 3), (80, 80, 80), dtype=np.uint8)
    cv2.circle(img1, (960, 540), 200, (255, 255, 255), -1)
    cv2.imwrite(os.path.join(img_dir, "truck_101_tire_front.jpg"), img1)

    # Image 2: 4:3 standard 1200x900
    img2 = np.full((900, 1200, 3), (60, 60, 60), dtype=np.uint8)
    cv2.circle(img2, (600, 450), 180, (200, 200, 200), -1)
    cv2.imwrite(os.path.join(img_dir, "truck_102_tire_rear.jpg"), img2)

    annotations = {
        "truck_101_tire_front.jpg": [{"class_name": "Sidewall_Crack", "box": [860, 440, 1060, 640]}],
        "truck_102_tire_rear.jpg": [{"class_name": "Rim_Damage", "box": [500, 350, 700, 550]}]
    }
    with open(os.path.join(img_dir, "annotations.json"), "w", encoding="utf-8") as f:
        json.dump(annotations, f, indent=2)
    print("   -> Generated 2 multi-aspect inspection images + annotations.json.")


def seed_unit4_maintenance_logs(log_path="datasets/maintenance_logs.txt"):
    """Writes raw unstructured maintenance technician logs for Unit 4 RAG ingestion."""
    print(f"[4/4] Writing Unit 4 unstructured maintenance logs to {log_path}...")
    raw_dump = """--- LOG_START ---
WORK_ORDER: WO-10023
TRUCK_ID: TRUCK-101
DATE: 2026-10-01
SEVERITY: CRITICAL
NOTES: Driver reported sudden loss of boost pressure climbing I-80 Sherman Hill grade. Inspection revealed hairline thermal fatigue fractures along the high-pressure turbocharger actuator housing and severe exhaust manifold gasket scorching. Reference OEM Safety Recall Bulletin #SR-994-B for immediate turbine replacement protocol.
--- LOG_END ---
--- LOG_START ---
WORK_ORDER: WO-10024
TRUCK_ID: TRUCK-204
DATE: 2026-10-03
SEVERITY: ROUTINE
NOTES: Completed scheduled 50,000-mile preventative maintenance interval. Drained primary crankcase synthetic diesel oil, replaced dual spin-on fuel water separators, and verified steer axle brake lining thickness at 11mm.
--- LOG_END ---
--- LOG_START ---
WORK_ORDER: WO-10025
TRUCK_ID: TRUCK-101
DATE: 2026-10-09
SEVERITY: HIGH
NOTES: Secondary diagnostic bay check following Cheyenne terminal alert. Detected metallic harmonic whining at 1,850 RPM originating from the variable geometry turbocharger vane assembly. Cross-checked against Recall Bulletin #SR-994-B; unit quarantined from interstate dispatch pending actuator swap.
--- LOG_END ---
"""
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(raw_dump)
    print("   -> Wrote 3 unstructured shop bay work orders to datasets/maintenance_logs.txt.")


def main():
    seed_unit1_duckdb()
    print("[2/4] Generating Unit 2 1,000,000-row fuel fraud Parquet dataset...")
    generate_fuel_dataset("datasets/fuel_transactions.parquet", num_records=1_000_000)
    seed_unit3_vision_images()
    seed_unit4_maintenance_logs()


if __name__ == "__main__":
    main()

