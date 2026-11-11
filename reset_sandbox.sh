#!/bin/bash
set -e

echo "======================================================================"
echo "  COSC 2060: Resetting Data Engineering Sandbox to Clean State..."
echo "======================================================================"

echo ">>> [1/2] Cleaning temporary pipeline output/ directories..."
rm -rf output/ data/ test_raw_images/
find units/ -maxdepth 2 -type d \( -name "output" -o -name "data" -o -name "test_raw_images" \) -exec rm -rf {} + 2>/dev/null || true

echo ">>> [2/2] Rebuilding pristine starter datasets (DuckDB, 1M Parquet, Vision, Logs)..."
if [ -f "datasets/seed_all_datasets.py" ]; then
    python datasets/seed_all_datasets.py
    echo ""
    echo "✅ SUCCESS! All datasets and databases have been restored to pristine starter state:"
    echo "   • datasets/apex_logistics.duckdb (drivers, routes, weather_observations)"
    echo "   • datasets/fuel_transactions.parquet & data/fuel_transactions.parquet (1,000,000 rows)"
    echo "   • datasets/raw_fleet_images/ (synthetic multi-resolution inspection photos)"
    echo "   • datasets/maintenance_logs.txt (raw unstructured shop bay repair logs)"
    echo ""
    echo "   🔒 Your Python (.py) and Notebook (.ipynb) files in units/ were NOT touched."
else
    echo "❌ Error: datasets/seed_all_datasets.py not found! Run this script from the repository root."
    exit 1
fi

