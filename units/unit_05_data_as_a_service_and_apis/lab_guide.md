# Unit 5 Lab: Building the Logistics Unified Data Service

> **Course**: COSC 2060 — Modern Data Engineering & AI Infrastructure  
> **Lab Deliverable**: Python script (`lab5_starter.py`) implementing a production-grade FastAPI microservice with Pydantic v2 data contracts and automated unit tests.  
> **Grading Mode**: 100-Point Rubric with automated `TestClient` verification assertions.

---

## 1. Coding Clinic: "I Do, We Do, You Do"

### "I Do" — The Instructor Demonstration: Strict Pydantic Field Validation
In production APIs, defensive programming requires validating not just data types, but numerical and domain boundaries:

```python
from pydantic import BaseModel, Field, field_validator

class DeliveryWindow(BaseModel):
    shipment_id: str = Field(..., pattern=r"^SHP-\d{5}$")
    transit_hours: float = Field(..., gt=0.0, le=72.0)
    carrier_rating: float = Field(..., ge=1.0, le=5.0)

    @field_validator("transit_hours")
    @classmethod
    def check_realistic_transit(cls, v: float) -> float:
        if v < 0.5:
            raise ValueError("Transit hours cannot be under 30 minutes for interstate freight.")
        return v

# Valid instance:
valid_win = DeliveryWindow(shipment_id="SHP-10023", transit_hours=14.5, carrier_rating=4.8)
print("Valid model created successfully:", valid_win.model_dump())
```

---

### "We Do" — Guided Class Practice: Testing Endpoints with FastAPI `TestClient`
We do not test APIs by manually clicking a browser. We use programmatic test clients that simulate HTTP requests in memory without needing to boot a separate server process:

```python
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

demo_app = FastAPI()

@demo_app.get("/v1/ping")
def ping():
    return {"status": "healthy", "service": "telemetry-gateway"}

client = TestClient(demo_app)
response = client.get("/v1/ping")
assert response.status_code == 200
assert response.json()["status"] == "healthy"
print("Ping endpoint passed verification!")
```

---

### "You Do" — Autonomous Applied Problem
Now, unify all four data layers from Units 1 through 4 into a single, high-performance Data as a Service (DaaS) gateway.

---

## 2. 100-Point Graded Challenges

#### Part 0: Basics Warm-Up — Minimal Pydantic Model & Validation
Before testing the multi-endpoint FastAPI service, run `part0_basics_warmup()` in `lab5_starter.py` to validate a 2-field `Pydantic` `BaseModel` (`SimpleRoutePing`) and serialize it to a dictionary using `.model_dump()`.



You will complete four progressive challenges inside `lab5_starter.py`.

```
================================================================================
COSC 2060 - UNIT 5 LAB: DATA AS A SERVICE (FASTAPI & PYDANTIC V2)
================================================================================
[Challenge 1: 25 pts] Defensive Pydantic v2 Data Contracts
[Challenge 2: 25 pts] Core Feature & Anomaly REST Endpoints
[Challenge 3: 25 pts] Multimodal Vision & Vector RAG Endpoint Integration
[Challenge 4: 25 pts] Automated Verification Suite with FastAPI TestClient
================================================================================
```

### Complete Copy-and-Paste Starter Script (`lab5_starter.py`)

Open `units/unit_05_data_as_a_service_and_apis/lab5_starter.py` in your sandbox repository (reference starter code shown below):

```python
"""
COSC 2060 — Unit 5 Lab: Data as a Service (DaaS) Unified API
Name: [Your Name]
Date: [Current Date]
"""

from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, field_validator

# -------------------------------------------------------------------------
# FASTAPI APPLICATION INSTANCE
# -------------------------------------------------------------------------
app = FastAPI(
    title="Midwest Logistics Unified Data Service",
    description="Production REST API serving multimodal feature matrices, anomaly scoring, vision manifests, and RAG retrieval.",
    version="1.0.0"
)

# =========================================================================
# PART 0: BASICS WARM-UP — PYDANTIC MODEL DUMP & VALIDATION ERROR
# =========================================================================
def part0_basics_warmup() -> dict:
    """
    PART 0: Basics Warm-Up (Ground-Up Pydantic Validation)
    Practices creating a simple 2-field Pydantic BaseModel, dumping a valid record
    to a dict, and catching a ValidationError before testing the full FastAPI service.
    """
    print("=== Part 0: Basics Warm-Up (Pydantic BaseModel & Field Bounds) ===")
    class SimpleRoutePing(BaseModel):
        route_id: int = Field(gt=0)
        origin_city: str = Field(min_length=2)

    valid_ping = SimpleRoutePing(route_id=101, origin_city="Cheyenne")
    print("Validated ping:", valid_ping.model_dump())
    return valid_ping.model_dump()


# =========================================================================
# CHALLENGE 1: Defensive Pydantic v2 Data Contracts (25 pts)
# =========================================================================
class FuelEvaluationRequest(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction ID (e.g. TX-99012)")
    truck_id: str = Field(..., pattern=r"^TRUCK-\d{3}$", description="Must follow format TRUCK-XXX")
    gallons_pumped: float = Field(..., gt=0.0, le=350.0, description="Gallons pumped (cannot exceed tank capacity)")
    price_per_gal: float = Field(..., gt=1.0, lt=10.0)
    fuel_station_state: str = Field(..., min_length=2, max_length=2, description="2-letter US State abbreviation")


class FuelEvaluationResponse(BaseModel):
    transaction_id: str
    truck_id: str
    is_anomaly: bool
    risk_level: str = Field(..., pattern="^(NORMAL|SUSPICIOUS|FRAUD_ALERT)$")
    reason: str


class FeatureMatrixResponse(BaseModel):
    truck_id: str
    avg_speed_mph: float
    total_trips: int
    fuel_efficiency_mpg: float
    maintenance_status: str


class RAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Search query string")
    truck_id_filter: Optional[str] = None
    top_k: int = Field(default=3, ge=1, le=10)


class RAGSearchResult(BaseModel):
    work_order: str
    truck_id: str
    text_snippet: str
    relevance_score: float


# =========================================================================
# MOCK IN-MEMORY DATA STORES (Simulating Upstream Storage Engines)
# =========================================================================
FEATURE_STORE = {
    "TRUCK-101": FeatureMatrixResponse(
        truck_id="TRUCK-101", avg_speed_mph=58.4, total_trips=142, fuel_efficiency_mpg=6.8, maintenance_status="OPERATIONAL"
    ),
    "TRUCK-219": FeatureMatrixResponse(
        truck_id="TRUCK-219", avg_speed_mph=52.1, total_trips=98, fuel_efficiency_mpg=5.1, maintenance_status="REQUIRES_INSPECTION"
    )
}

VISION_MANIFEST_STORE = {
    "TRUCK-219": [
        {"image_name": "tire_steer_left_01.jpg", "label": "sidewall_crack", "confidence": 0.89, "bbox": [0.45, 0.52, 0.12, 0.08]},
        {"image_name": "tire_steer_right_01.jpg", "label": "normal", "confidence": 0.95, "bbox": [0.50, 0.50, 0.20, 0.20]}
    ]
}

MAINTENANCE_LOGS = [
    {"work_order": "WO-10045", "truck_id": "TRUCK-219", "text": "High whistling sound at 1800 rpm with brass glitter in oil pan.", "score": 0.87},
    {"work_order": "WO-10088", "truck_id": "TRUCK-302", "text": "Alternator voltage regulator replaced under heavy load.", "score": 0.42}
]


# =========================================================================
# CHALLENGE 2: Core Feature & Anomaly REST Endpoints (25 pts)
# =========================================================================
@app.get("/v1/health")
def health_check():
    """Health check endpoint for container orchestrators."""
    return {"status": "HEALTHY", "service": "midwest-logistics-daas"}


@app.get("/v1/features/{truck_id}", response_model=FeatureMatrixResponse)
def get_truck_features(truck_id: str):
    """Retrieves pre-computed feature matrix record for a specific truck."""
    if truck_id not in FEATURE_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Truck '{truck_id}' not found in feature store."
        )
    return FEATURE_STORE[truck_id]


@app.post("/v1/anomalies/fuel-check", response_model=FuelEvaluationResponse)
def evaluate_fuel_transaction(payload: FuelEvaluationRequest):
    """
    Evaluates real-time fuel transaction against physical threshold logic:
      - If gallons > 200 and state != 'OH' (home terminal): Flag as SUSPICIOUS
      - If gallons > 300: Flag as FRAUD_ALERT (tank capacity exceeded)
      - Otherwise: NORMAL
    """
    if payload.gallons_pumped > 300.0:
        return FuelEvaluationResponse(
            transaction_id=payload.transaction_id,
            truck_id=payload.truck_id,
            is_anomaly=True,
            risk_level="FRAUD_ALERT",
            reason="Gallons pumped exceeds physical maximum fuel tank capacity."
        )
    elif payload.gallons_pumped > 200.0 and payload.fuel_station_state != "OH":
        return FuelEvaluationResponse(
            transaction_id=payload.transaction_id,
            truck_id=payload.truck_id,
            is_anomaly=True,
            risk_level="SUSPICIOUS",
            reason="High-volume off-terminal fuel purchase flagged for auditing."
        )
    else:
        return FuelEvaluationResponse(
            transaction_id=payload.transaction_id,
            truck_id=payload.truck_id,
            is_anomaly=False,
            risk_level="NORMAL",
            reason="Transaction within standard operational thresholds."
        )


# =========================================================================
# CHALLENGE 3: Multimodal Vision & Vector RAG Endpoint Integration (25 pts)
# =========================================================================
@app.get("/v1/vision/manifest/{truck_id}")
def get_vision_manifest(truck_id: str):
    """Returns detected visual anomalies and YOLO bounding box metadata."""
    if truck_id not in VISION_MANIFEST_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No vision inspection manifest recorded for truck '{truck_id}'."
        )
    return {
        "truck_id": truck_id,
        "inspection_records": VISION_MANIFEST_STORE[truck_id]
    }


@app.post("/v1/maintenance/search", response_model=List[RAGSearchResult])
def search_maintenance_logs(request: RAGSearchRequest):
    """Performs semantic search across historical mechanic notes."""
    results = []
    for item in MAINTENANCE_LOGS:
        if request.truck_id_filter and item["truck_id"] != request.truck_id_filter:
            continue
        results.append(RAGSearchResult(
            work_order=item["work_order"],
            truck_id=item["truck_id"],
            text_snippet=item["text"],
            relevance_score=item["score"]
        ))
    return results[:request.top_k]


# =========================================================================
# CHALLENGE 4: Automated Verification Suite with TestClient (25 pts)
# =========================================================================
if __name__ == "__main__":
    part0_basics_warmup()
    print("\nRunning Automated API Test Suite...")
    client = TestClient(app)

    # Test 1: Health Check (200 OK)
    res_health = client.get("/v1/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "HEALTHY"
    print("[PASS] Test 1: Health check endpoint passed.")

    # Test 2: Feature Retrieval (200 OK & 404 Not Found)
    res_feat = client.get("/v1/features/TRUCK-219")
    assert res_feat.status_code == 200
    assert res_feat.json()["maintenance_status"] == "REQUIRES_INSPECTION"
    
    res_feat_404 = client.get("/v1/features/TRUCK-999")
    assert res_feat_404.status_code == 404
    print("[PASS] Test 2: Feature retrieval and 404 handling passed.")

    # Test 3: Contract Validation & Anomaly Detection (200 OK & 422 Unprocessable Entity)
    valid_tx = {
        "transaction_id": "TX-10492",
        "truck_id": "TRUCK-219",
        "gallons_pumped": 320.0,
        "price_per_gal": 3.89,
        "fuel_station_state": "IN"
    }
    res_anomaly = client.post("/v1/anomalies/fuel-check", json=valid_tx)
    assert res_anomaly.status_code == 200
    assert res_anomaly.json()["risk_level"] == "FRAUD_ALERT"

    # Malformed Request (Negative gallons should trigger 422 Unprocessable Entity):
    invalid_tx = {
        "transaction_id": "TX-10493",
        "truck_id": "TRUCK-219",
        "gallons_pumped": -50.0,  # Fails gt=0.0 constraint
        "price_per_gal": 3.89,
        "fuel_station_state": "IN"
    }
    res_invalid = client.post("/v1/anomalies/fuel-check", json=invalid_tx)
    assert res_invalid.status_code == 422
    print("[PASS] Test 3: Anomaly scoring and Pydantic 422 contract validation passed.")

    # Test 4: Multimodal Endpoints (Vision Manifest & RAG Search)
    res_vision = client.get("/v1/vision/manifest/TRUCK-219")
    assert res_vision.status_code == 200
    assert len(res_vision.json()["inspection_records"]) == 2

    rag_query = {"query": "whistling sound in turbo", "truck_id_filter": "TRUCK-219", "top_k": 1}
    res_rag = client.post("/v1/maintenance/search", json=rag_query)
    assert res_rag.status_code == 200
    assert len(res_rag.json()) == 1
    assert res_rag.json()[0]["work_order"] == "WO-10045"
    print("[PASS] Test 4: Multimodal vision and RAG endpoints passed.")

    print("\n[SUCCESS] All Unit 5 Lab challenges verified successfully!")
```

---

## 3. 100-Point Rubric Table

| Criteria | Points | Full Mastery (100%) | Minor Flaw (75%) | Unacceptable (0%) |
|---|---|---|---|---|
| **Challenge 1: Pydantic v2 Contracts** | 25 pts | Strict boundary constraints (`gt`, `le`, regex pattern, enum check) implemented; rejects out-of-range payloads with `422`. | Minor omission in field constraints (e.g. allows negative gallons). | Missing Pydantic models; endpoints accept raw dictionaries. |
| **Challenge 2: Core Endpoints** | 25 pts | Implements `/v1/health`, `/v1/features/{truck_id}`, and `/v1/anomalies/fuel-check` with exact HTTP status codes. | Endpoints work but return 200 with error string instead of proper 404/422. | Endpoints fail or crash on execution. |
| **Challenge 3: Multimodal Integration** | 25 pts | Integrates vision manifest and vector RAG search with structured query models and response guarantees. | Endpoints lack response models or query filtering is hardcoded. | Endpoints omitted or uncallable. |
| **Challenge 4: Automated Verification** | 25 pts | Test suite exercises 200, 404, and 422 responses cleanly with 100% assertions passing. | Test suite tests happy path only, skipping 422 validation. | No automated test script provided. |

---

### Submission Instructions (GitHub-Only Workflow)
1. Edit and test `units/unit_05_data_as_a_service_and_apis/lab5_starter.py` inside your personal `COSC-2060-Student-Sandbox-yourname` repository.
2. Confirm your code and tests run cleanly in the terminal with zero errors.
3. Commit and push your changes to your personal GitHub repository:
   ```bash
   git add -A
   git commit -m "Complete Unit 5 Lab"
   git push
   ```
4. In Canvas, submit your **GitHub repository URL** along with a **list of the files you changed** (e.g., `units/unit_05_data_as_a_service_and_apis/lab5_starter.py`). Do not upload `.py` files to Canvas.
