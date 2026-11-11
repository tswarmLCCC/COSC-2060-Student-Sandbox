"""
====================================================================
COSC 2060: Modern Data Engineering & AI Infrastructure
Unit 5 Synchronous Coding Clinic ("I Do, We Do, You Do")
Topic: Data as a Service (FastAPI & Pydantic v2 Contracts)
====================================================================
Run this script from the terminal to execute the live class walkthrough
demonstrations:
    python units/unit_05_data_as_a_service_and_apis/coding_clinic.py
====================================================================
"""


# ====================================================================
# PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION
# ====================================================================
print("\n>>> Executing PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION...")
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


# ====================================================================
# PART 2: 'WE DO' — GUIDED CLASS PRACTICE
# ====================================================================
print("\n>>> Executing PART 2: 'WE DO' — GUIDED CLASS PRACTICE...")
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

