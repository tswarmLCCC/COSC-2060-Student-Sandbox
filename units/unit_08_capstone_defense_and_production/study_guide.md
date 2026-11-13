# Unit 8: Required Readings, Concepts & Video Lectures

Welcome to the core instructional lecture and study hub for **Unit 8: Capstone Defense & Production Handoff**. This page organizes all weekly learning materials into five structured sections:

1. **Unit Overview & Objectives:** Review the architectural context and measurable learning objectives for this unit.
2. **Instructor Lecture & Conceptual Deep Dive (Ribbon Slices 2a–2h):** Master the target Capstone Audit Report and multi-modal source systems, bottom-up multi-modal data auditing & DLQ design, how Docker containers & blind-test harnesses verify production readiness, the "Works on My Machine" tragedy, the "Intermodal Shipping Container" mental model, multi-stage Dockerfile hardening, non-root security, and live capstone defense protocols.
3. **Required Readings & Authoritative Tutorial Guides:** Study curated official documentation from Docker, OWASP Container Security standards, and Twelve-Factor App methodologies.
4. **Required Micro-Video Lectures (Embedded):** Watch high-definition video chapters with verified timestamp navigation to observe container builds, image optimizations, and healthcheck verifications in live environments.
5. **Institutional Video Lecture Embeds:** Access campus-specific video recordings and announcements uploaded by your instructor.

*Work through each section in sequence as part of your 150-minute asynchronous self-study allocation before starting the applied laboratory assignment.*

---



## 1. Unit Overview & Objectives
Over the past seven units, you have constructed every layer of an enterprise AI infrastructure ecosystem:
* **Relational Core:** Feature engineering with point-in-time joins in DuckDB (Unit 1)
* **High-Throughput Analytics:** Unsupervised anomaly detection in Polars (Unit 2)
* **Visual Intelligence:** Standardized computer vision manifests in OpenCV (Unit 3)
* **Unstructured Knowledge:** Dense vector search and semantic RAG in Sentence-Transformers (Unit 4)
* **Data as a Service:** Contract-guaranteed REST APIs in FastAPI (Unit 5)
* **Agentic Bridges:** Model Context Protocol (MCP) tool integration (Unit 6)
* **Resilient Automation:** Asset-based DAG orchestration and DLQs (Unit 7)

In **Unit 8**, you face the final and most critical milestone of a professional engineer: **Production Handoff and Live Capstone Defense.**

Building software that only runs on your local development laptop is an incomplete engineering achievement. In the enterprise, your pipeline must run reliably in reproducible cloud environments, survive unseen messy data inputs, and be defended before executive stakeholders and technical review boards.

You will package your entire ecosystem into a production **Docker container**, write automated healthchecks, and defend your architecture against an **unseen blind test batch** during a live technical evaluation.

```
[Local Dev Code] ──> [Hardened Multi-Stage Dockerfile] ──> [Immutable Container Image] ──> [Cloud Staging / Blind Test Defense]
```

**Measurable Learning Objectives:**
* **Explain** the principles of containerization (Virtual Machines vs. Linux Containers) and eliminate the "Works on My Machine" failure mode.
* **Author** a hardened, multi-stage `Dockerfile` and `docker-compose.yml` that pins dependencies, enforces non-root execution, and exposes healthcheck endpoints.
* **Execute** an end-to-end integration test where an unseen "Blind Test / Chaos Batch" of multimodal data is ingested, cleansed, evaluated, and served without human intervention.
* **Articulate** architectural trade-offs, latency SLAs, memory constraints, and defensive failure recoveries in an executive technical presentation.
* **Defend** your ecosystem against real-time operational stress-tests in a live 15-minute capstone evaluation.

---

## 2a. What Our Output Looks Like and Where the Data Comes From

### The Purpose
Our goal in Unit 8 is to build the **End-to-End Capstone Defense Pipeline** (`lab8_capstone_runner.py`). It ingests a multi-modal operational batch—containing route telemetry, fuel swipes, inspection image metadata, and mechanic notes—quarantines any corrupted records into a Dead-Letter Queue, runs the valid records through our feature, anomaly, vision, and RAG stages, and outputs a comprehensive **`capstone_audit_report.json`** alongside the curated `.parquet` tables.

### Why Production Systems Need End-to-End Integration Audits
When you test each unit's script in isolation on clean sample data, it is easy to assume everything works. In production, however, data flows through multiple stages in sequence, and real incoming batches often contain multiple types of defects simultaneously:
* A route row might have a weather timestamp recorded *after* departure (temporal leakage attempt).
* A fuel swipe might have `-120.0` gallons or a missing `driver_id`.
* A camera frame might be `0 x 0` pixels or completely pitch black (`mean_brightness < 5.0`).
* A mechanic work order might consist only of empty HTML tags (`"<p>   </p>"`).

Your capstone pipeline proves that your system can ingest an entire messy multi-modal batch in one command, catch and quarantine every defective item in the Dead-Letter Queue (`capstone_dlq.jsonl`), and produce clean, verified outputs for all valid items.

### Where the Raw Data Comes From (Source Systems)
The capstone pipeline ingests a combined operational drop (`datasets/unit_08_chaos_batch.json` and multi-table seeds) representing a full day of fleet operations across all four source systems:
1. **Dispatch & NOAA Weather Logs** (Relational / Temporal)
2. **POS Fleet Fuel Card Stream** (High-Volume Tabular)
3. **Terminal Gate Camera Frames & Bounding Boxes** (Visual Sensor)
4. **Shop Bay Maintenance Work Orders** (Unstructured Text)

### Sample Output Dataset (The Target Capstone Audit Report Shape)
When your Unit 8 capstone script completes its run, it writes `output/capstone_audit_report.json` with exact verification counts across every subsystem:

```json
{
  "capstone_status": "PASSED_ALL_DEFENSIVE_CHECKS",
  "student_pipeline_version": "1.0.0",
  "subsystems": {
    "relational_feature_store": {
      "input_routes": 25,
      "valid_routes_exported": 23,
      "leaked_rows_blocked": 2,
      "output_file": "output/capstone_features.parquet"
    },
    "anomaly_detection_engine": {
      "input_transactions": 40,
      "valid_transactions_scored": 38,
      "anomalies_flagged": 4
    },
    "vision_preprocessing": {
      "input_images": 10,
      "valid_letterboxed_images": 9,
      "corrupted_images_quarantined": 1
    },
    "rag_vector_index": {
      "input_documents": 15,
      "valid_chunks_indexed": 28,
      "empty_docs_quarantined": 1
    }
  },
  "dead_letter_queue_total": 6,
  "dlq_file": "output/capstone_dlq.jsonl"
}
```

> **Companion Reference:** To see how all four data modalities in this capstone (relational matrices, anomaly tables, 3D image manifests, and RAG chunks) fit together across the entire course, open **The Shapes of AI Data: A Companion Guide** in the *Getting Started - Course Orientation* module.

---

## 2b. Building a Multi-Modal Auditor & Dead-Letter Queue from the Ground Up

Before we examine production containerization tragedies or multi-stage Dockerfiles, let's start at the beginning: **How do we combine all four data modalities from Units 1–4 into one defensive Python pipeline that never crashes on messy real-world inputs?**

In Units 1–7, you built each layer of the fleet logistics platform one piece at a time. In Unit 8, your capstone script (`lab8_capstone_runner.py`) acts as the **single quality gate** for an entire day of incoming fleet data. Let's walk through the four foundational building blocks of an end-to-end multi-modal verifier from the ground up.

### 1. Separating Good Records from Bad Records with a Shared `DeadLetterQueue`
When a batch contains 25 routes, 40 fuel swipes, 10 camera frames, and 15 mechanic notes, a single corrupted entry in *any* subsystem should never crash the other 95% of valid records. Instead of writing four separate error-logging loops, we create one shared `DeadLetterQueue` helper class with a `.quarantine(subsystem, record_id, raw_payload, reason)` method that tags every bad item with its origin (`"relational"`, `"anomaly_engine"`, `"vision"`, or `"rag"`) and writes them all to `output/capstone_dlq.jsonl`.

### 2. Enforcing Subsystem-Specific Invariants Before Passing Data Downstream
Each modality has its own non-negotiable physical or mathematical rule:
* **Relational Routes (Unit 1):** `act_arrival >= dep_time` (a truck cannot arrive before it departs), and weather joins must satisfy `r.dep_time >= w.obs_time` via `ASOF LEFT JOIN`.
* **Fuel Swipes (Unit 2):** `gallons > 0` and `amount_usd > 0` *before* computing Z-scores, plus physical anomaly flags (`gallons > 300` or `implied_speed_mph > 75`).
* **Camera Frames (Unit 3):** `width > 0`, `height > 0`, and `mean_brightness >= 5.0` (blocking pitch-black night frames) before computing letterbox padding and `[0.0, 1.0]` normalized YOLO boxes.
* **Mechanic Work Orders (Unit 4):** After stripping HTML tags and collapsing whitespace, `len(cleaned_text) > 0` before splitting into overlapping chunks.

### 3. Packaging the Runtime Environment (`requirements.txt` + `Dockerfile`)
In Unit 8, your Python script is only half of the deliverable. Because OpenCV relies on Linux C-libraries (`libgl1`, `libglib2.0-0`) and DuckDB/Polars rely on exact Python versions, we pin every Python package in `requirements.txt` and declare the exact operating system libraries inside a `Dockerfile` so the entire pipeline runs identically on your laptop, in GitHub Codespaces, and on any cloud server.

### 4. Writing Self-Checking Assertions and an Audit Report (`capstone_audit_report.json`)
A production pipeline never exits silently and hopes for the best. At the end of `lab8_capstone_runner.py`, it runs automated assertions (`assert` statements / `pytest` checks) verifying row counts, zero temporal leakage, and valid coordinate bounds, then writes `output/capstone_audit_report.json` with exact input, valid, and quarantined counts for every subsystem.

---

## 2c. How Containers & Blind-Test Harnesses Prove Production Readiness

You do not need prior DevOps or Kubernetes coursework to understand why **containers** and **blind-test harnesses** are the final exam of production data engineering.

### Virtual Machines vs. Linux Containers
When engineers first tried to isolate applications on shared servers, they used **Virtual Machines (VMs)**. Every VM boots an entire separate guest operating system (Windows or Linux kernel + gigabytes of OS files), consuming 4–10 GB of RAM and taking minutes to start.

A **Docker Container** shares the host machine's Linux kernel and packages *only* your application's user-space filesystem (Python 3.11 + `libgl1` + `requirements.txt` + your `.py` scripts). It starts in less than 1 second, uses a fraction of the RAM, and behaves **100% identically** everywhere Docker runs.

### What Happens During a "Blind Test / Chaos Batch" Defense
When your system is evaluated in production (and in your Unit 8 capstone lab), an automated test harness drops an unseen **"Chaos Batch"** (`datasets/unit_08_chaos_batch.json`) into your pipeline. You cannot hand-edit the input file or hardcode row IDs. Instead, your containerized pipeline must:
1. Ingest the unseen multi-modal batch cleanly.
2. Quarantine every injected defect (future weather timestamps, negative gallons, pitch-black frames, empty HTML notes) into `capstone_dlq.jsonl`.
3. Export verified Parquet tables and pass every automated `pytest` invariant check without throwing an unhandled exception.

This establishes our core rule for Unit 8:

> **The Production Handoff Rule:** Software is not ready for production until (1) its entire OS, C-library, and Python dependency tree is pinned inside a reproducible, non-root container, and (2) it survives an unseen multi-modal chaos batch without crashing or leaking corrupted data downstream.

---

## 2d. Why the "Works on My Machine" Tragedy Cost $1.2M (Failure Case Study)

To appreciate why containerization and reproducible handoffs are mandatory in data engineering, examine an authentic corporate tragedy.

A team of talented junior engineers developed a cutting-edge real-time logistics routing and delay-prediction system for a regional freight carrier. They spent four months refining their algorithms on their high-end local development laptops running macOS and Windows.

The client scheduled a high-stakes final evaluation with the Chief Technology Officer, VP of Supply Chain, and lead enterprise architects. If the demonstration succeeded, the system would receive a **\$1.2 million production rollout contract**.

### The Disaster in the Boardroom
The team arrived at corporate headquarters. The client provided a fresh, clean cloud staging server running Ubuntu 22.04 LTS and instructed the team to deploy their system:

```bash
git clone https://github.com/tswarmLCCC/COSC-2060-Student-Sandbox.git
python3 main.py
```

Within 12 seconds, the terminal exploded in red text:

```text
Traceback (most recent call last):
  File "main.py", line 4, in <module>
    import cv2
ModuleNotFoundError: No module named 'cv2'
```

The lead engineer stammered: *"Oh, we just need to install OpenCV. Let me run `pip install`..."*

When they ran `pip install opencv-python`, the staging server failed with a missing system C-library:
```text
ImportError: libGL.so.1: cannot open shared object file: No such file or directory
```

For 45 agonized minutes in front of the executive committee, the engineers frantically typed `sudo apt-get install`, battled version conflicts with Python 3.10 vs. 3.11, discovered that their local macOS NumPy binaries behaved differently than Linux glibc, and watched their demo freeze with an Out-Of-Memory segmentation fault.

The CTO closed his laptop:
> *"If this system requires an army of engineers to manually configure an operating system, it cannot survive in our automated Kubernetes cloud infrastructure. The demo is concluded."*

The company lost the \$1.2 million contract.

### The Lesson
**Code alone is not software.** Software is the code **plus** the exact Python runtime, the exact C-libraries (`libGL`, `libgomp`), the exact filesystem layout, the environment variables, and the network ports. Containers package all of these elements into a single, immutable artifact.

---

## 2e. "The Intermodal Shipping Container"

Before 1956, global ocean shipping was a logistical nightmare. Cargo arrived at docks in random wooden crates, barrels, and sacks. Longshoremen spent weeks hand-loading individual barrels into ship holds. Ships frequently sank because heavy sacks shifted during storms, and theft was rampant.

In 1956, Malcom McLean invented the standardized **Intermodal Shipping Container**—a sealed steel box with standard dimensions (40 &times; 8 &times; 8.5 feet).

The ship captain does not care what is inside the container (shoes, car engines, or apples). The container fits identically on a ship, on a flatbed semi-truck, or on a train car.

```
DOCKER IS THE INTERMODAL CONTAINER FOR CODE:
Inside the Container:  [Ubuntu Base + Python 3.11 + OpenCV + DuckDB + Polars + App Code]
Outside the Container: [Docker Engine / Kubernetes / Cloud AWS / Laptop]
Rule: "If it runs in the container on your laptop, it runs identically in the cloud!"
```

---

## 2f. Multi-Stage Dockerfile Hardening — Security & Minimal Footprint

In production, you must never ship an 8 GB development image containing compilers (`gcc`, `g++`) or run containers as `root`.

### Multi-Stage Architecture:
1. **Builder Stage:** Uses a build image to compile C-extensions and install wheel dependencies into a temporary virtual environment (`/opt/venv`).
2. **Runtime Stage:** Copies *only* the compiled virtual environment into a clean, minimal image (`python:3.11-slim`), sets up a non-privileged system user (`appuser`), and drops all root privileges.

```
BUILDER STAGE (Heavy: 1.5 GB) ──> Compiles wheels & packages
                                        │ (Copies only /opt/venv)
                                        ▼
RUNTIME STAGE (Lean: 180 MB)  ──> Non-root user + Healthcheck + Ports 8000/8001
```

### Guided Implementation Walkthrough — Production Multi-Stage `Dockerfile`

```dockerfile
# -------------------------------------------------------------
# STAGE 1: Build & Dependencies
# -------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install system compilation prerequisites
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install production dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# -------------------------------------------------------------
# STAGE 2: Hardened Production Runtime
# -------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Install runtime system libraries required by OpenCV & ML engines
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Security: Create non-root execution user (Principle of Least Privilege)
RUN groupadd -r appgroup && useradd -r -g appgroup -s /sbin/nologin appuser

WORKDIR /app
COPY . /app

# Grant read access to application directory
RUN chown -R appuser:appgroup /app
USER appuser

# Expose DaaS API and MCP ports
EXPOSE 8000 8001

# Production Container Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Production Entrypoint
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 2g. Step-by-Step Code Ramp-Up — Building the End-to-End Capstone Verifier

In this week's capstone lab, you will bring together the defensive patterns from Units 1–7 into a modular Python pipeline that processes an unseen multi-modal "Chaos / Blind Test Batch." Let's walk through how to structure a multi-subsystem verifier step by step.

### Step 1: Writing a Unified Dead-Letter Queue (DLQ) Collector
First, create a reusable helper class that any subsystem (Relational, Anomaly, Vision, or RAG) can call whenever it catches a corrupted record:

```python
import json
from datetime import datetime, timezone

class DeadLetterQueue:
    """Collects malformed or unsafe records across all pipeline stages without crashing the batch."""
    def __init__(self):
        self.items = []

    def quarantine(self, subsystem: str, record_id: str, raw_payload: dict, reason: str):
        self.items.append({
            "subsystem": subsystem,
            "record_id": str(record_id),
            "raw_payload": raw_payload,
            "error_reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def save_jsonl(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            for item in self.items:
                f.write(json.dumps(item) + "\n")

dlq = DeadLetterQueue()
dlq.quarantine("anomaly_engine", "TX-99", {"gallons": -10}, "gallons must be > 0")
print("Quarantined count:", len(dlq.items))
```

### Step 2: Auditing Each Modality Stage Before Export
Next, trace the exact defensive checks we run on each of the four data modalities in the capstone batch:

1. **Relational Stage (Unit 1 Check):**
   * Verify `act_arrival >= dep_time` and ensure weather observations are joined via `ASOF LEFT JOIN ... ON r.origin_city = w.city AND r.dep_time >= w.obs_time`. If a route record has corrupted timestamps (`act_arrival < dep_time`), quarantine it in `dlq`.
2. **Tabular Anomaly Stage (Unit 2 Check):**
   * Verify `gallons > 0` and `amount_usd > 0`. Quarantine negative sensor glitches in `dlq`, then compute Z-scores (`(col - mean) / std`) and physical anomaly flags (`gallons > 300` or `implied_speed_mph > 75`) on the clean rows using Polars.
3. **Visual Sensor Stage (Unit 3 Check):**
   * Verify each image has positive dimensions (`width > 0 and height > 0`) and is not a pitch-black broken camera frame (`mean_brightness >= 5.0`). Quarantine broken frames in `dlq`, and compute letterbox scale `r`, padding `(pad_x, pad_y)`, and normalized `[0.0, 1.0]` YOLO coordinates for valid frames.
4. **Unstructured Text / RAG Stage (Unit 4 Check):**
   * Strip HTML tags and normalize whitespace. If a document is empty after cleaning (`len(cleaned_text) == 0`), quarantine it in `dlq`. Otherwise, split into overlapping chunks and attach metadata.

```python
def process_vision_records(image_records: list[dict], dlq: DeadLetterQueue) -> list[dict]:
    """Validates image metadata, quarantines broken frames, and computes 640x640 letterbox parameters."""
    valid_manifests = []
    for rec in image_records:
        img_id = rec.get("image_id", "UNKNOWN")
        w, h = rec.get("width", 0), rec.get("height", 0)
        brightness = rec.get("mean_brightness", 0.0)

        if w <= 0 or h <= 0 or brightness < 5.0:
            dlq.quarantine("vision", img_id, rec, f"Invalid frame ({w}x{h}) or dark frame (brightness={brightness})")
            continue

        ratio = min(640.0 / w, 640.0 / h)
        new_w, new_h = int(round(w * ratio)), int(round(h * ratio))
        pad_x, pad_y = (640 - new_w) // 2, (640 - new_h) // 2
        valid_manifests.append({
            "image_id": img_id,
            "scale_ratio": round(ratio, 4),
            "pad_x": pad_x,
            "pad_y": pad_y
        })
    return valid_manifests
```

### Step 3: Writing Automated Verification Assertions (`pytest` & Audit Report)
Finally, a production pipeline verifies its own outputs before reporting success:
* Assert that the exported Parquet table exists and has `> 0` rows.
* Assert that zero rows in the exported table have `weather_obs_time > dep_time`.
* Assert that all normalized YOLO coordinates lie within `[0.0, 1.0]`.
* Write the complete summary dictionary to `output/capstone_audit_report.json`.

---

## 2h. Practice Exercises & Formative Self-Check FAQ

Try these three exercises in your GitHub Codespaces sandbox (`units/unit_08_capstone_defense_and_production/`) before starting the capstone lab:

1. **Exercise 1 (Inspecting Our Own Sandbox Container):** Open `.devcontainer/devcontainer.json` in your workspace and examine how the container `image`, `postCreateCommand`, and VS Code `extensions` are configured. You have been developing inside a reproducible Linux container all semester!
2. **Exercise 2 (Testing Multi-Modal DLQ Quarantine):** Run `coding_clinic.ipynb` in `units/unit_08_capstone_defense_and_production/` and inspect how corrupted records from different modalities are logged with their subsystem name and error reason.
3. **Exercise 3 (Running `pytest`):** Run `pytest` in your terminal to observe how automated test functions (`def test_...(): assert ...`) verify pipeline invariants in milliseconds.

### Common Traps & Formative Self-Check FAQ

* **Question 1: Why must Docker bind to `0.0.0.0` instead of `127.0.0.1`?**  
  *Answer:* Inside a container, `127.0.0.1` refers exclusively to the container's own internal loopback interface. If Uvicorn listens on `127.0.0.1`, requests from outside the container cannot reach it. Listening on `0.0.0.0` binds to all network interfaces, allowing host port forwarding (`-p 8000:8000`) to succeed.

* **Question 2: What is the Blind Test Batch defense protocol?**  
  *Answer:* During your capstone evaluation, the review harness injects an unseen batch of raw files containing edge-case anomalies (corrupted image headers, fuel card teleportation, negative gallons, and malformed rows). Your automated orchestrator and API must process the batch, isolate the bad rows to the DLQ, and serve clean predictions without throwing unhandled exceptions.

* **Question 3: Why do we copy `requirements.txt` and run `pip install` *before* running `COPY . /app` in a `Dockerfile`?**  
  *Answer:* Docker caches each instruction layer in order. Because you edit your `.py` files frequently while rarely changing `requirements.txt`, copying and installing `requirements.txt` first allows Docker to reuse the cached dependency layer whenever you rebuild after code edits.

---

## 3. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical specifications before beginning your applied lab:

1. **[Docker Official Documentation: Best Practices for Writing Dockerfiles](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)**
   *Learn how to optimize image caching, minimize layer count, manage secrets, and eliminate unnecessary bloat.*

2. **[Docker Documentation: Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)**
   *Understand how separating build tools from runtime environments reduces container attack surface and shrinks image sizes by 80%.*

3. **[OWASP Container Security Verification Standard](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)**
   *Review the gold standard for container hardening: non-root users, read-only root filesystems, and dropped Linux capabilities.*

4. **[The Twelve-Factor App: Cloud-Native Architecture Principles](https://12factor.net/)**
   *Study the foundational methodology for designing modern, scalable, container-ready services.*

5. **[Docker Compose Specification: Multi-Container Environments](https://docs.docker.com/compose/compose-file/)**
   *Master multi-service local orchestration, volume mounting, network bridging, and dependency startup ordering.*

---

## 4. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to observe containerization and production hardening in action:

### Docker in 100 Seconds <span style="font-size: 0.9em; color: #64748b;">(Fireship - 2:15)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Docker in 100 Seconds" src="https://www.youtube.com/embed/Gjnup-PuquQ" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=Gjnup-PuquQ" target="_blank" rel="noopener">Open video in new tab (2:15)</a></p>

### Docker for Data Engineers: Containerizing Python Applications <span style="font-size: 0.9em; color: #64748b;">(Patrick Loeber - Core Walkthrough)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Docker Tutorial for Python Applications" src="https://www.youtube.com/embed/bi0cKgmRuiA" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=bi0cKgmRuiA" target="_blank" rel="noopener">Open video in new tab</a></p>

### Top 8 Docker Best Practices for Production & Security <span style="font-size: 0.9em; color: #64748b;">(TechWorld with Nana - Multi-Stage & Non-Root)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Docker Best Practices for Production" src="https://www.youtube.com/embed/8vXoMqWgbQQ" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=8vXoMqWgbQQ" target="_blank" rel="noopener">Open video in new tab</a></p>

---

## 5. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for Unit 8 will appear in this designated container.</p>
</div>
