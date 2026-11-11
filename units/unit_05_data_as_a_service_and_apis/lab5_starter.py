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
    print("Running Automated API Test Suite...")
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
