#!/bin/bash
set -e

PYTHON_BIN="/usr/local/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="$(which python3)"
fi

echo "======================================================================"
echo "  COSC 2060: Initializing Modern Data Engineering & AI Sandbox..."
echo "  Using Python Interpreter: $PYTHON_BIN ($($PYTHON_BIN --version))"
echo "======================================================================"

echo ">>> [1/5] Configuring Git directory trust & line endings..."
git config --global --add safe.directory '*'
git config --global core.autocrlf input

echo ">>> [2/5] Registering Jupyter Kernel & installing fast core engines (DuckDB, Polars, Arrow)..."
"$PYTHON_BIN" -m pip install --upgrade pip ipykernel jupyter duckdb pyarrow polars pandas numpy scikit-learn opencv-python-headless Pillow fastapi "uvicorn[standard]" "pydantic>=2.6.0" httpx pytest ruff -q
"$PYTHON_BIN" -m ipykernel install --user --name python3 --display-name "Python 3.11 (COSC 2060 Sandbox)"

echo ">>> [3/5] Seeding Apex Logistics multimodal datasets (DuckDB, 1M Parquet, Vision, Logs)..."
"$PYTHON_BIN" datasets/seed_all_datasets.py

echo ">>> [4/5] Installing CPU-only PyTorch & Sentence-Transformers (Unit 4 RAG)..."
"$PYTHON_BIN" -m pip install -r requirements.txt -q

echo ">>> [5/5] Pre-warming local Sentence-Transformers model cache (all-MiniLM-L6-v2)..."
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
