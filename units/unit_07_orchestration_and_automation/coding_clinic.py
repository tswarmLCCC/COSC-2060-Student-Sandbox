"""
====================================================================
COSC 2060: Modern Data Engineering & AI Infrastructure
Unit 7 Synchronous Coding Clinic ("I Do, We Do, You Do")
Topic: Orchestration, Asset DAGs, & Dead-Letter Queues
====================================================================
Run this script from the terminal to execute the live class walkthrough
demonstrations:
    python units/unit_07_orchestration_and_automation/coding_clinic.py
====================================================================
"""


# ====================================================================
# PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION
# ====================================================================
print("\n>>> Executing PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION...")
import time

def resilient_operation(action, max_attempts=3, base_delay=0.1):
    for attempt in range(1, max_attempts + 1):
        try:
            return action()
        except Exception as e:
            if attempt == max_attempts:
                raise e
            sleep_time = base_delay * (2 ** (attempt - 1))
            print(f"[RETRY] Attempt {attempt} failed ({e}). Sleeping {sleep_time:.2f}s...")
            time.sleep(sleep_time)

# Simulating transient failure that succeeds on attempt 2:
counter = 0
def flaky_network():
    global counter
    counter += 1
    if counter < 2:
        raise ConnectionResetError("Remote host disconnected.")
    return "SUCCESS: 500 records downloaded"

result = resilient_operation(flaky_network)
print("Final Outcome:", result)


# ====================================================================
# PART 2: 'WE DO' — GUIDED CLASS PRACTICE
# ====================================================================
print("\n>>> Executing PART 2: 'WE DO' — GUIDED CLASS PRACTICE...")
# Target table represented as a dictionary partitioned by date:
TARGET_TABLE = {}

def idempotent_batch_write(date_partition: str, records: list):
    # Enforce idempotency: overwrite or clear existing partition:
    TARGET_TABLE[date_partition] = []
    for rec in records:
        TARGET_TABLE[date_partition].append(rec)
    print(f"Partition '{date_partition}' committed with {len(records)} records.")

# Running once:
idempotent_batch_write("2024-10-24", [{"id": 1}, {"id": 2}])
# Running a second time (simulating a pipeline replay):
idempotent_batch_write("2024-10-24", [{"id": 1}, {"id": 2}])

# Length remains 2, NOT 4!
assert len(TARGET_TABLE["2024-10-24"]) == 2
print("Idempotency verified: Zero duplicate rows generated.")

