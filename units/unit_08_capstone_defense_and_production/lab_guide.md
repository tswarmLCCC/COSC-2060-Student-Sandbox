# Unit 8 Lab: The Capstone Defense & Blind Batch Verification

> **Course**: COSC 2060 — Modern Data Engineering & AI Infrastructure  
> **Lab Deliverable**: Python script (`lab8_starter.py`) and container configuration (`Dockerfile`) executing an automated end-to-end integration test against a blind, unseen evaluation batch.  
> **Grading Mode**: 100-Point Rubric with live automated verification assertions.

---

## 1. Coding Clinic: "I Do, We Do, You Do"

### "I Do" — The Instructor Demonstration: Multi-Stage Container Packaging
A production Dockerfile builds dependencies in a builder stage to keep the final production runtime small and secure:

```dockerfile
# Stage 1: Build & Dependencies
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Clean Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### "We Do" — Guided Class Practice: Validating Pipeline Health Prior to Defense
Before presenting to stakeholders, we run an automated health probe to confirm all microservices are responding within latency limits:

```python
import time

def verify_system_readiness(health_func, max_timeout=5.0):
    start = time.time()
    while time.time() - start < max_timeout:
        try:
            status = health_func()
            if status == "HEALTHY":
                print(f"[OK] System healthy and ready for live defense ({time.time() - start:.2f}s).")
                return True
        except Exception:
            time.sleep(0.5)
    raise TimeoutError("System failed readiness probe before defense.")

# Test readiness:
verify_system_readiness(lambda: "HEALTHY")
```

---

### "You Do" — Autonomous Applied Problem
Now, complete the capstone challenge: assemble all units into a cohesive system, ingest the blind evaluation batch, and pass the automated defense audit.

---

## 2. 100-Point Graded Challenges

#### Part 0: Basics Warm-Up — Pre-Flight Inspection of the Blind Batch
Before executing the full Capstone Defense verification suite, run `part0_basics_warmup()` in `lab8_starter.py` to inspect and count the incoming records across all three modalities in `BLIND_TEST_BATCH`.



You will complete four progressive challenges inside `lab8_starter.py`.

```
================================================================================
COSC 2060 - UNIT 8 LAB: CAPSTONE DEFENSE & BLIND BATCH VERIFICATION
================================================================================
[Challenge 1: 25 pts] Multi-Modal System Architecture & Config Validation
[Challenge 2: 25 pts] Unseen Blind Test Batch Ingestion & DLQ Isolation
[Challenge 3: 25 pts] Automated Cross-Engine Diagnostic Synthesis
[Challenge 4: 25 pts] Full Stack Capstone Defense Verification Suite
================================================================================
```

### Complete Copy-and-Paste Starter Script (`lab8_starter.py`)

Open `units/unit_08_capstone_defense_and_production/lab8_starter.py` in your sandbox repository (reference starter code shown below):

```python
"""
COSC 2060 — Unit 8 Lab: Capstone Defense & Blind Batch Verification
Name: [Your Name]
Date: [Current Date]
"""

import json
import time
from typing import Dict, List, Any

# =========================================================================
# THE BLIND TEST BATCH (Injected by Faculty Review Board during Defense)
# =========================================================================
BLIND_TEST_BATCH = {
    "fuel_transactions": [
        {"tx_id": "TX-901", "truck_id": "TRUCK-101", "gallons": 140.0, "state": "OH"},
        {"tx_id": "TX-902", "truck_id": "TRUCK-219", "gallons": 340.0, "state": "IN"}, # Anomaly: Exceeds tank capacity!
        {"tx_id": "TX-903", "truck_id": "TRUCK-304", "gallons": -12.5, "state": "IL"}, # Poison Pill: Negative gallons!
        {"tx_id": "TX-904", "truck_id": "TRUCK-405", "gallons": 95.0,  "state": "OH"}
    ],
    "vision_inspections": [
        {"truck_id": "TRUCK-219", "image": "img_blind_01.jpg", "defect": "sidewall_crack", "confidence": 0.94},
        {"truck_id": "TRUCK-101", "image": "img_blind_02.jpg", "defect": "none", "confidence": 0.99}
    ],
    "maintenance_logs": [
        {"truck_id": "TRUCK-219", "wo": "WO-9901", "notes": "Engine whistling noise under high acceleration. Recall notice Part #TC-884."},
        {"truck_id": "TRUCK-101", "wo": "WO-9902", "notes": "Wiper blade replacement completed."}
    ]
}


# =========================================================================
# PART 0: BASICS WARM-UP — CAPSTONE PRE-FLIGHT SANITY CHECK
# =========================================================================
def part0_basics_warmup() -> Dict[str, int]:
    """
    PART 0: Basics Warm-Up (Pre-Flight Inspection of the Blind Test Batch)
    Counts the incoming records across all three modalities in BLIND_TEST_BATCH
    before executing the full Capstone Defense verification suite.
    """
    print("--- Part 0: Basics Warm-Up (Inspecting Blind Batch Counts) ---")
    counts = {k: len(v) for k, v in BLIND_TEST_BATCH.items()}
    print("Incoming Blind Batch Modality Counts:", counts)
    return counts


# =========================================================================
# CHALLENGE 1: Multi-Modal System Architecture & Config (25 pts)
# =========================================================================
class CapstoneDefenseSystem:
    def __init__(self, system_name: str = "Midwest-Logistics-Autonomous-Core"):
        self.system_name = system_name
        self.feature_store = {}
        self.dlq = []
        self.active_alerts = []
        self.grounded_fleet = set()
        print(f"[{self.system_name}] Initializing Capstone Defense Ecosystem...")


# =========================================================================
# CHALLENGE 2: Blind Test Batch Ingestion & DLQ Isolation (25 pts)
# =========================================================================
    def ingest_blind_fuel_transactions(self, transactions: List[Dict[str, Any]]):
        """
        Ingests fuel transactions:
          - Quarantines negative or zero gallons into the Dead-Letter Queue (DLQ).
          - Detects fuel anomalies (gallons > 300) and raises a FRAUD_ALERT.
          - Commits clean transactions into the feature store.
        """
        for tx in transactions:
            # 1. Poison Pill Check
            if tx["gallons"] <= 0.0:
                self.dlq.append({
                    "record": tx,
                    "reason": "Corrupted numeric measurement (gallons <= 0)",
                    "timestamp": time.time()
                })
                continue
                
            # 2. Anomaly Evaluation
            if tx["gallons"] > 300.0:
                self.active_alerts.append({
                    "alert_type": "FUEL_FRAUD",
                    "truck_id": tx["truck_id"],
                    "detail": f"Transaction {tx['tx_id']}: {tx['gallons']} gallons exceeds tank capacity."
                })
                
            # 3. Commit clean feature state
            tid = tx["truck_id"]
            if tid not in self.feature_store:
                self.feature_store[tid] = {"total_gallons": 0.0, "transaction_count": 0}
            self.feature_store[tid]["total_gallons"] += tx["gallons"]
            self.feature_store[tid]["transaction_count"] += 1


# =========================================================================
# CHALLENGE 3: Automated Cross-Engine Diagnostic Synthesis (25 pts)
# =========================================================================
    def evaluate_operational_clearance(self, truck_id: str, vision_data: List[Dict], rag_data: List[Dict]) -> Dict[str, Any]:
        """
        Synthesizes multimodal data across vision and text to determine if a vehicle is CLEARED or GROUNDED.
        """
        findings = []
        is_grounded = False
        
        # Check Vision Defects:
        truck_vision = [v for v in vision_data if v["truck_id"] == truck_id]
        for v in truck_vision:
            if v["defect"] == "sidewall_crack" and v["confidence"] >= 0.80:
                findings.append(f"Vision Alert: Tire sidewall crack detected ({v['confidence']*100:.1f}% confidence).")
                is_grounded = True
                
        # Check Maintenance RAG Recalls:
        truck_rag = [r for r in rag_data if r["truck_id"] == truck_id]
        for r in truck_rag:
            if "recall" in r["notes"].lower() or "whistling" in r["notes"].lower():
                findings.append(f"RAG Alert: Unresolved safety bulletin in work order {r['wo']}.")
                is_grounded = True
                
        if is_grounded:
            self.grounded_fleet.add(truck_id)
            return {
                "truck_id": truck_id,
                "status": "GROUNDED",
                "risk_tier": "CRITICAL",
                "findings": findings
            }
        else:
            return {
                "truck_id": truck_id,
                "status": "CLEARED",
                "risk_tier": "NORMAL",
                "findings": ["All automated safety checks passed."]
            }


# =========================================================================
# CHALLENGE 4: Full Stack Capstone Defense Verification Suite (25 pts)
# =========================================================================
if __name__ == "__main__":
    print("================================================================================")
    print("COSC 2060 CAPSTONE TECHNICAL DEFENSE: LIVE SIMULATION")
    print("================================================================================")
    
    part0_basics_warmup()
    defense = CapstoneDefenseSystem()

    # Step 1: Ingesting Blind Batch
    print("\n--- Phase 1: Ingesting Blind Fuel Transactions ---")
    defense.ingest_blind_fuel_transactions(BLIND_TEST_BATCH["fuel_transactions"])
    
    print(f"Clean records processed for trucks: {list(defense.feature_store.keys())}")
    print(f"Quarantined DLQ count: {len(defense.dlq)}")
    print(f"Active fraud alerts: {len(defense.active_alerts)}")

    # Verification: Poison pill TX-903 isolated in DLQ:
    assert len(defense.dlq) == 1, f"Expected 1 DLQ record, got {len(defense.dlq)}"
    assert defense.dlq[0]["record"]["tx_id"] == "TX-903"
    print("[PASS] Poison pill TX-903 successfully routed to DLQ without crashing pipeline.")

    # Verification: Fuel fraud alert on TRUCK-219:
    assert len(defense.active_alerts) == 1
    assert defense.active_alerts[0]["truck_id"] == "TRUCK-219"
    print("[PASS] Fuel tank anomaly detected on TRUCK-219.")

    # Step 2: Evaluating Multimodal Operational Clearance
    print("\n--- Phase 2: Multimodal Cross-Engine Diagnostics ---")
    
    # Evaluate TRUCK-101:
    res_101 = defense.evaluate_operational_clearance(
        "TRUCK-101", BLIND_TEST_BATCH["vision_inspections"], BLIND_TEST_BATCH["maintenance_logs"]
    )
    print(f"TRUCK-101 Status: {res_101['status']}")
    assert res_101["status"] == "CLEARED"
    assert res_101["risk_tier"] == "NORMAL"
    print("[PASS] TRUCK-101 cleared for highway operation.")

    # Evaluate TRUCK-219:
    res_219 = defense.evaluate_operational_clearance(
        "TRUCK-219", BLIND_TEST_BATCH["vision_inspections"], BLIND_TEST_BATCH["maintenance_logs"]
    )
    print(f"TRUCK-219 Status: {res_219['status']}")
    print(f"TRUCK-219 Findings: {res_219['findings']}")
    assert res_219["status"] == "GROUNDED"
    assert res_219["risk_tier"] == "CRITICAL"
    assert len(res_219["findings"]) == 2
    assert "TRUCK-219" in defense.grounded_fleet
    print("[PASS] TRUCK-219 correctly grounded with 2 independent safety violations.")

    print("\n================================================================================")
    print("CAPSTONE AUDIT VERDICT: 100% PASS - READY FOR ENTERPRISE DEPLOYMENT")
    print("================================================================================")
```

---

## 3. 100-Point Rubric Table

| Criteria | Points | Full Mastery (100%) | Minor Flaw (75%) | Unacceptable (0%) |
|---|---|---|---|---|
| **Challenge 1: Architecture & Config** | 25 pts | Ecosystem properly structures feature store, DLQ, alert dispatch, and fleet grounding state. | State variables declared globally instead of encapsulated in class. | Incomplete system structure. |
| **Challenge 2: Blind Batch Ingestion** | 25 pts | Quarantines poison pills into DLQ without crash; flags fuel fraud; aggregates valid transactions. | Ingestion crashes on negative values or ignores fraud alert. | Fails to parse transactions. |
| **Challenge 3: Multimodal Diagnostics** | 25 pts | Correctly joins vision defects and RAG notes; grounds TRUCK-219 with 2 verified citations. | Grounds truck but misses one of the two modalities. | Gives false clearance to unsafe vehicle. |
| **Challenge 4: Live Defense Verification** | 25 pts | 100% assertions pass across all 4 phases of blind test batch; outputs clear executive audit trail. | Passes with warnings or manual intervention required. | Script crashes during verification suite. |

---

### Submission Instructions (GitHub-Only Workflow)
1. Edit and test `units/unit_08_capstone_defense_and_production/lab8_starter.py` inside your personal `COSC-2060-Student-Sandbox-yourname` repository.
2. Confirm your code and tests run cleanly in the terminal with zero errors.
3. Commit and push your changes to your personal GitHub repository:
   ```bash
   git add -A
   git commit -m "Complete Unit 8 Lab"
   git push
   ```
4. In Canvas, submit your **GitHub repository URL** along with a **list of the files you changed** (e.g., `units/unit_08_capstone_defense_and_production/lab8_starter.py`). Do not upload `.py` files to Canvas.
