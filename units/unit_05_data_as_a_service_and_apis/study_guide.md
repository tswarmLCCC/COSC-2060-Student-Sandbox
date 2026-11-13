# Unit 5: Required Readings, Concepts & Video Lectures

Welcome to the core instructional lecture and study hub for **Unit 5: Data as a Service (DaaS) & The API Layer**. This page organizes all weekly learning materials into five structured sections:

1. **Unit Overview & Objectives:** Review the architectural context and measurable learning objectives for this unit.
2. **Instructor Lecture & Conceptual Deep Dive (Ribbon Slices 2a–2h):** Master the target JSON API contract shapes, operational DaaS source systems, bottom-up Pydantic v2 & FastAPI route construction, how downstream applications consume Data as a Service, the "Death of the CSV" operational postmortem, HTTP REST semantics, and asynchronous FastAPI endpoints.
3. **Required Readings & Authoritative Tutorial Guides:** Study curated official documentation from FastAPI, Pydantic v2, Starlette, and Uvicorn.
4. **Required Micro-Video Lectures (Embedded):** Watch high-definition video chapters with verified timestamp navigation to observe RESTful endpoints and real-time schema validation in live Python environments.
5. **Institutional Video Lecture Embeds:** Access campus-specific video recordings and announcements uploaded by your instructor.

*Work through each section in sequence as part of your 150-minute asynchronous self-study allocation before starting the applied laboratory assignment.*

---



## 1. Unit Overview & Objectives
In Units 1 through 4, we built specialized engines for every modern data modality:
* **Unit 1:** Relational feature matrices in DuckDB.
* **Unit 2:** Real-time anomaly detection in Polars.
* **Unit 3:** Computer vision preprocessing manifests in OpenCV.
* **Unit 4:** Semantic vector search and RAG indexing in Sentence-Transformers.

Each of these systems generated static artifacts: a `.parquet` file, a `.csv` dump, a `.json` manifest, or an in-memory vector array.

In **Unit 5**, we confront a fundamental engineering reality: **Data trapped in files on a hard drive is useless to the enterprise.**

A frontend web application cannot run DuckDB queries directly on your laptop's Parquet files. An iOS mobile app in a driver's hands cannot import your Polars script. An autonomous AI agent cannot read raw Python dictionaries from memory.

To make data accessible, secure, and resilient, we must treat **Data as a Service (DaaS)**. We wrap our data engines behind modern, high-performance **REST APIs** built with **FastAPI** and protected by strict **Pydantic v2 Data Contracts**.

```
[DuckDB / Polars / OpenCV / Vector RAG] ──> [FastAPI Service Layer] ──> [Pydantic v2 Contracts] ──> [Clients: Web / Mobile / AI Agents]
```

**Measurable Learning Objectives:**
* **Explain** the architectural risks of file-based data sharing (the "Death of the CSV") versus decoupled, contract-enforced REST APIs.
* **Design and Implement** RESTful endpoints utilizing standard HTTP verbs (`GET`, `POST`), status codes (`200 OK`, `400 Bad Request`, `404 Not Found`, `422 Unprocessable Entity`), and path/query parameters.
* **Construct** defensive Pydantic v2 models (`BaseModel` and `Field`) that validate input payloads and guarantee output schemas, rejecting malformed or out-of-bounds data before processing.
* **Unify** multimodal data sources (relational Parquet, tabular anomaly models, visual manifests, and vector retrieval) into a cohesive microservice.
* **Test and Verify** API endpoints programmatically using automated Python client testing (`TestClient` / `httpx`) and interactive OpenAPI documentation (`/docs`).

---

## 2a. What Our Output Looks Like and Where the Data Comes From

### The Purpose
Our goal in Unit 5 is to build a **Validated Fleet Data Microservice** (`app = FastAPI()`) enforced by **Pydantic v2 Request and Response Schemas**. When a client application requests route delay predictions or submits a new fuel transaction for anomaly scoring, our service validates every field, queries the underlying Parquet/DuckDB store, and returns a guaranteed JSON response.

### Why Downstream Systems Need a Strict JSON Contract
When two software systems communicate over a network (for example, a dispatch web dashboard talking to your Python data pipeline), they exchange **JSON (JavaScript Object Notation)** payloads over HTTP.

If your Python service returns `"delay_mins": 15` on Monday, `"delay_mins": "15 minutes"` on Tuesday, and renames the key to `"route_delay": null` on Wednesday, the web dashboard will crash. A **Data Contract** (written as a Pydantic `BaseModel`) acts as a strict gatekeeper on both sides:
1. **Inbound Request Validation:** If a client sends negative gallons (`gallons: -50.0`) or text where a number belongs (`driver_id: "unknown"`), Pydantic blocks the request immediately and returns HTTP `422 Unprocessable Entity` before bad data can touch your database or model.
2. **Outbound Response Guarantee:** Every successful HTTP `200 OK` response is verified against a response schema (`response_model=...`) so downstream apps can trust every field name and data type 100% of the time.

### Where the Raw Data Comes From (Source Systems)
Our Unit 5 FastAPI service sits between live operational clients and the curated Parquet/vector datasets we built in Units 1–4:
1. **Curated Parquet & Vector Stores (`feature_matrix.parquet`, `anomaly_features.parquet`, `rag_chunks.jsonl`):** Queried in milliseconds by DuckDB or Polars inside the API route handler.
2. **Inbound Client HTTP Requests (Dispatch Web UI, Driver Mobile App, Terminal Scanners):** Send live JSON payloads over `GET` and `POST` requests asking for driver history lookups or real-time transaction evaluations.

### Sample Output Dataset (The Target API Contract Shape)
When a client interacts with our API, the exchange follows these exact HTTP + JSON contracts:

**Inbound HTTP `POST /v1/evaluate-anomaly` Request Body:**
```json
{
  "trans_id": 1002,
  "driver_id": 42,
  "gallons": 380.0,
  "amount_usd": 1444.0,
  "implied_speed_mph": 185.0
}
```

**Verified Outbound HTTP `200 OK` JSON Response Body:**
```json
{
  "trans_id": 1002,
  "is_anomaly": true,
  "risk_score": 0.95,
  "rejection_reason": "Tank overflow violation (>300 gallons pumped)"
}
```

**Verified Outbound HTTP `422 Unprocessable Entity` (When Invalid Data Is Sent, e.g., `gallons: -10.0`):**
```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": ["body", "gallons"],
      "msg": "Input should be greater than 0",
      "input": -10.0
    }
  ]
}
```

> **Companion Reference:** To see how Pydantic API contracts compare with the tabular matrices, image manifests, and RAG schemas from Units 1–4, open **The Shapes of AI Data: A Companion Guide** in the *Getting Started - Course Orientation* module.

---

## 2b. Building Pydantic Data Contracts & HTTP Routes from the Ground Up

Before we examine real-world API outages or microservice architectures, let's start at the beginning: **How do we enforce strict data types in Python using Pydantic, and how do we expose a Python function over HTTP using FastAPI?**

In standard Python, type annotations like `gallons: float` are merely polite suggestions—Python will happily allow a caller to pass `"N/A"` or `-999.0` into a function until a math operation crashes halfway through your pipeline. Let's walk through the four foundational building blocks that turn fragile Python dictionaries into contract-guaranteed web services.

### 1. Turning Python Classes into Runtime Validators with `BaseModel`
* **How `BaseModel` differs from plain Python dictionaries and type hints:** In plain Python, a `dict` accepts any key or type without complaint, and standard type hints (`driver_id: int`) are ignored at runtime. When a class inherits from `pydantic.BaseModel`, Pydantic acts like a strict bouncer at the door: the instant an object is created, it inspects every field, rejects bad types (like `"abc"` for an `int`), and converts valid inputs into a guaranteed Python object.
* **What `BaseModel` is used for overall:** Engineers use Pydantic `BaseModel` classes across web APIs, config files, and LLM structured outputs whenever data crosses a boundary between two systems.
* **How it applies to our fleet API:** We define a `DriverSummary` contract so every downstream dashboard receives the exact fields and types it expects:

```python
from pydantic import BaseModel

class DriverSummary(BaseModel):
    driver_id: int
    safety_score: float
    is_active: bool

# Valid inputs pass and can be converted to a plain Python dict via .model_dump()
d = DriverSummary(driver_id=42, safety_score=0.98, is_active=True)
print(d.model_dump())  # {'driver_id': 42, 'safety_score': 0.98, 'is_active': True}
```

### 2. Adding Physical Domain Boundaries with `Field(...)`
Knowing that `gallons` is a `float` is not enough—a negative number like `-50.0` is still a valid `float`! Pydantic's `Field(...)` function lets us attach physical domain boundaries directly to each attribute:
* **`gt=0.0`** (strictly **g**reater **t**han `0.0`) or **`ge=0.0`** (**g**reater than or **e**qual to `0.0`)
* **`lt=4000.0`** (strictly **l**ess **t**han `4000.0`) or **`le=450.0`** (**l**ess than or **e**qual to `450.0`)
* **`min_length=2, max_length=50`** (minimum and maximum character length for strings)

### 3. Understanding HTTP Verbs (`GET` vs. `POST`) and Route Decorators
* **How web routes differ from local Python functions:** A normal Python function can only be called from another Python script on the same computer. A **FastAPI route decorator** (`@app.get(...)` or `@app.post(...)`) attaches a web URL path to a Python function so any browser, mobile app, or remote service on the network can call it over HTTP and get JSON back.
* **What `GET` and `POST` are used for overall:** Across the entire web, `GET` requests **read/fetch** existing data using parameters in the URL, while `POST` requests **send** a JSON payload in the request body (like submitting a form or sending a record to be scored).
* **How it applies to our fleet service:** You create an application with `app = FastAPI()` and attach route decorators above your Python functions:
* **`@app.get("/v1/routes/{route_id}")`**: Used when a client wants to **read or look up** an existing record without sending a complex body. The `{route_id}` part of the URL is a **path parameter** passed directly into your Python function (`async def get_route(route_id: int):`).
* **`@app.post("/v1/evaluate-anomaly")`**: Used when a client wants to **send a JSON payload** in the request body (such as a new fuel card swipe) for your server to validate, score, or process.

### 4. Querying DuckDB or Polars Inside an Endpoint Handler
Inside a FastAPI function, you can query the exact same `.parquet` files you built in Units 1–4 using DuckDB or Polars, convert the matching row to a dictionary, and return it as a validated Pydantic response object!

---

## 2c. How Client Applications & AI Systems Consume Data as a Service (DaaS)

You do not need prior web development coursework to understand how **Data as a Service (DaaS)** connects your data engineering pipelines to the rest of an organization.

In Units 1 through 4, our scripts ran in batch mode and saved files to disk (`feature_matrix.parquet`, `anomaly_features.parquet`, `rag_chunks.jsonl`). In a real company, three types of consumers need live access to those results every second:
1. **Frontend Web Dashboards (React / Vue / Internal Portals):** A human dispatcher clicks on Route #101 in their web browser. The browser sends an HTTP `GET /v1/routes/101` request to your FastAPI service and renders the returned JSON on screen.
2. **Mobile & Edge Devices (Driver Tablets / Gate Scanners):** When a fuel card is swiped at a travel plaza, the payment gateway sends an HTTP `POST /v1/evaluate-anomaly` JSON payload to your FastAPI service and receives an instant `{ "is_anomaly": false, "risk_score": 0.05 }` decision in 5 milliseconds.
3. **Downstream Microservices & AI Agents:** Other backend services call your API (and inspect its auto-generated `/docs` OpenAPI schema) without ever needing to know whether your backend stores data in DuckDB, Polars, PostgreSQL, or ChromaDB.

This architecture establishes our core rule for Unit 5:

> **The Bilateral Contract Rule:** A production Data-as-a-Service endpoint must enforce a strict Pydantic schema on **both** the inbound request (blocking malformed or out-of-bounds inputs with HTTP `422 Unprocessable Entity` before they reach your database) and the outbound `response_model` (guaranteeing downstream clients never crash due to renamed columns or unexpected `null` types).

---

## 2d. Why the $380,000 Monday Morning Outage Happened (The Death of the CSV)

To appreciate why production data engineering abandoned CSV handoffs, consider an authentic incident at a national freight logistics firm.

Midwest Logistics operated a real-time dispatch dashboard used by 120 dispatchers to monitor delivery delays across 1,200 trucks. Every morning at 6:00 AM, an automated script exported an updated machine learning prediction table from the data science repository to a shared network drive:

`\\corp-shares\analytics\delivery_delay_predictions.csv`

At 7:45 AM, the dispatch dashboard backend ingested this file and loaded the delay probability scores into the user interface.

### The Silent Change
On Friday afternoon, a well-meaning junior data engineer cleaned up the feature engineering pipeline. They made three seemingly harmless improvements:
1. Renamed `truck_id` to `vehicle_vin` to match the company's new ERP standard.
2. Encoded missing weather delay values as the text string `"N/A"` instead of leaving them empty or null.
3. Added a new column containing unencrypted driver phone numbers for convenience.

Because CSV files contain **no schema enforcement, no type declarations, and no contracts**, the script generated the file without error.

### The Catastrophic Failure
On Monday morning at 8:00 AM, the dispatch dashboard backend crashed with an unhandled exception:
```text
KeyError: 'truck_id' not found in DataFrame columns
```

The application restarted, attempted to re-read the CSV, failed, and entered a crash loop. Dispatchers across four terminals were unable to view route assignments, delivery deadlines, or high-risk delays.

For four hours during peak morning operations, freight sat idle on loading docks. Cross-country teams scrambled. The company missed contracted delivery windows, resulting in **\$380,000 in liquidated damages** and lost logistics contracts.

### The Architectural Diagnosis: The Death of the CSV
Why did this disaster occur?
* **No Contract:** The data team threw raw files over the wall. There was no explicit agreement on column names, data types, or allowable values.
* **No Validation:** The recipient application assumed the file was correct and crashed when its assumptions broke.
* **Coupling:** Changing internal data storage broke external consumers.

**The Solution:** Expose data through **APIs with Pydantic contracts**. If an upstream engineer renames a field, the API contract catches it immediately during testing. If an invalid value is sent, the API returns a structured `422 Unprocessable Entity` error rather than crashing the client application.

---

## 2e. "The Restaurant Waiter" & API Contracts

To understand how APIs decouple systems, consider a restaurant dining room:

* **The Kitchen (The Data Engine):** The kitchen contains industrial stoves, walk-in freezers, raw meat, and sharp knives (your `.parquet` files and DuckDB/Polars engines). Customers do not walk into the kitchen, open the freezer, and cook their own steaks. That would be chaotic, dangerous, and unhygienic.
* **The Customer (The Client Application):** The customer wants a specific meal cooked to their specifications.
* **The Menu (The API Contract / OpenAPI Spec):** The menu lists exactly what dishes are available, what ingredients they contain, and what customizations are permitted.
* **The Waiter (FastAPI):** The customer gives an order to the waiter. The waiter validates the order (*"I'm sorry, you cannot order a negative number of steaks"*). If valid, the waiter delivers the order to the kitchen, receives the prepared dish, and serves it on a clean plate.

```
CLIENT (Customer) ──[HTTP GET /v1/routes/101]──> FASTAPI (Waiter) ──> DUCKDB (Kitchen)
                                                       │
                                            PYDANTIC CONTRACT
                                        (Validates Schema & Types)
```

By placing FastAPI between clients and your raw databases, you can upgrade DuckDB, refactor Polars, or change disk paths without breaking a single external application.

### Essential HTTP Status Codes
When a client talks to your FastAPI server, the server replies with a 3-digit **HTTP status code** so the client knows immediately what happened:
* **`200 OK`:** The request succeeded and the validated JSON response is attached.
* **`404 Not Found`:** The request was formatted properly, but the specific ID requested (such as `route_id = 99999`) does not exist in the database.
* **`422 Unprocessable Entity`:** The client sent invalid data that violated your Pydantic contract (such as a negative number of gallons or a missing required field).

---

## 2f. Defensive Service Evolution — The Power of Pydantic v2 & Contract-First APIs

In Python, types are normally dynamic and unenforced. Pydantic v2 changes this by executing Python type validation in compiled **Rust**.

When you declare a schema:
```python
from pydantic import BaseModel, Field

class PredictionRequest(BaseModel):
    truck_id: int = Field(gt=0, description="Positive integer fleet truck ID")
    distance_miles: float = Field(gt=0.0, lt=4000.0)
    origin_city: str = Field(min_length=2, max_length=50)
```

Pydantic automatically:
1. **Validates Types:** Rejects `"N/A"` or arbitrary strings when a number is required.
2. **Enforces Domain Constraints:** Blocks negative truck IDs (`gt=0`) or physically impossible distances (`lt=4000.0`).
3. **Generates OpenAPI Documentation:** Instantly populates interactive Swagger UI documentation at `/docs`.
4. **Executes in Rust:** Validates 100,000 payloads per second with microsecond latency.

### Tracing the 3-Step Engineering Evolution
Let's trace the three ways teams share data across applications to see why bilateral Pydantic contracts are the industry standard:

#### Step 1: Shared Network CSV Drops (No Schema, Silent Breakage)
```python
# DANGEROUS: Renaming 'truck_id' to 'vehicle_vin' silently crashes downstream readers on Monday morning!
df.to_csv("/mnt/shared/predictions.csv", index=False)
```

#### Step 2: Unvalidated Dictionary Endpoint (Crashes Inside Handler with HTTP 500)
```python
# DANGEROUS: Accepts arbitrary dict; crashes with KeyError or TypeError if 'gallons' is "N/A" or negative
@app.post("/v1/evaluate-unvalidated")
async def bad_endpoint(payload: dict):
    is_overflow = payload["gallons"] > 300.0  # TypeError if payload["gallons"] == "N/A"!
    return {"overflow": is_overflow}
```

#### Step 3: Production FastAPI + Bilateral Pydantic v2 Contracts
```python
# PRODUCTION: Validates inbound FuelTransactionPayload (422 on bad input) AND outbound AnomalyEvaluationResponse
@app.post("/v1/evaluate-anomaly", response_model=AnomalyEvaluationResponse)
async def evaluate_transaction(payload: FuelTransactionPayload):
    ...
```

---

## 2g. Step-by-Step Code Ramp-Up & Guided Implementation Walkthrough (Pydantic + FastAPI)

Let's build up the Python syntax for Pydantic v2 and FastAPI step by step from the ground up, and then examine the complete production microservice and `TestClient` verification harness.

### Step 1: Creating and Testing a Pydantic `BaseModel` Contract
When a Python class inherits from `BaseModel`, Pydantic validates every field the moment an instance is created. Common `Field(...)` constraints include:
* `gt=0`: strictly **g**reater **t**han `0`
* `ge=0`: **g**reater than or **e**qual to `0`
* `le=450`: **l**ess than or **e**qual to `450`
* `min_length=2`, `max_length=50`: string length bounds

```python
from pydantic import BaseModel, Field, ValidationError

class RouteLookupContract(BaseModel):
    route_id: int = Field(gt=0)
    origin_city: str = Field(min_length=2, max_length=50)
    distance_miles: float = Field(gt=0.0, le=4000.0)

# 1. Valid record passes cleanly and exports to a dict via .model_dump():
valid_route = RouteLookupContract(route_id=101, origin_city="Cheyenne", distance_miles=102.5)
print("Validated dict:", valid_route.model_dump())

# 2. Invalid record (negative distance) raises a ValidationError automatically:
try:
    bad_route = RouteLookupContract(route_id=102, origin_city="Cheyenne", distance_miles=-50.0)
except ValidationError as err:
    print("Blocked invalid payload:", err.errors()[0]["msg"])
```

### Step 2: Creating `GET` Endpoints and Raising `HTTPException(status_code=404)`
A `@app.get("/path")` decorator registers a function to handle HTTP `GET` requests. If a requested ID is missing from your database, raise `HTTPException(status_code=404, detail="...")`:

```python
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Fleet Data Service")

ROUTES_DB = {
    101: {"route_id": 101, "origin_city": "Cheyenne", "distance_miles": 102.5, "target_delay_mins": 15},
    102: {"route_id": 102, "origin_city": "Denver", "distance_miles": 345.0, "target_delay_mins": 0},
}

@app.get("/v1/routes/{route_id}")
async def get_route_by_id(route_id: int):
    if route_id not in ROUTES_DB:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")
    return ROUTES_DB[route_id]
```

### Step 3: Guided Implementation Walkthrough — Production FastAPI Microservice
Here is how we combine `GET` and `POST` routes with strict Pydantic request (`FuelTransactionPayload`) and response (`AnomalyEvaluationResponse`) contracts in a production microservice:

```python
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
import uvicorn

# 1. Initialize FastAPI application
app = FastAPI(
    title="COSC 2060 Fleet Logistics Data Service",
    description="Unified API layer serving real-time predictions, anomalies, and maintenance logs",
    version="1.0.0"
)

# 2. Define strict Pydantic v2 data contracts
class FuelTransactionPayload(BaseModel):
    trans_id: int = Field(gt=0, description="Unique transaction ID")
    driver_id: int = Field(gt=0)
    gallons: float = Field(gt=0.0, le=450.0, description="Fuel pumped in gallons")
    amount_usd: float = Field(gt=0.0)
    implied_speed_mph: float = Field(ge=0.0, le=120.0, description="Speed calculated from consecutive swipes")

class AnomalyEvaluationResponse(BaseModel):
    trans_id: int
    is_anomaly: bool
    risk_score: float = Field(ge=0.0, le=1.0)
    rejection_reason: Optional[str] = None

# 3. Create RESTful evaluation endpoint
@app.post(
    "/v1/evaluate-anomaly",
    response_model=AnomalyEvaluationResponse,
    status_code=status.HTTP_200_OK
)
async def evaluate_transaction(payload: FuelTransactionPayload):
    # Domain Rule 1: Tank Capacity Violation
    if payload.gallons > 300.0:
        return AnomalyEvaluationResponse(
            trans_id=payload.trans_id,
            is_anomaly=True,
            risk_score=0.95,
            rejection_reason="Tank overflow violation (>300 gallons pumped)"
        )
    
    # Domain Rule 2: Physics Violation
    if payload.implied_speed_mph > 75.0:
        return AnomalyEvaluationResponse(
            trans_id=payload.trans_id,
            is_anomaly=True,
            risk_score=0.99,
            rejection_reason=f"Impossible velocity detected ({payload.implied_speed_mph} mph)"
        )
    
    return AnomalyEvaluationResponse(
        trans_id=payload.trans_id,
        is_anomaly=False,
        risk_score=0.05,
        rejection_reason=None
    )

# 4. Health Check Endpoint
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy", "service": "fleet-data-api"}
```

### Step 4: Testing Endpoints Programmatically with `TestClient`
To verify your API inside a Python script or automated test suite without needing a browser, use `fastapi.testclient.TestClient`:

```python
from fastapi.testclient import TestClient

client = TestClient(app)

# 1. Verify GET /health returns 200 OK
resp_health = client.get("/health")
assert resp_health.status_code == 200
print("Health check:", resp_health.json())

# 2. Verify valid anomalous transaction returns 200 OK with is_anomaly=True
resp_ok = client.post("/v1/evaluate-anomaly", json={
    "trans_id": 1002,
    "driver_id": 42,
    "gallons": 380.0,
    "amount_usd": 1444.0,
    "implied_speed_mph": 62.0
})
assert resp_ok.status_code == 200
print("Valid POST response:", resp_ok.json())

# 3. Verify out-of-bounds payload (negative gallons) is rejected with 422 Unprocessable Entity
resp_bad = client.post("/v1/evaluate-anomaly", json={
    "trans_id": 1003,
    "driver_id": 42,
    "gallons": -25.0,
    "amount_usd": 100.0,
    "implied_speed_mph": 55.0
})
assert resp_bad.status_code == 422
print("Invalid POST blocked with status code:", resp_bad.status_code)
```

**Verification Output:**
```
Health check: {'status': 'healthy', 'service': 'fleet-data-api'}
Valid POST response: {'trans_id': 1002, 'is_anomaly': True, 'risk_score': 0.95, 'rejection_reason': 'Tank overflow violation (>300 gallons pumped)'}
Invalid POST blocked with status code: 422
```

---

## 2h. Practice Exercises & Formative Self-Check FAQ

Try these three exercises in your GitHub Codespaces sandbox (`units/unit_05_data_as_a_service_and_apis/`) before starting the graded lab:

1. **Exercise 1 (Testing Field Boundaries):** In Python, instantiate `FuelTransactionPayload` with `implied_speed_mph=950.0` (violating `le=120.0`). Inspect the `ValidationError` message produced by Pydantic.
2. **Exercise 2 (404 Not Found Verification):** Using `TestClient(app)`, call `client.get("/v1/routes/9999")` for a route ID that does not exist and verify that `response.status_code == 404`.
3. **Exercise 3 (Querying DuckDB Inside an Endpoint):** Inside a FastAPI `GET` route handler, run a one-line DuckDB query on `datasets/unit_01_routes.parquet` and return `.df().to_dict(orient="records")`.

### Common Traps & Formative Self-Check FAQ

* **Question 1: What is the difference between synchronous (`def`) and asynchronous (`async def`) endpoints?**  
  *Answer:* An `async def` endpoint allows Python's event loop (think of a restaurant server taking Table 2's order while Table 1's food is cooking in the kitchen) to pause while waiting on slow I/O (like querying a database or waiting on a network socket) and process other incoming HTTP requests concurrently.

* **Question 2: What happens when a client sends invalid JSON to a FastAPI endpoint?**  
  *Answer:* FastAPI intercepts the malformed payload, prevents it from touching your database or model code, and automatically responds with an HTTP `422 Unprocessable Entity` containing exact details on which field failed validation.

* **Question 3: In Pydantic v2, should I use `.dict()` or `.model_dump()` to convert a model instance into a Python dictionary?**  
  *Answer:* In Pydantic v2, `.model_dump()` is the standard method (replacing `.dict()` from Pydantic v1). Similarly, `.model_validate()` is the Pydantic v2 method for validating a dictionary.

* **Question 4: Why should I specify `response_model=AnomalyEvaluationResponse` in `@app.post(...)` if my function already returns an object?**  
  *Answer:* Specifying `response_model=...` guarantees that FastAPI validates and filters the outgoing data against your contract (stripping any accidental internal fields like passwords or phone numbers) and documents the exact response schema in the interactive `/docs` OpenAPI specification.

---

## 3. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical specifications before beginning your applied lab:

1. **[FastAPI Official Tutorial: User Guide & Core Concepts](https://fastapi.tiangolo.com/tutorial/)**
   *Learn how to define path operations, query parameters, request bodies, and automatic OpenAPI schema documentation.*

2. **[Pydantic v2 Documentation: Models & Rust Validation Engine](https://docs.pydantic.dev/latest/)**
   *Understand model declaration, custom validators (`@field_validator`), strict mode, and high-speed serialization.*

3. **[Starlette ASGI Framework: Architecture & Performance](https://starlette.dev/)**
   *Explore the underlying asynchronous toolkit that powers FastAPI's high-concurrency HTTP request handling.*

4. **[Uvicorn ASGI Web Server: Configuration Reference](https://uvicorn.dev/)**
   *Master running production Python services with worker processes, hot-reloading, and socket binding.*

5. **[Designing Data-Intensive Applications: Service-Oriented Architecture (OER Notes)](https://github.com/ept/ddia-references)**
   *Understand data encoding, schema evolution, and backward compatibility in distributed microservices.*

---

## 4. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to observe RESTful APIs and schema contracts in action:

### RESTful APIs in 100 Seconds <span style="font-size: 0.9em; color: #64748b;">(Fireship - 2:10)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="RESTful APIs in 100 Seconds" src="https://www.youtube.com/embed/-MTSQjw5DrM" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=-MTSQjw5DrM" target="_blank" rel="noopener">Open video in new tab (2:10)</a></p>

### FastAPI Tutorial: Building Modern Asynchronous Python Endpoints <span style="font-size: 0.9em; color: #64748b;">(pixegami - 15-Minute Walkthrough)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="FastAPI Tutorial in Python" src="https://www.youtube.com/embed/iWS9ogMPOI0" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=iWS9ogMPOI0" target="_blank" rel="noopener">Open video in new tab</a></p>

### Pydantic v2: Fast Data Validation for Production Python <span style="font-size: 0.9em; color: #64748b;">(pixegami - Core Walkthrough)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Pydantic v2 Data Validation" src="https://www.youtube.com/embed/XIdQ6gO3Anc" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=XIdQ6gO3Anc" target="_blank" rel="noopener">Open video in new tab</a></p>

---

## 5. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for Unit 5 will appear in this designated container.</p>
</div>
