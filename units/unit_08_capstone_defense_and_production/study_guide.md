# Unit 8: Required Readings, Concepts & Video Lectures

Welcome to the instructional reading and study guide for **Unit 8: Capstone Defense, Containerization & Production Verification**. This page organizes the week's learning materials into four sections:

1. **Instructor Lecture & Conceptual Deep Dive:** Learn how all seven layers of our course fit together into an end-to-end architecture, what our final Capstone Audit Manifest and Docker container configuration look like, how containers eliminate environment mismatches, and how to defend your pipeline against an unseen blind test batch.
2. **Required Readings & Tutorial Guides:** Explore official documentation on Dockerfile best practices, multi-stage builds, OWASP container security, and the Twelve-Factor App methodology.
3. **Required Micro-Video Lectures (Embedded):** Watch focused video tutorials covering Docker containers, packaging Python data pipelines, and production container security.
4. **Institutional Video Lecture Embeds:** Access instructor announcements and capstone walkthrough recordings.

*Work through each section in sequence as part of your 150-minute self-study block before starting the capstone lab.*

---

## 1. Instructor Lecture & Conceptual Deep Dive

### Bringing Every Layer Together for Production Handoff

Over the past seven units, you have built every core layer of a modern data and AI infrastructure system:
* **Unit 1 (Relational Feature Tables):** Point-in-time `ASOF JOIN` and rolling lag windows in DuckDB.
* **Unit 2 (High-Speed Outlier Detection):** Multithreaded `LazyFrame` filtering and Z-score standardization in Polars.
* **Unit 3 (Computer Vision Tensors):** Aspect-ratio-preserving letterbox padding and normalized YOLO coordinates in OpenCV/NumPy.
* **Unit 4 (Unstructured Text & RAG):** HTML/whitespace scrubbing, sliding-window chunking, and cosine similarity vector search.
* **Unit 5 (Data as a Service):** Pydantic v2 data contracts and REST API endpoints in FastAPI.
* **Unit 6 (Agentic Interfaces):** Read-only JSON-RPC 2.0 tool servers using the Model Context Protocol (MCP).
* **Unit 7 (Orchestration & Fault Tolerance):** Topological DAG execution, idempotent writes, exponential backoff, and Dead-Letter Queues (DLQs).

In **Unit 8**, we bring all of these pieces together into a single, end-to-end **Capstone Verification Pipeline** and learn how data engineers package their code inside **Docker Containers** so it runs identically on any laptop or cloud server.

```
RAW MULTIMODAL BATCH (Tabular + Sensor + Vision + Text)
         │
         ▼
[1. Defensive Validation & Dead-Letter Queue (DLQ)]
         │
         ▼
[2. DuckDB / Polars / OpenCV / RAG Processing Engines]
         │
         ▼
[3. FastAPI + MCP Service Layer + Capstone Audit Report]
```

#### Measurable Learning Objectives
* **Integrate** tabular (DuckDB/Polars), visual (OpenCV/NumPy), unstructured text (RAG chunking), and service/contract layers (Pydantic/MCP) into a unified end-to-end pipeline.
* **Process** an unseen **"Chaos / Blind Test Batch"** containing mixed valid records and intentional corruptions (negative values, future-leaked timestamps, zero-dimension images, empty text) without unhandled crashes.
* **Explain** how Docker containers package Python code, system C-libraries (`libgl1`), and dependencies into a reproducible image.
* **Write** a hardened multi-stage `Dockerfile` using a non-root user and healthcheck endpoint.
* **Generate** a verified `capstone_audit_report.json` and curated `.parquet` output proving zero data leakage and 100% contract compliance.

---

### What Our Output Looks Like and Where the Data Comes From

#### The Purpose
Our goal in Unit 8 is to build the **End-to-End Capstone Defense Pipeline** (`lab8_capstone_runner.py`). It ingests a multi-modal operational batch—containing route telemetry, fuel swipes, inspection image metadata, and mechanic notes—quarantines any corrupted records into a Dead-Letter Queue, runs the valid records through our feature, anomaly, vision, and RAG stages, and outputs a comprehensive **`capstone_audit_report.json`** alongside the curated `.parquet` tables.

#### Why Production Systems Need End-to-End Integration Audits
When you test each unit's script by itself on clean sample data, it is easy to assume everything works. In production, however, data flows through multiple stages in sequence, and real incoming batches often contain multiple types of defects at the same time:
* A route row might have a weather timestamp recorded *after* departure (temporal leakage attempt).
* A fuel swipe might have `-120.0` gallons or a missing `driver_id`.
* A camera frame might be `0 x 0` pixels or completely black (`mean_brightness < 5.0`).
* A mechanic work order might be empty HTML tags (`"<p>   </p>"`).

Your capstone pipeline proves that your system can ingest an entire messy multi-modal batch in one command, catch and quarantine every defective item in the Dead-Letter Queue (`dlq_quarantine.jsonl`), and produce clean, verified outputs for all valid items.

#### Where the Raw Data Comes From (Source Systems)
The capstone pipeline ingests a combined operational drop (`datasets/unit_08_chaos_batch.json` or multi-table seed) representing a full day of fleet operations across all four source systems:
1. **Dispatch & NOAA Weather Logs** (Relational / Temporal)
2. **POS Fleet Fuel Card Stream** (High-Volume Tabular)
3. **Terminal Gate Camera Frames & Bounding Boxes** (Visual Sensor)
4. **Shop Bay Maintenance Work Orders** (Unstructured Text)

#### Sample Output Dataset (The Target Capstone Audit Report Shape)
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

---

### Why "It Works on My Laptop" Fails in Production

Suppose you finish writing your Python pipeline on your personal Windows or Mac laptop, and you email `pipeline.py` to your company's cloud operations team so they can deploy it on a Linux server.

Ten minutes later, they write back: *"Your script crashed immediately on startup."*

Why does code that works on your laptop fail on another machine?
1. **Missing Python Packages or Version Drift:** Your laptop had `pydantic==2.9.0` installed, while the server had an older `pydantic==1.10.0` where `.model_dump()` doesn't exist.
2. **Missing Operating System C-Libraries:** Libraries like OpenCV (`cv2`), DuckDB, and Polars rely on compiled C/C++ and Rust libraries (such as `libGL.so.1` on Linux). Even if `pip install` finishes, importing `cv2` on a bare Linux server fails if the operating system package `libgl1` isn't installed.
3. **Hardcoded File Paths:** A path written with Windows backslashes (`"C:\\Users\\Trevor\\output\\data.parquet"`) fails immediately on a Linux cloud server.

---

### How Docker Containers Solve Environment Drift

To make sure code runs identically everywhere, software and data engineers use **Docker Containers** (in fact, the GitHub Codespaces sandbox you have been using all semester is a Docker container defined by `.devcontainer/devcontainer.json`!).

Think of a **standardized steel shipping container** on a cargo ship:
* Before shipping containers were invented, workers had to load individual wooden barrels, sacks, and crates onto ships by hand.
* With a standardized steel shipping container, the factory packs everything inside the box once. That exact same sealed box can be lifted onto a train, a semi-truck, or a cargo ship anywhere in the world without ever unpacking the contents.

```
WHAT IS INSIDE A DOCKER CONTAINER IMAGE:
┌────────────────────────────────────────────────────────────┐
│  Your Pipeline Scripts (lab8_capstone_runner.py, api.py)   │
│  Python Libraries (duckdb, polars, opencv, fastapi, ...)   │
│  Python Runtime (Python 3.11)                              │
│  OS System Libraries (Debian/Ubuntu Slim + libgl1)         │
└────────────────────────────────────────────────────────────┘
Rule: If it runs inside the container during testing, it runs identically in the cloud!
```

#### Three Production Dockerfile Best Practices
When writing a `Dockerfile` for a data engineering service, follow three rules:
1. **Multi-Stage Builds (`FROM ... AS builder` then `FROM ... AS runtime`):** Install heavy C compilers (`build-essential`) only in a temporary `builder` stage to compile Python wheels into `/opt/venv`, then copy *only* `/opt/venv` into a clean, lightweight `runtime` stage. This shrinks your container size by 70–80%.
2. **Run as a Non-Root User (`USER appuser`):** Never run web servers or data pipelines as the Linux `root` administrator inside a container. Creating a dedicated unprivileged user (`useradd -r appuser`) limits damage if an attacker ever finds a vulnerability.
3. **Include a `HEALTHCHECK` and Bind to `0.0.0.0`:** Add a `HEALTHCHECK` instruction that pings `/health` every 30 seconds so cloud orchestrators know if the service is alive, and bind Uvicorn to `--host 0.0.0.0` so traffic from outside the container can reach port `8000`.

```dockerfile
# STAGE 1: Builder (Compiles dependencies into /opt/venv)
FROM python:3.11-slim AS builder
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# STAGE 2: Lean Production Runtime
FROM python:3.11-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create and switch to non-root user
RUN useradd -r -s /sbin/nologin appuser
WORKDIR /app
COPY . /app
RUN chown -R appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Step-by-Step Code Ramp-Up: Building the End-to-End Capstone Verifier

In this week's lab, you will bring together the defensive patterns from Units 1–7 into a clean, modular Python pipeline that processes a multi-modal "Chaos Batch." Let's walk through how to structure a multi-subsystem verifier step by step.

#### Step 1: Writing a Unified Dead-Letter Queue (DLQ) Collector
First, let's create a simple helper class or list that any subsystem (Relational, Anomaly, Vision, or RAG) can call whenever it catches a bad record:

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

#### Step 2: Auditing Each Modality Stage Before Export
Next, let's trace the exact defensive check we run on each of the four data modalities in the capstone batch:

1. **Relational Stage (Unit 1 Check):**
   * Check that `act_arrival >= dep_time` and that any matched weather observation satisfies `obs_time <= dep_time`. If a row has corrupt timestamps (`act_arrival < dep_time`), quarantine it in `dlq` and exclude it from the DuckDB `ASOF LEFT JOIN` feature table.
2. **Tabular Anomaly Stage (Unit 2 Check):**
   * Check that `gallons > 0` and `amount_usd > 0`. Quarantine negative sensor glitches in `dlq`, then compute Z-scores (`(col - mean) / std`) and physical anomaly flags (`gallons > 300` or `implied_speed_mph > 75`) on the clean rows using Polars.
3. **Visual Sensor Stage (Unit 3 Check):**
   * Check that each image has positive dimensions (`width > 0 and height > 0`) and is not a pitch-black broken camera frame (`mean_brightness >= 5.0`). Quarantine broken frames in `dlq`, and compute letterbox scale `r`, padding `(pad_x, pad_y)`, and normalized `[0.0, 1.0]` YOLO coordinates for valid frames.
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
            dlq.quarantine("vision", img_id, rec, f"Invalid frame dimensions ({w}x{h}) or dark frame (brightness={brightness})")
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

#### Step 3: Writing Automated Assertions (`pytest` / Verification Audit)
Finally, a production pipeline verifies its own outputs before reporting success:
* Assert that the exported Parquet table exists and has `> 0` rows.
* Assert that zero rows in the exported table have `weather_obs_time > dep_time`.
* Assert that all normalized YOLO coordinates lie within `[0.0, 1.0]`.
* Write the complete summary dictionary to `output/capstone_audit_report.json`.

---

### Practice Exercises and Common Questions

Try these three exercises in your GitHub Codespaces sandbox (`units/unit_08_capstone_defense_and_production/`) before starting the capstone lab:

1. **Exercise 1 (Inspecting Our Own Sandbox Container):** Open `.devcontainer/devcontainer.json` in your workspace and look at how the `image`, `postCreateCommand`, and VS Code `extensions` are configured. You have been working inside a Linux container all semester!
2. **Exercise 2 (Testing the DLQ Quarantine):** Run `coding_clinic.py` in `units/unit_08_capstone_defense_and_production/` and inspect how corrupted records from different modalities are logged with their subsystem name and error reason.
3. **Exercise 3 (Running `pytest`):** Run `pytest` in your terminal to see how automated test functions (`def test_...(): assert ...`) verify pipeline outputs in milliseconds.

#### Common Questions & Troubleshooting

* **Question 1: Why does a FastAPI server inside Docker need `--host 0.0.0.0` instead of `--host 127.0.0.1`?**  
  *Answer:* Inside a Docker container, `127.0.0.1` (`localhost`) only listens to traffic coming from *inside* that exact same container. Binding to `0.0.0.0` tells the server to listen on all network interfaces so requests forwarded from your host computer or cloud load balancer can reach it.

* **Question 2: Why do we copy `requirements.txt` and run `pip install` *before* running `COPY . /app` in a `Dockerfile`?**  
  *Answer:* Docker caches each step (layer) of a `Dockerfile`. You edit your `.py` code files every day, but you rarely change `requirements.txt`. By installing `requirements.txt` first, Docker reuses the cached package installation layer whenever you rebuild after editing your Python code, making builds take 2 seconds instead of 3 minutes!

* **Question 3: In the Capstone Lab, should my script crash with an exception when it encounters a corrupted record in the Chaos Batch?**  
  *Answer:* No! Your script should catch corrupted records using defensive validation, quarantine them into the Dead-Letter Queue (`dlq`), and finish processing all valid records cleanly (`exit code 0`). Only raise an unhandled exception if a *system invariant* fails (such as leakage making it into the final output table).

---

## 2. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical references before beginning your capstone lab:

1. **[Docker Official Documentation: Best Practices for Writing Dockerfiles](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)**
   *Learn how layer caching, `.dockerignore`, and minimal base images keep containers fast and small.*

2. **[Docker Documentation: Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)**
   *Understand how separating build tools from the runtime image shrinks container sizes and improves security.*

3. **[OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)**
   *Review container hardening standards: non-root users, read-only filesystems, and secret management.*

4. **[The Twelve-Factor App Methodology](https://12factor.net/)**
   *Study the industry standard principles for building portable, cloud-ready services.*

5. **[Docker Compose File Specification](https://docs.docker.com/compose/compose-file/)**
   *See how multi-container services, volumes, and healthcheck dependencies are configured.*

---

## 3. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to see containerization and production best practices in action:

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

## 4. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for Unit 8 will appear in this designated container.</p>
</div>
