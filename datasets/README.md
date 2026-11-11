# COSC 2060: Apex Logistics Multimodal Datasets

This directory houses the dataset generation scripts and pre-seeded files used across all 8 units of **COSC 2060: Modern Data Engineering & AI Infrastructure**.

---

## 📦 Pre-Seeded Datasets

When your GitHub Codespace boots (or whenever you run `./reset_sandbox.sh`), `seed_all_datasets.py` automatically builds the following assets:

| File / Folder | Used In | Format | Description |
| :--- | :--- | :--- | :--- |
| `datasets/apex_logistics.duckdb` | **Unit 1** | DuckDB Database | Persistent relational tables: `drivers` (4 rows), `routes` (5 rows), and `weather_observations` (6 rows) for practicing `ASOF JOIN` and window lag functions. |
| `datasets/fuel_transactions.parquet` *(also mirrored at `data/fuel_transactions.parquet`)* | **Unit 2** | Apache Parquet (Snappy) | **1,000,000 rows** of synthetic commercial fleet fuel swipes across WY, CO, UT, TX, and NE with ~1% embedded fraud anomalies (tank overflow & impossible velocity). |
| `datasets/raw_fleet_images/` | **Unit 3** | JPEG + JSON | Multi-resolution gate camera inspection photos (`1920x1080` 16:9 and `1200x900` 4:3) + Pascal VOC bounding boxes in `annotations.json`. |
| `datasets/maintenance_logs.txt` | **Unit 4** | Raw Text | Unstructured shop bay work orders containing safety-critical turbocharger defect citations (`Recall Bulletin #SR-994-B`). |

---

## 🔄 Regenerating Datasets Manually

To restore all datasets to their factory-fresh condition at any time:

```bash
./reset_sandbox.sh
```

Or run the Python generator directly:

```bash
python datasets/seed_all_datasets.py
```

