# COSC 2060: Modern Data Engineering & AI Infrastructure — Student Lab Sandbox

Welcome to the hands-on student repository for **COSC 2060: Modern Data Engineering & AI Infrastructure**. This sandbox is pre-configured with **Python 3.11**, **DuckDB**, **Polars**, **Scikit-Learn**, **OpenCV**, **Sentence-Transformers**, **FastAPI**, **Pydantic v2**, and **Docker-in-Docker** so you can build leak-free feature matrices, anomaly pipelines, computer vision manifests, RAG ingestion engines, DaaS microservices, and MCP tool bridges directly in your web browser.

---

## 🚀 1-Click Quick Start (GitHub Codespaces)

Click the button below to launch your personal, cloud-hosted Data Engineering & AI development environment:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/tswarmLCCC/COSC-2060-Student-Sandbox?quickstart=1)

*Wait ~90 seconds for your container to spin up. Once the terminal displays `>>> COSC 2060 Sandbox Ready!`, all Python engines and your 1,000,000-row Apex Logistics datasets are live and pre-seeded!*

---

## 🛠️ Three Ways to Work in This Sandbox

### 1. Interactive "DS Prototype $\rightarrow$ DE Engine" Notebooks (`ds_to_engine.ipynb`)
Each unit folder includes a guided Jupyter Notebook showing how fragile Data Science prototypes are refactored into defensive Data Engineering engines:
1. Open the current unit folder (e.g., `units/unit_01_relational_foundations/`).
2. Click **`ds_to_engine.ipynb`**.
3. Click **Run All** (or press `Shift + Enter` on each cell) using the pre-configured `/usr/local/bin/python` kernel.

### 2. Synchronous Coding Clinics (`coding_clinic.py`)
Follow along during class walkthroughs ("I Do, We Do, You Do") directly in the terminal:
```bash
python units/unit_01_relational_foundations/coding_clinic.py
```

### 3. Weekly Applied Lab Starters (`lab{N}_starter.py`)
Complete your graded 100-point weekly engineering lab using the pre-scaffolded starter script with built-in defensive assertions:
```bash
cd units/unit_01_relational_foundations
python lab1_starter.py
```

---

## 🔄 Disaster Recovery: Corrupted Your Data or Outputs?

If an experimental pipeline overwrites your DuckDB tables, corrupts a Parquet file, or fills `output/` with broken manifests, restore your data environment to pristine condition anytime from the repository root:

```bash
./reset_sandbox.sh
```
*Note: This regenerates all files in `datasets/` and cleans temporary `output/` folders. It **NEVER** touches or deletes your `.py` scripts or `.ipynb` notebooks inside `units/`.*

---

## 📁 Repository Structure

```text
.
├── .devcontainer/             # Automated Python 3.11 + Docker-in-Docker configuration
├── .vscode/                   # Pre-configured Python, Jupyter, Ruff, & Parquet Viewer settings
├── datasets/                  # Master dataset generators (DuckDB, 1M Parquet, Vision, Logs)
├── requirements.txt           # CPU-optimized PyTorch, Headless OpenCV, DuckDB, Polars, FastAPI
├── reset_sandbox.sh           # 1-click dataset & output recovery script
└── units/                     # 8 Bi-Weekly Guided Learning & Applied Engineering Units
    ├── unit_01_relational_foundations/
    ├── unit_02_anomaly_detection_engines/
    ├── unit_03_visual_sensor_and_multimodal/
    ├── unit_04_unstructured_text_and_vector_rag/
    ├── unit_05_data_as_a_service_and_apis/
    ├── unit_06_agentic_interfaces_and_mcp/
    ├── unit_07_orchestration_and_automation/
    └── unit_08_capstone_defense_and_production/
```

Inside **each unit folder**, you will find:
* `ds_to_engine.ipynb`: Interactive Jupyter Notebook bridging Data Science prototypes to production Data Engineering pipelines.
* `coding_clinic.py`: Runnable synchronous class walkthrough script ("I Do, We Do, You Do").
* `lab{N}_starter.py`: Starter template with mock data initialization and automated defensive tests.
* `lab_guide.md`: Detailed business scenario, architecture specifications, and step-by-step instructions.
* `lab_rubric.md`: The 100-point grading rubric used in Canvas SpeedGrader.
* `study_guide.md`: Asynchronous OER textbook chapters, architectural diagrams, and focus concepts.
* `self_check_drills.md`: Interactive diagnostic questions and syntax traces to complete before class.

---

## 🗺️ 16-Week / 8-Unit Progression

| Unit | Weeks | Title | Core Stack | Graded Lab Deliverable |
| :--- | :--- | :--- | :--- | :--- |
| **Unit 1** | 1–2 | The Relational Foundation | DuckDB, `ASOF JOIN`, Window Lag | `lab1_yourlastname.py` |
| **Unit 2** | 3–4 | The Anomaly Engine | Polars LazyFrames, Isolation Forest | `lab2_yourlastname.py` |
| **Unit 3** | 5–6 | The Visual Sensor Layer | OpenCV Letterboxing, YOLO Coordinates | `lab3_yourlastname.py` |
| **Unit 4** | 7–8 | Unstructured Text & Vector RAG | Sliding-Window Chunking, MiniLM-L6-v2 | `lab4_yourlastname.py` |
| **Unit 5** | 9–10 | Data as a Service (API Layer) | FastAPI, Pydantic v2, `TestClient` | `lab5_yourlastname.py` |
| **Unit 6** | 11–12 | The Agentic Interface (MCP) | Model Context Protocol, JSON-RPC Guardrails | `lab6_yourlastname.py` |
| **Unit 7** | 13–14 | Orchestration & Automation | Asset DAGs, Exponential Backoff, DLQ | `lab7_yourlastname.py` |
| **Unit 8** | 15–16 | Capstone Defense & Production | Multi-Stage `Dockerfile`, Blind Batch Audit | `lab8_yourlastname.py` & `Dockerfile` |

---

## 📝 How to Complete and Submit Weekly Labs

1. Open the unit folder for the current unit (e.g., `units/unit_01_relational_foundations/`).
2. Read the business scenario and specifications in `lab_guide.md` and review `lab_rubric.md`.
3. Open `lab{N}_starter.py` and implement your pipeline logic under each `# TODO` challenge section.
4. **Verify your pipeline:** Run your script in the terminal (`python lab1_starter.py`) and confirm all built-in `assert` verification checks print `PASS`.
5. Save a copy of your completed file as `lab{N}_{yourlastname}.py` (e.g., `lab1_smith.py`).
6. Download/export your `lab{N}_{yourlastname}.py` file from VS Code (Right-click file $\rightarrow$ **Download...**) and upload it to the corresponding **Applied Lab Assignment in Canvas**.

cd "c:\dev\Course-Content-Agentic-Template\courses\cosc-2060-data-engineering\student_sandbox_template"
git init -b main
git add .
git commit -m "Initial release: COSC 2060 Student Lab Sandbox"
git remote add origin https://github.com/tswarmLCCC/COSC-2060-Student-Sandbox.git
git push -u origin main