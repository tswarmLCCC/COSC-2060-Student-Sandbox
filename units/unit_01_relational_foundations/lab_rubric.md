# Unit 1 Lab Grading Rubric: The Relational Foundation & Look-Ahead Bias Prevention

> **Course**: COSC 2060 — Modern Data Engineering & AI Infrastructure  
> **Assessment**: Unit 1 Applied Engineering Lab (`lab1_yourlastname.py`)  
> **Total Points**: 100 Points (Canvas SpeedGrader)

---

| Criteria | Exemplary (Full Points) | Competent (Partial Points) | Developing (Needs Revision) | Points |
|---|---|---|---|---|
| **1. Temporal Leakage Prevention (ASOF Join)** | The `ASOF JOIN` is constructed correctly with `dep_time >= obs_time`. Automated assertions pass with zero future timestamp contamination. | Join executes, but inequality is inverted or calendar dates are used instead of timestamps, causing minor leakage. | Standard `LEFT JOIN` used without time boundaries, introducing catastrophic look-ahead bias. | **30** |
| **2. Rolling Window Isolation (Lag Features)** | Rolling driver statistics strictly utilize `ROWS BETWEEN N PRECEDING AND 1 PRECEDING`. Current row is never included in input feature computation. | Window function partitions correctly, but uses `CURRENT ROW` for feature calculation, causing label leakage. | Window functions omitted or syntax produces runtime errors. | **25** |
| **3. Pipeline Execution & Output Format** | Standalone script executes cleanly without human intervention; outputs valid `output/feature_matrix.parquet` with correct schema. | Script runs, but requires manual file path tweaks or exports only flat uncompressed CSV. | Script fails to execute due to unhandled Python or DuckDB syntax errors. | **20** |
| **4. Defensive Null & Edge Case Handling** | Uses `COALESCE` to provide sensible physical defaults for routes with no prior weather history or first-time drivers. | Leaves unexpected `NULL` values across continuous feature columns. | Script crashes on missing values or unhandled joins. | **15** |
| **5. Code Quality & Standards** | Professional Python/SQL formatting: uppercase SQL keywords, descriptive column aliases, clear docstrings, and modular design. | Minor style violations (mixed case keywords, cryptic column names, missing comments). | Unformatted monolithic script; no documentation or explanatory comments. | **10** |
| **Total** | | | | **100** |
