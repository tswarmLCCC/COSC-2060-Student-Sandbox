# Unit 5 Lab Grading Rubric: Data as a Service (FastAPI & Pydantic v2 Contracts)

> **Course**: COSC 2060 — Modern Data Engineering & AI Infrastructure  
> **Assessment**: Unit 5 Applied Engineering Lab (`lab5_yourlastname.py`)  
> **Total Points**: 100 Points (Canvas SpeedGrader)

---

| Criteria | Points | Full Mastery (100%) | Minor Flaw (75%) | Unacceptable (0%) |
|---|---|---|---|---|
| **Challenge 1: Pydantic v2 Contracts** | 25 pts | Strict boundary constraints (`gt`, `le`, regex pattern, enum check) implemented; rejects out-of-range payloads with `422`. | Minor omission in field constraints (e.g. allows negative gallons). | Missing Pydantic models; endpoints accept raw dictionaries. |
| **Challenge 2: Core Endpoints** | 25 pts | Implements `/v1/health`, `/v1/features/{truck_id}`, and `/v1/anomalies/fuel-check` with exact HTTP status codes. | Endpoints work but return 200 with error string instead of proper 404/422. | Endpoints fail or crash on execution. |
| **Challenge 3: Multimodal Integration** | 25 pts | Integrates vision manifest and vector RAG search with structured query models and response guarantees. | Endpoints lack response models or query filtering is hardcoded. | Endpoints omitted or uncallable. |
| **Challenge 4: Automated Verification** | 25 pts | Test suite exercises 200, 404, and 422 responses cleanly with 100% assertions passing. | Test suite tests happy path only, skipping 422 validation. | No automated test script provided. |
