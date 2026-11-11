# COSC 2060: Modern Data Engineering & AI Infrastructure — Student Lab Sandbox

Welcome to the hands-on student repository for **COSC 2060: Modern Data Engineering & AI Infrastructure**. This sandbox is pre-configured with **Python 3.11**, **DuckDB**, **Polars**, **Scikit-Learn**, **OpenCV**, **Sentence-Transformers**, **FastAPI**, **Pydantic v2**, and **Docker-in-Docker** so you can build leak-free feature matrices, anomaly pipelines, computer vision manifests, RAG ingestion engines, DaaS microservices, and MCP tool bridges directly in your web browser.

<!-- TEMPLATE_STATUS_BANNER -->

---

## 🚀 Getting Started: 2-Step Sandbox Setup

Because this repository is a **GitHub Template**, you must first create your own personal copy before launching your Codespace. **(Do NOT launch a Codespace directly on the instructor's `tswarmLCCC` template repository!)**

### Step 1: Create Your Personal Sandbox Repository (One-Time Setup) 
1. Click the button below (or click the green **"Use this template" $\rightarrow$ "Create a new repository"** button in the top-right corner of this GitHub page):

   [![Use This Template](https://img.shields.io/badge/Step_1-Create_Your_Personal_Sandbox_Repo-2ea44f?style=for-the-badge&logo=github)](https://github.com/new?template_owner=tswarmLCCC&template_name=COSC-2060-Student-Sandbox&owner=%40me&name=COSC-2060-Student-Sandbox&description=My+COSC+2060+Data+Engineering+Sandbox&visibility=private)

2. Name your new repository **`COSC-2060-Student-Sandbox`**, set visibility to **Private** (or Public), and click **Create repository**.
3. Wait ~15 seconds after your repository is created—an automated GitHub Action (`.github/workflows/personalize_template.yml`) will automatically update the Codespaces badge in Step 2 below so it points to **your personal repository**! *(Refresh your browser page once to see the updated badge).*

### Step 2: Launch Your Personal GitHub Codespace
Once you are inside **your own repository** (`<your-username>/COSC-2060-Student-Sandbox`), launch your cloud environment using either method below:

* **Option A — Via the GitHub UI Button (Always Works Immediately)**:
  1. Click the green **`<> Code`** button near the top-right of your repository page.
  2. Click the **`Codespaces`** tab.
  3. Click **`Create codespace on main`** (or click your existing Codespace name to resume it).

* **Option B — Via Your Personalized 1-Click Badge**:
  *(Note: Only click this badge from inside **your own** `<your-username>/COSC-2060-Student-Sandbox` repository after completing Step 1!)*

  [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/tswarmLCCC/COSC-2060-Student-Sandbox?quickstart=1)

*Wait ~90 seconds for your container to spin up on first launch. Once the terminal displays `>>> COSC 2060 Sandbox Ready!`, all Python engines and your 1,000,000-row Apex Logistics datasets are live and pre-seeded!*

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
├── .github/workflows/         # Auto-personalizes README Codespaces badge for student repos
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
6. You can both commit/push to your personal GitHub repo (`git add . && git commit -m "Complete Lab 1" && git push`) AND download your `lab{N}_{yourlastname}.py` file from VS Code (Right-click file $\rightarrow$ **Download...**) to upload it to the **Applied Lab Assignment in Canvas**.
