# Unit 5: Required Readings, Concepts & Video Lectures

Welcome to the instructional reading and study guide for **Unit 5: Data as a Service (DaaS) & REST APIs**. This page organizes the week's learning materials into four sections:

1. **Instructor Lecture & Conceptual Deep Dive:** Learn why sharing raw files breaks downstream applications, what our validated JSON API contract looks like, how Pydantic v2 enforces data types and boundaries, and how to build and test a FastAPI service step by step.
2. **Required Readings & Tutorial Guides:** Explore official documentation from FastAPI, Pydantic v2, Starlette, and Uvicorn.
3. **Required Micro-Video Lectures (Embedded):** Watch focused video tutorials covering REST APIs, FastAPI endpoints, and Pydantic v2 validation.
4. **Institutional Video Lecture Embeds:** Access instructor announcements and lab walkthrough recordings.

*Work through each section in sequence as part of your 150-minute self-study block before starting the applied lab.*

---

## 1. Instructor Lecture & Conceptual Deep Dive

### Serving Data Safely with FastAPI and Pydantic Contracts

In Units 1 through 4, we built pipelines for four major types of AI data:
* **Unit 1:** Relational feature matrices in DuckDB (`.parquet`).
* **Unit 2:** Standardized anomaly detection tables in Polars (`.parquet`).
* **Unit 3:** Letterboxed computer vision tensors and YOLO manifests (`.npy` / `.parquet`).
* **Unit 4:** Cleaned, overlapping text chunks and vector embeddings (`.jsonl` / `.parquet`).

Each of those pipelines produced files on disk. But in **Unit 5**, we face a practical question: **how do other software systems—like a dispatcher's web dashboard, a driver's mobile app, or an AI agent—actually use the data we built?**

A web browser or mobile phone cannot reach onto your server's hard drive and open a `.parquet` file directly. Instead, data engineers wrap their datasets and models behind a **REST API (Application Programming Interface)** using **FastAPI** and protect the inputs and outputs with **Pydantic Data Contracts**.

#### Measurable Learning Objectives
* **Explain** why sharing unvalidated CSV files across teams causes silent pipeline failures and how explicit API contracts prevent them.
* **Define** Pydantic `BaseModel` schemas with `Field` constraints (`gt`, `ge`, `le`, `min_length`) and custom validators to reject bad data automatically.
* **Build** REST API endpoints in **FastAPI** using `GET` and `POST` routes, query parameters, and HTTP status codes (`200 OK`, `404 Not Found`, `422 Unprocessable Entity`).
* **Connect** FastAPI endpoints to underlying DuckDB/Polars Parquet tables so live applications can query curated features on demand.
* **Test** API endpoints programmatically using FastAPI's `TestClient` without needing a separate browser.

---

### What Our Output Looks Like and Where the Data Comes From

#### The Purpose
Our goal in Unit 5 is to build a **Validated Fleet Data Microservice** (`app = FastAPI()`) enforced by **Pydantic Request and Response Schemas**. When a client application requests route delay predictions or submits a new fuel transaction for anomaly scoring, our service validates every field, queries the underlying Parquet/DuckDB store, and returns a guaranteed JSON response.

#### Why Downstream Systems Need a Strict JSON Contract
When two software systems talk over a network (for example, a dispatch web app talking to your Python data pipeline), they communicate using **JSON (JavaScript Object Notation)** over HTTP.

If your Python service returns `"delay_mins": 15` on Monday, `"delay_mins": "15 minutes"` on Tuesday, and renames the key to `"route_delay": null` on Wednesday, the web dashboard will crash. A **Data Contract** (written as a Pydantic `BaseModel`) acts as a strict gatekeeper on both sides:
1. **Inbound Request Validation:** If a client sends negative gallons (`gallons: -50.0`) or text where a number belongs (`driver_id: "unknown"`), Pydantic blocks the request immediately and returns HTTP `422 Unprocessable Entity` before bad data can touch your database or model.
2. **Outbound Response Guarantee:** Every successful HTTP `200 OK` response is verified against a response schema so downstream apps can trust every field name and data type 100% of the time.

#### Where the Raw Data Comes From (Source Systems)
Our Unit 5 FastAPI service sits between live operational clients and the curated Parquet/vector datasets we built in Units 1–4:
1. **Curated Parquet & Vector Stores (`feature_matrix.parquet`, `anomaly_features.parquet`, `rag_chunks.jsonl`):** Queried in milliseconds by DuckDB or Polars inside the API route handler.
2. **Inbound Client HTTP Requests (Dispatch Web UI, Driver Mobile App, Terminal Scanners):** Send live JSON payloads over `GET` and `POST` requests asking for driver history lookups or real-time transaction evaluations.

#### Sample Output Dataset (The Target API Contract Shape)
When a client sends a valid request to our API, the exchange follows this exact HTTP + JSON structure:

**Inbound HTTP `POST /v1/evaluate-transaction` Request Body:**
```json
{
  "trans_id": 1002,
  "driver_id": 42,
  "origin_city": "Cheyenne",
  "gallons": 380.0,
  "amount_usd": 1444.0,
  "implied_speed_mph": 185.0
}
```

**Verified Outbound HTTP `200 OK` JSON Response Body:**
```json
{
  "trans_id": 1002,
  "driver_id": 42,
  "is_anomaly": true,
  "risk_score": 0.99,
  "flags_triggered": [
    "TANK_OVERFLOW (>300 gal)",
    "IMPOSSIBLE_SPEED (>75 mph)"
  ],
  "status": "REJECTED_FOR_REVIEW"
}
```

**Verified Outbound HTTP `422 Unprocessable Entity` (When Bad Data Is Sent, e.g., `gallons: -10`):**
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

---

### How an Unchecked CSV Update Broke a Dispatch Dashboard

To see why teams replace shared CSV files with APIs and data contracts, consider a real incident from freight operations.

A logistics company ran a web dashboard used by 120 dispatchers every morning to track high-risk shipments. Every morning at 6:00 AM, a Python script exported a CSV file to a shared network folder:
`/shared/analytics/delivery_delay_predictions.csv`

At 7:45 AM, the dispatch web server read that CSV file and displayed the predictions on screen.

One Friday afternoon, a developer updated the Python script and made two small changes:
1. They renamed the column `truck_id` to `vehicle_vin` to match a new database table.
2. Where weather data was missing, they wrote the string `"N/A"` instead of `0.0`.

Because a CSV file has no built-in schema check, the Python script saved the file without any warning. On Monday morning at 8:00 AM, the dispatch dashboard crashed on startup with:
```text
KeyError: 'truck_id' not found
ValueError: could not convert string to float: 'N/A'
```

For four hours on Monday morning, dispatchers had no visibility into scheduled routes.

Why did that happen?
* **No Schema Contract:** Nothing checked that `truck_id` was still present or that numeric columns actually held numbers.
* **Tight Coupling:** The dashboard depended directly on internal file column names.

When you serve data through a **FastAPI endpoint backed by a Pydantic model**, a missing field or invalid data type is caught immediately by automated tests before the code ever reaches production.

---

### How APIs Work: The Restaurant Dining Room Analogy

If you are new to web APIs, think of a **restaurant**:

* **The Kitchen (Your DuckDB / Polars / Vector Engine):** Holds the raw ingredients, stoves, and storage freezers (your `.parquet` files and SQL tables). Outside customers are never allowed to walk into the kitchen and grab food out of the freezer themselves.
* **The Menu (The Pydantic Schema / OpenAPI Spec):** Lists the exact requests a customer is allowed to make and what each dish comes with.
* **The Waiter (FastAPI):** Takes the customer's order at the counter, checks that the order makes sense (*"Sorry, you can't order -3 sandwiches"*), brings valid orders to the kitchen, and hands back a clean, standardized plate (the JSON response).

```
CLIENT APP  ──[ HTTP Request (GET / POST) ]──>  FASTAPI + PYDANTIC  ──>  DUCKDB / POLARS
(Customer)                                      (Waiter + Menu Check)     (The Kitchen)
```

#### Common HTTP Status Codes Every Data Engineer Should Know
When a client talks to your FastAPI server, the server replies with a 3-digit **HTTP status code** so the client knows immediately what happened:
* **`200 OK`:** The request succeeded and the JSON data is attached.
* **`404 Not Found`:** The request was formatted properly, but the specific ID requested (such as `route_id = 99999`) does not exist in the database.
* **`422 Unprocessable Entity`:** The client sent invalid data that failed your Pydantic contract (such as a negative number of gallons or a missing required field).

---

### Step-by-Step Code Ramp-Up: Pydantic and FastAPI from the Ground Up

Let's build up the Python syntax for Pydantic v2 and FastAPI step by step, starting from a simple class definition.

#### Step 1: Creating Your First Pydantic Data Contract (`BaseModel` and `Field`)
Normally in Python, type hints like `gallons: float` are just polite suggestions—Python won't stop someone from passing `-999` or `"hello"`.

When your class inherits from Pydantic's `BaseModel`, Pydantic actively validates every field the moment an object is created. You can add numeric and string rules using `Field(...)`:
* `gt=0`: strictly **g**reater **t**han `0`
* `ge=0`: **g**reater than or **e**qual to `0`
* `le=450`: **l**ess than or **e**qual to `450`
* `min_length=2`: string must have at least 2 characters

```python
from pydantic import BaseModel, Field, ValidationError

class FuelSwipeContract(BaseModel):
    trans_id: int = Field(gt=0, description="Transaction ID must be a positive integer")
    driver_id: int = Field(gt=0)
    origin_city: str = Field(min_length=2, max_length=50)
    gallons: float = Field(gt=0.0, le=450.0, description="Gallons must be between 0 and 450")
    implied_speed_mph: float = Field(ge=0.0, le=120.0)

# 1. Valid record passes cleanly:
valid_swipe = FuelSwipeContract(
    trans_id=101,
    driver_id=42,
    origin_city="Cheyenne",
    gallons=150.5,
    implied_speed_mph=62.0
)
print("Validated dict:", valid_swipe.model_dump())

# 2. Invalid record (negative gallons) raises a ValidationError automatically!
try:
    bad_swipe = FuelSwipeContract(
        trans_id=102,
        driver_id=42,
        origin_city="Cheyenne",
        gallons=-25.0,
        implied_speed_mph=62.0
    )
except ValidationError as err:
    print("Blocked bad record:", err.errors()[0]["msg"])
```

#### Step 2: Creating a `GET` Endpoint in FastAPI
Now let's create a web API using `FastAPI()`. A `@app.get("/path")` decorator tells FastAPI to run your Python function whenever a client requests that URL path:

```python
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Fleet Data Service")

# Sample in-memory lookup table (in our lab, we can also query DuckDB/Parquet!)
ROUTES_DB = {
    101: {"route_id": 101, "origin_city": "Cheyenne", "distance_miles": 102.5, "target_delay_mins": 15},
    102: {"route_id": 102, "origin_city": "Denver", "distance_miles": 345.0, "target_delay_mins": 0},
}

@app.get("/health")
def health_check():
    """Simple health check endpoint returning 200 OK."""
    return {"status": "healthy", "service": "cosc-2060-api"}

@app.get("/v1/routes/{route_id}")
def get_route_by_id(route_id: int):
    """Looks up a single route by ID, or returns 404 Not Found if missing."""
    if route_id not in ROUTES_DB:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")
    return ROUTES_DB[route_id]
```

#### Step 3: Creating a `POST` Endpoint with Pydantic Input & Output Contracts
When a client needs to send a structured JSON payload to your API (for example, submitting a transaction to be scored), we use `@app.post(...)`. By setting the function parameter type to `payload: FuelSwipeContract` and specifying `response_model=AnomalyResponse`, FastAPI validates both the input and the output automatically:

```python
from pydantic import BaseModel

class AnomalyResponse(BaseModel):
    trans_id: int
    is_anomaly: bool
    risk_score: float
    reason: str

@app.post("/v1/evaluate-anomaly", response_model=AnomalyResponse)
def evaluate_fuel_swipe(payload: FuelSwipeContract):
    """Evaluates a validated fuel transaction for tank overflow or speed anomalies."""
    if payload.gallons > 300.0:
        return AnomalyResponse(
            trans_id=payload.trans_id,
            is_anomaly=True,
            risk_score=0.95,
            reason="Tank overflow (>300 gallons)"
        )
    if payload.implied_speed_mph > 75.0:
        return AnomalyResponse(
            trans_id=payload.trans_id,
            is_anomaly=True,
            risk_score=0.99,
            reason="Speed exceeds 75 mph governor limit"
        )
    return AnomalyResponse(
        trans_id=payload.trans_id,
        is_anomaly=False,
        risk_score=0.05,
        reason="Normal transaction"
    )
```

#### Step 4: Testing Your API Directly in Python with `TestClient`
How do you test your FastAPI endpoints inside a script or automated grader without opening a web browser or managing background server ports? FastAPI includes `TestClient`, which lets you call `client.get(...)` and `client.post(...)` right inside your Python script:

```python
from fastapi.testclient import TestClient

client = TestClient(app)

# 1. Test GET /health
resp_health = client.get("/health")
assert resp_health.status_code == 200
print("GET /health:", resp_health.json())

# 2. Test POST /v1/evaluate-anomaly with valid anomalous transaction
resp_eval = client.post("/v1/evaluate-anomaly", json={
    "trans_id": 501,
    "driver_id": 42,
    "origin_city": "Cheyenne",
    "gallons": 380.0,
    "implied_speed_mph": 60.0
})
assert resp_eval.status_code == 200
print("POST valid payload:", resp_eval.json())

# 3. Test POST /v1/evaluate-anomaly with invalid negative gallons (expect 422!)
resp_bad = client.post("/v1/evaluate-anomaly", json={
    "trans_id": 502,
    "driver_id": 42,
    "origin_city": "Cheyenne",
    "gallons": -15.0,
    "implied_speed_mph": 60.0
})
assert resp_bad.status_code == 422
print("POST invalid payload blocked with HTTP status:", resp_bad.status_code)
```

---

### Practice Exercises and Common Questions

Try these three exercises in your GitHub Codespaces sandbox (`units/unit_05_data_as_a_service_and_apis/`) before starting the graded lab:

1. **Exercise 1 (Testing Field Boundaries):** In Python, instantiate `FuelSwipeContract` with `origin_city="A"` (only 1 character, violating `min_length=2`). Inspect the `ValidationError` message produced by Pydantic.
2. **Exercise 2 (404 Not Found Check):** Using `TestClient(app)`, call `client.get("/v1/routes/9999")` for a route ID that does not exist and verify that `response.status_code == 404`.
3. **Exercise 3 (Querying DuckDB Inside an Endpoint):** Inside a FastAPI `GET` function, run a one-line DuckDB query on `datasets/unit_01_routes.parquet` and return `.df().to_dict(orient="records")`.

#### Common Questions & Troubleshooting

* **Question 1: In Pydantic v2, should I use `.dict()` or `.model_dump()` to convert a model instance into a Python dictionary?**  
  *Answer:* In Pydantic v2, `.model_dump()` is the standard method (replacing `.dict()` from Pydantic v1). Similarly, `.model_validate()` is the Pydantic v2 method for validating a dictionary.

* **Question 2: What is the difference between a Path Parameter (`/v1/routes/{route_id}`) and a Query Parameter (`/v1/routes?city=Cheyenne`)?**  
  *Answer:* A **Path Parameter** (`{route_id}`) identifies one specific resource by its unique ID. A **Query Parameter** (`?city=Cheyenne&limit=10`) filters or paginates a list of resources. In FastAPI, any function argument not in `{...}` in the URL path is automatically treated as a query parameter (for `GET`) or request body (for `POST`).

* **Question 3: Why did my FastAPI endpoint return HTTP `422` instead of running my `if` statements?**  
  *Answer:* That is Pydantic doing its job! FastAPI validates the incoming JSON against your `BaseModel` *before* your endpoint function even starts running. If any field is missing or out of bounds, FastAPI immediately returns `422 Unprocessable Entity`.

---

## 2. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical references before beginning your applied lab:

1. **[FastAPI Official Tutorial: User Guide & Core Concepts](https://fastapi.tiangolo.com/tutorial/)**
   *Learn how to define path operations, query parameters, request bodies, and automatic OpenAPI schema documentation.*

2. **[Pydantic v2 Documentation: Models & Field Validators](https://docs.pydantic.dev/latest/)**
   *Understand model declaration, `Field` constraints, custom `@field_validator` methods, and serialization.*

3. **[Starlette ASGI Framework: Architecture & Testing](https://starlette.dev/)**
   *Explore the toolkit underneath FastAPI and how `TestClient` simulates HTTP requests in Python.*

4. **[Uvicorn ASGI Web Server: Configuration Reference](https://uvicorn.dev/)**
   *Learn how production FastAPI services are launched and managed with Uvicorn workers.*

5. **[Designing Data-Intensive Applications: Data Encoding & Evolution Notes](https://github.com/ept/ddia-references)**
   *Review how schema contracts maintain backward and forward compatibility across services.*

---

## 3. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to see RESTful APIs and schema contracts in action:

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

## 4. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for Unit 5 will appear in this designated container.</p>
</div>
