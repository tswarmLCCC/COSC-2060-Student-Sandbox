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

