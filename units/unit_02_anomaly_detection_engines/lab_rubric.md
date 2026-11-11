# Unit 2 Lab Grading Rubric: The Anomaly Engine & Vectorized LazyFrames

> **Course**: COSC 2060 — Modern Data Engineering & AI Infrastructure  
> **Assessment**: Unit 2 Applied Engineering Lab (`lab2_yourlastname.py`)  
> **Total Points**: 100 Points (Canvas SpeedGrader)

---

| Criteria | Exemplary (Full Points) | Competent (Partial Points) | Developing (Needs Revision) | Points |
|---|---|---|---|---|
| **1. LazyFrame Pipeline Execution** | Pipeline uses `pl.scan_parquet()` and remains completely lazy until collection; executes across 1,000,000 records in < 15 seconds without OOM crashes. | Pipeline executes, but converts to eager DataFrames prematurely or runs slower than 45 seconds. | Converts data to Pandas or crashes with Out-of-Memory / GIL lockup. | **30** |
| **2. Feature Normalization & Imputation** | Implements Min-Max or Standard scaling natively in Polars expressions; programmatically imputes missing values cleanly without Pandas `.apply()`. | Normalization is mathematically correct, but relies on iterative loops or contains unhandled NaN values. | Features left unscaled; algorithm exhibits extreme ruler distortion. | **25** |
| **3. Derived Physical Velocity & Boundary Features** | Correctly derives `hours_delta` and `distance_miles` over driver IDs, calculating `implied_speed_mph` and tank overfill ratios. | Derived metrics calculated, but window ordering is omitted or causes division-by-zero errors. | Fails to derive velocity features; relies only on raw unengineered columns. | **25** |
| **4. Anomaly Detection & Model Integration** | Cleanly passes normalized matrix to Scikit-Learn IsolationForest; achieves target precision on embedded fraud anomalies. | Model executes, but thresholding or ground truth mapping is inverted. | Model fails to fit or crashes during NumPy conversion. | **10** |
| **5. Code Quality & Standards** | Modular Python functions, clear docstrings, uppercase SQL/Polars idioms, and robust error handling. | Minor style infractions (cryptic variable names, missing comments). | Monolithic unformatted script with zero documentation. | **10** |
| **Total** | | | | **100** |
