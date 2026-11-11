# Unit 5: Asynchronous Preparation & Diagnostic Drills
## Data-as-a-Service (DaaS) & Production REST Serving

> **Time Commitment**: ~60 Minutes (Asynchronous Self-Study)  
> **Prerequisites**: Review of [Unit 5 Required Readings & Concepts](study_guide.md)  
> **Target Mastery**: REST API contracts, FastAPI async architecture, Pydantic v2 validation, HTTP 422 defenses.

---

## 1. Readiness Self-Check Checklist
Before attempting the diagnostic drills below, verify you have completed the foundational preparation:
- [ ] Grasped why serving models or features via raw unvalidated pickle files introduces severe security vulnerabilities and schema drift.
- [ ] Understood the HTTP status code taxonomy (`200 OK`, `400 Bad Request`, `404 Not Found`, `422 Unprocessable Entity`, `500 Server Error`).
- [ ] Verified local installation of `fastapi`, `pydantic>=2.0`, and `httpx`.

---

## 2. Part 1: Foundational Concept Checks
Test your conceptual grasp of production data serving and API engineering. Formulate your answer first, then click the bar to verify your reasoning against the architectural rationale.

<details>
<summary>Question 1: Why is loading data models using Python's pickle module a critical security vulnerability?</summary>

**Architectural Rationale:**
The Python `pickle` serialization format is not a passive data storage format—it serializes executable Python bytecode instructions. 

When `pickle.load()` deserializes a binary stream, it invokes Python's `__reduce__` protocol, which can execute arbitrary shell commands (e.g. `os.system("rm -rf /")`) or open reverse network shells without authentication. Production data engineering systems must exchange typed, structured schemas like JSON, Parquet, or Protocol Buffers, never untrusted pickles.
</details>

<details>
<summary>Question 2: What is the architectural role of Pydantic v2 in the FastAPI pipeline?</summary>

**Architectural Rationale:**
Pydantic v2 functions as an automated firewall at the network boundary. Written in compiled Rust (`pydantic-core`), it validates incoming JSON request payloads against strict type annotations and domain constraints (e.g., `Field(gt=0, le=1000)`). 

If a client sends an invalid payload (such as a string for a vehicle ID or a negative shipment weight), Pydantic rejects the request with an automatic **HTTP 422 Unprocessable Entity** response before any backend business logic or database queries are executed.
</details>

<details>
<summary>Question 3: Why must heavy CPU-bound computations NOT be placed directly inside an async def FastAPI endpoint?</summary>

**Architectural Rationale:**
FastAPI runs asynchronous request handlers on a single-threaded Python `asyncio` event loop. Cooperative multitasking requires endpoints to yield execution (`await`) during I/O operations (like database queries or network requests). 

If you run a heavy synchronous, CPU-bound calculation (like training a Scikit-Learn tree or running a CPU matrix loop) inside an `async def` function, it locks the entire event loop thread! All other incoming HTTP requests from all users stall until that calculation completes. Heavy CPU tasks must be offloaded to worker processes or run via `def` endpoints on a threadpool.
</details>

<details>
<summary>Question 4: What is the difference between HTTP 400 Bad Request and HTTP 422 Unprocessable Entity?</summary>

**Architectural Rationale:**
- **HTTP 400 Bad Request:** Indicates malformed syntax at the protocol layer (e.g., corrupted JSON string with unclosed braces or invalid HTTP headers). The server cannot even parse the payload.
- **HTTP 422 Unprocessable Entity:** Indicates syntactically valid JSON that violates semantic schema rules (e.g., valid JSON `{"vehicle_id": -99}`, but `vehicle_id` is constrained to positive integers). FastAPI automatically outputs structured 422 error details specifying the exact offending field.
</details>

---

## 3. Part 2: Code Execution Order & Syntax Traces

### Trace Drill 1: Identifying Event Loop Blocking
Examine the FastAPI endpoint below:

```python
from fastapi import FastAPI
import time

app = FastAPI()

@app.get("/telemetry/{vehicle_id}")
async def get_telemetry(vehicle_id: int):
    # Simulating a slow database query or synchronous wait
    time.sleep(2.0)
    return {"vehicle_id": vehicle_id, "status": "active"}
```

<details>
<summary>Analyze the Handler: What fatal scaling bottleneck occurs when 100 clients request this endpoint simultaneously?</summary>

**Diagnostic Analysis: EVENT LOOP STARVATION**
- The endpoint is declared with `async def`, but uses `time.sleep(2.0)`, which is a **synchronous blocking call**!
- Because `time.sleep()` does not yield to the event loop, the single thread sleeps for 2 full seconds per request.
- When 100 concurrent requests arrive, request #100 waits over **200 seconds** (3.3 minutes) to be served!
- **Defensive Fix**: In async endpoints, always use non-blocking async operations:
  `await asyncio.sleep(2.0)`
  Or declare the endpoint with standard synchronous `def get_telemetry(...)`, which causes FastAPI to execute it inside an external threadpool without blocking the main event loop.
</details>

### Trace Drill 2: Pydantic Contract Validation Trace
Examine the Pydantic schema below:

```python
from pydantic import BaseModel, Field

class DispatchRequest(BaseModel):
    route_id: int = Field(..., gt=0)
    cargo_weight_lbs: float = Field(..., ge=100.0, le=80000.0)
    origin_hub: str = Field(..., min_length=3, max_length=3)
```

Evaluate whether each of the following incoming payloads passes or triggers an HTTP 422 error:
1. `{"route_id": 104, "cargo_weight_lbs": 45000.0, "origin_hub": "DEN"}`
2. `{"route_id": -1, "cargo_weight_lbs": 500.0, "origin_hub": "CHY"}`
3. `{"route_id": 201, "cargo_weight_lbs": 95000.0, "origin_hub": "SLC"}`
4. `{"route_id": 302, "cargo_weight_lbs": 1200.0, "origin_hub": "Chicago"}`

<details>
<summary>Check the Validation Results: Reveal the pass/fail status and exact error for each payload.</summary>

**Validation Outcomes:**
1. **PASS**: `route_id > 0`, `100 <= weight <= 80000`, `hub` is exactly 3 characters.
2. **HTTP 422 FAIL**: `route_id = -1` violates `gt=0` (greater than zero).
3. **HTTP 422 FAIL**: `cargo_weight_lbs = 95000.0` violates `le=80000.0` (DOT legal limit exceeded).
4. **HTTP 422 FAIL**: `origin_hub = "Chicago"` has length 7, violating `max_length=3` (must be 3-letter IATA/hub code).
</details>

---

## 4. Architecture Traps & Defensive Rules

<div style="background: #f8fafc; border-left: 4px solid #1e3a8a; padding: 1rem 1.25rem; margin: 1.5rem 0; border-radius: 0 4px 4px 0;">
  <h4 style="margin: 0 0 0.5rem 0; color: #1e3a8a;">The Three Golden Rules of Production DaaS APIs:</h4>
  <ol style="margin: 0; padding-left: 1.25rem; line-height: 1.7;">
    <li><strong>Never Block the Event Loop:</strong> Use <code>async def</code> only when awaiting non-blocking I/O; otherwise, use standard <code>def</code> to leverage threadpools.</li>
    <li><strong>Enforce Explicit Bounds:</strong> Never use naked types like <code>float</code> or <code>int</code> without semantic range bounds (e.g. <code>gt=0</code>, <code>le=80000</code>).</li>
    <li><strong>Defend the Output Contract:</strong> Always declare <code>response_model=...</code> to guarantee internal database columns or sensitive fields never leak to client consumers.</li>
  </ol>
</div>

---

## 5. Preparation for Live In-Class Coding Clinic (Slot 2)
In the upcoming synchronous session, we will execute a live **"I Do, We Do" refactoring clinic**:
- **What to Have Open**: Terminal with Python 3.10+ activated, VS Code, and local Jupyter environment.
- **The Clinic Mission**: We will inspect Dr. Leo Chen's freight pricing prototype loading an unvalidated pickled dictionary, demonstrate its silent failure on schema drift, and live-code an asynchronous **FastAPI + Pydantic v2** service delivering **2.3ms average latency** with automatic HTTP 422 protection.
