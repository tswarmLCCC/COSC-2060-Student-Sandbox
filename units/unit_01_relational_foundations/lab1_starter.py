"""
====================================================================
COSC 2060: Modern Data Engineering & AI Infrastructure
Unit 1 Applied Lab: The Feature Matrix Builder
Starter Template File (100 Points Total)
====================================================================
Student Name : [YOUR NAME HERE]
Submission   : lab1_yourlastname.py
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
