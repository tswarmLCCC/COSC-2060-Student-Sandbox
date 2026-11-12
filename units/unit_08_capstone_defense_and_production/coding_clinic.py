"""
====================================================================
COSC 2060: Modern Data Engineering & AI Infrastructure
Unit 8 Synchronous Coding Clinic ("I Do, We Do, You Do")
Topic: Capstone Defense, Multi-Stage Docker, & Blind Batch Audit
====================================================================
Run this script from the terminal to execute the live class walkthrough
demonstrations:
    python units/unit_08_capstone_defense_and_production/coding_clinic.py
====================================================================
"""


# ====================================================================
# PART 0: BASICS WARM-UP — MULTI-MODAL DEFENSIVE CHECKS AT A GLANCE
# ====================================================================
print("\n>>> Executing PART 0: BASICS WARM-UP (Multi-Modal Sanity Checks)...")
sample_checks = {
    "tabular_gallons_positive": 140.0 > 0.0,
    "vision_confidence_valid": 0.0 <= 0.94 <= 1.0,
    "rag_notes_non_empty": len("Recall notice Part #TC-884".strip()) > 0
}
print("Part 0 Warm-Up — Defensive Check Results:", sample_checks)


# ====================================================================
# PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION
# ====================================================================
print("\n>>> Executing PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION...")
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

