#!/bin/bash
set -e

echo "======================================================================"
echo "  COSC 2060: Initializing Modern Data Engineering & AI Sandbox..."
echo "======================================================================"

echo ">>> [1/5] Ensuring system pip & unified Python paths..."
if [ -x "/usr/local/python/current/bin/python" ]; then
    PYTHON_BIN="/usr/local/python/current/bin/python"
    sudo ln -sf /usr/local/python/current/bin/python /usr/local/bin/python || true
    sudo ln -sf /usr/local/python/current/bin/pip /usr/local/bin/pip || true
else
    PYTHON_BIN="$(which python3 || which python)"
fi

# Ensure Debian/Ubuntu system python (/usr/bin/python3) also has pip so VS Code never fails if a user picks it
if ! /usr/bin/python3 -m pip --version >/dev/null 2>&1; then
    sudo apt-get update -qq && sudo apt-get install -y -qq python3-pip python3-venv >/dev/null 2>&1 || true
fi

echo "    -> Active Python: $PYTHON_BIN ($($PYTHON_BIN --version))"

echo ">>> [2/5] Configuring Git directory trust & line endings..."
git config --global --add safe.directory '*'
git config --global core.autocrlf input

echo ">>> [3/5] Registering Jupyter Kernel & installing core Data Engineering stack..."
"$PYTHON_BIN" -m pip install --upgrade pip ipykernel jupyter duckdb pyarrow polars pandas numpy scikit-learn opencv-python-headless Pillow fastapi "uvicorn[standard]" "pydantic>=2.6.0" httpx pytest ruff -q
"$PYTHON_BIN" -m ipykernel install --user --name python3 --display-name "Python 3.11 (COSC 2060 Sandbox)"

echo ">>> [4/5] Seeding Apex Logistics multimodal datasets (DuckDB, 1M Parquet, Vision, Logs)..."
"$PYTHON_BIN" datasets/seed_all_datasets.py

echo ">>> [5/5] Installing CPU-only PyTorch & Sentence-Transformers (Unit 4 RAG)..."
"$PYTHON_BIN" -m pip install -r requirements.txt -q
"$PYTHON_BIN" -c "
try:
    from sentence_transformers import SentenceTransformer
    SentenceTransformer('all-MiniLM-L6-v2')
    print('    -> Cached all-MiniLM-L6-v2 embedding model successfully.')
except Exception as e:
    print(f'    -> Note: Offline or skipped model pre-download ({e}). Model will download on first Unit 4 run.')
"

echo "======================================================================"
echo "  >>> COSC 2060 Sandbox Ready!"
echo "  • Interactive Notebooks : Open any 'ds_to_engine.ipynb' inside units/"
echo "  • Synchronous Clinics   : Run 'python units/unit_01_.../coding_clinic.py'"
echo "  • Weekly Applied Labs   : Edit and run 'labN_starter.py' inside units/"
echo "  • Disaster Recovery     : Run './reset_sandbox.sh' anytime to reset data"
echo "======================================================================"
