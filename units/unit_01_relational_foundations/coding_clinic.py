"""
====================================================================
COSC 2060: Modern Data Engineering & AI Infrastructure
Unit 1 Synchronous Coding Clinic ("I Do, We Do, You Do")
Topic: The Relational Foundation & Look-Ahead Bias Prevention
====================================================================
Run this script from the terminal to execute the live class walkthrough
demonstrations:
    python units/unit_01_relational_foundations/coding_clinic.py
====================================================================
"""


# ====================================================================
# PART 0: BASICS WARM-UP — BUILDING BASIC SQL FEATURES FROM SCRATCH
# ====================================================================
print("\n>>> Executing PART 0: BASICS WARM-UP (Ground-Up SQL Features)...")
import duckdb

con = duckdb.connect()

# Before touching ASOF JOIN or window lags, let's build basic features in SQL:
# 1. Extract hour from a timestamp
# 2. Compute an arithmetic ratio (estimated driving hours at 55 mph)
# 3. Create a 0/1 indicator flag using CASE WHEN
warmup_df = con.sql("""
SELECT
    101 AS route_id,
    TIMESTAMP '2026-10-15 07:30:00' AS dep_time,
    EXTRACT(HOUR FROM TIMESTAMP '2026-10-15 07:30:00') AS dep_hour,
    165.0 AS distance_miles,
    ROUND(165.0 / 55.0, 2) AS est_drive_hours,
    CASE
        WHEN EXTRACT(HOUR FROM TIMESTAMP '2026-10-15 07:30:00') BETWEEN 7 AND 9 THEN 1
        ELSE 0
    END AS is_morning_rush
""").df()
print("Part 0 Warm-Up — Basic SQL Features:")
print(warmup_df)


# ====================================================================
# PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION
# ====================================================================
print("\n>>> Executing PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION...")

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

-- Weather observations (intermittent weather station logs)
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


# ====================================================================
# PART 2: 'WE DO' — GUIDED CLASS PRACTICE
# ====================================================================
print("\n>>> Executing PART 2: 'WE DO' — GUIDED CLASS PRACTICE...")
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

