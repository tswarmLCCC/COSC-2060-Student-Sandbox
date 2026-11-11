# Unit 5: Required Readings, Concepts & Video Lectures

Welcome to the core instructional lecture and study hub for **Unit 5: Data as a Service (DaaS) & The API Layer**. This page organizes all weekly learning materials into four structured chapters:

1. **Instructor Lecture & Conceptual Deep Dive:** Master decoupled microservices, the "Death of the CSV" operational postmortem, HTTP REST semantics, strict Pydantic v2 data validation schemas, and asynchronous ASGI concurrency.
2. **Required Readings & Authoritative Tutorial Guides:** Study curated official documentation from FastAPI, Pydantic v2, Starlette, and Uvicorn.
3. **Required Micro-Video Lectures (Embedded):** Watch high-definition video chapters with verified timestamp navigation to observe RESTful endpoints and real-time schema validation in live Python environments.
4. **Institutional Video Lecture Embeds:** Access campus-specific video recordings and announcements uploaded by your instructor.

*Work through each section in sequence as part of your 150-minute asynchronous self-study allocation before starting the applied laboratory assignment.*

---

## 1. Instructor Lecture & Conceptual Deep Dive

### Treating Data as a Service: Modern REST APIs & Pydantic Contracts

#### 1. Unit Overview & Objectives
In Units 1 through 4, we built specialized engines for every modern data modality:
* **Unit 1**: Relational feature matrices in DuckDB.
* **Unit 2**: Real-time anomaly detection in Polars.
* **Unit 3**: Computer vision preprocessing manifests in OpenCV.
* **Unit 4**: Semantic vector search and RAG indexing in Sentence-Transformers.

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
* **Construct** defensive Pydantic v2 models that validate input payloads and guarantee output schemas, rejecting malformed or out-of-bounds data before processing.
* **Unify** multimodal data sources (relational Parquet, tabular anomaly models, visual manifests, and vector retrieval) into a cohesive microservice.
* **Test and Verify** API endpoints using automated Python client testing (`TestClient` / `httpx`) and interactive OpenAPI documentation (`/docs`).

---

#### 2. The Narrative of Data: The $380,000 Monday Morning Outage
To appreciate why production data engineering abandoned CSV handoffs, consider an authentic incident at a national freight logistics firm.

Midwest Logistics operated a real-time dispatch dashboard used by 120 dispatchers to monitor delivery delays across 1,200 trucks. Every morning at 6:00 AM, an automated script exported an updated machine learning prediction table from the data science repository to a shared network drive:

`\\corp-shares\analytics\delivery_delay_predictions.csv`

At 7:45 AM, the dispatch dashboard backend ingested this file and loaded the delay probability scores into the user interface.

##### The Silent Change
On Friday afternoon, a well-meaning junior data engineer cleaned up the feature engineering pipeline. They made three seemingly harmless improvements:
1. Renamed `truck_id` to `vehicle_vin` to match the company's new ERP standard.
2. Encoded missing weather delay values as the text string `"N/A"` instead of leaving them empty or null.
3. Added a new column containing unencrypted driver phone numbers for convenience.

Because CSV files contain **no schema enforcement, no type declarations, and no contracts**, the script generated the file without error.

##### The Catastrophic Failure
On Monday morning at 8:00 AM, the dispatch dashboard backend crashed with an unhandled exception:
```text
KeyError: 'truck_id' not found in DataFrame columns
```

The application restarted, attempted to re-read the CSV, failed, and entered a crash loop. Dispatchers across four terminals were unable to view route assignments, delivery deadlines, or high-risk delays.

For four hours during peak morning operations, freight sat idle on loading docks. Cross-country teams scrambled. The company missed contracted delivery windows, resulting in **$380,000 in liquidated damages** and lost logistics contracts.

##### The Architectural Diagnosis: The Death of the CSV
Why did this disaster occur?
* **No Contract:** The data team threw raw files over the wall. There was no explicit agreement on column names, data types, or allowable values.
* **No Validation:** The recipient application assumed the file was correct and crashed when its assumptions broke.
* **Coupling:** Changing internal data storage broke external consumers.

**The Solution:** Expose data through **APIs with Pydantic contracts**. If an upstream engineer renames a field, the API contract catches it immediately during testing. If an invalid value is sent, the API returns a structured `422 Unprocessable Entity` error rather than crashing the client application.

---

#### 3. The Mental Model: "The Restaurant Waiter" & API Contracts
To understand how APIs decouple systems, consider a restaurant dining room:

* **The Kitchen (The Data Engine):** The kitchen contains industrial stoves, walk-in freezers, raw meat, and sharp knives. Customers do not walk into the kitchen, open the freezer, and cook their own steaks. That would be chaotic, dangerous, and unhygienic.
* **The Customer (The Client Application):** The customer wants a specific meal cooked to their specifications.
* **The Menu (The API Contract / OpenAPI Spec):** The menu lists exactly what dishes are available, what ingredients they contain, and what customizations are permitted.
* **The Waiter (FastAPI):** The customer gives an order to the waiter. The waiter validates the order (*"I'm sorry, you cannot order a negative number of steaks"*). If valid, the waiter delivers the order to the kitchen, receives the prepared dish, and serves it on a clean plate.

```
CLIENT (Customer) ──[HTTP GET /v1/routes/101]──> FASTAAPI (Waiter) ──> DUCKDB (Kitchen)
                                                       │
                                            PYDANTIC CONTRACT
                                        (Validates Schema & Types)
```

By placing FastAPI between clients and your raw databases, you can upgrade DuckDB, refactor Polars, or change disk paths without breaking a single external application.

---

#### 4. The Power of Pydantic v2: Zero-Cost Rust Data Contracts
In Python, types are normally dynamic and unenforced. Pydantic v2 changes this by rewriting Python type validation in **Rust**.

When you declare a schema:
```python
from pydantic import BaseModel, Field

class PredictionRequest(BaseModel):
    truck_id: int = Field(gt=0, description="Positive integer fleet truck ID")
    distance_miles: float = Field(gt=0.0, lt=4000.0)
    origin_city: str = Field(min_length=2, max_length=50)
```

Pydantic automatically:
1. **Validates Types:** Rejects `"N/A"` or strings when an integer is required.
2. **Enforces Domain Constraints:** Blocks negative truck IDs or physically impossible distances ($> 4000$ miles).
3. **Generates OpenAPI Documentation:** Instantly populates interactive Swagger UI documentation at `/docs`.
4. **Executes in Rust:** Validates 100,000 payloads per second with microsecond latency.

---

#### 5. Guided Implementation Walkthrough: Production FastAPI Microservice

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

# 2. Define strict Pydantic v2 data contract
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

---

#### 6. Common Traps & Formative Self-Check FAQ

* **Question 1: What is the difference between synchronous (`def`) and asynchronous (`async def`) endpoints?**  
  *Answer:* An `async def` endpoint allows Python's event loop to pause execution during I/O operations (like querying a database or reading a file) and process other incoming HTTP requests concurrently. Use `async def` whenever your endpoint calls non-blocking async drivers.

* **Question 2: What happens when a client sends invalid JSON to a FastAPI endpoint?**  
  *Answer:* FastAPI intercepts the malformed payload, prevents it from touching your database or model code, and automatically responds with an HTTP `422 Unprocessable Entity` containing exact details on which field failed validation.

---

## 2. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical specifications before beginning your applied lab:

1. **[FastAPI Official Tutorial: User Guide & Core Concepts](https://fastapi.tiangolo.com/tutorial/)**
   *Learn how to define path operations, query parameters, request bodies, and automatic OpenAPI schema documentation.*

2. **[Pydantic v2 Documentation: Models & Rust Validation Engine](https://docs.pydantic.dev/latest/)**
   *Understand model declaration, custom validators (`@field_validator`), strict mode, and high-speed serialization.*

3. **[Starlette ASGI Framework: Architecture & Performance](https://www.starlette.io/)**
   *Explore the underlying asynchronous toolkit that powers FastAPI's high-concurrency HTTP request handling.*

4. **[Uvicorn ASGI Web Server: Configuration Reference](https://www.uvicorn.org/)**
   *Master running production Python services with worker processes, hot-reloading, and socket binding.*

5. **[Designing Data-Intensive Applications: Service-Oriented Architecture (OER Notes)](https://github.com/ept/ddia-references)**
   *Understand data encoding, schema evolution, and backward compatibility in distributed microservices.*

---

## 3. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to observe RESTful APIs and schema contracts in action:

### RESTful APIs in 100 Seconds <span style="font-size: 0.9em; color: #64748b;">(Full Video - 2:10)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="RESTful APIs in 100 Seconds" src="https://www.youtube.com/embed/-MTSQjw5DrM" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=-MTSQjw5DrM" target="_blank" rel="noopener">Open video segment in new tab (2:10)</a></p>

### FastAPI Tutorial: Building Modern Asynchronous Python Endpoints <span style="font-size: 0.9em; color: #64748b;">(Core Concepts - 15:00)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="FastAPI Tutorial" src="https://www.youtube.com/embed/qw--VYLpxG4?start=4348" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=qw--VYLpxG4&amp;t=4348s" target="_blank" rel="noopener">Open video segment in new tab (72:28)</a></p>

### Pydantic v2: Fast Data Validation for Production Python <span style="font-size: 0.9em; color: #64748b;">(Full Video - 10:30)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Pydantic v2 Validation" src="https://www.youtube.com/embed/T1dJfh1KlYA" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=T1dJfh1KlYA" target="_blank" rel="noopener">Open video segment in new tab (11:30)</a></p>

---

## 4. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for Unit 5 will appear in this designated container.</p>
</div>
