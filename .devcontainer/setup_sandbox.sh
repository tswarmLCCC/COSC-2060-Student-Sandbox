#!/bin/bash
set -e

echo "======================================================================"
echo "  COSC 2060: Initializing Modern Data Engineering & AI Sandbox..."
echo "======================================================================"

echo ">>> [1/5] Installing pip on system Python (/usr/bin/python) & devcontainer Python..."
sudo apt-get update -qq && sudo apt-get install -y -qq python3-pip python3-venv libgl1
sudo rm -f /usr/lib/python3*/EXTERNALLY-MANAGED || true
export PIP_BREAK_SYSTEM_PACKAGES=1

echo ">>> [2/5] Configuring Git directory trust & line endings..."
git config --global --add safe.directory '*'
git config --global core.autocrlf input

echo ">>> [3/5] Installing core Data Engineering stack & registering Jupyter Kernel..."
/usr/bin/python3 -m pip install --upgrade pip ipykernel jupyter duckdb pyarrow polars pandas numpy scikit-learn opencv-python-headless Pillow fastapi "uvicorn[standard]" "pydantic>=2.6.0" httpx pytest ruff
/usr/bin/python3 -m ipykernel install --user --name python3 --display-name "Python 3 (COSC 2060 Sandbox)"

if [ -x "/usr/local/bin/python" ] && [ "/usr/local/bin/python" != "/usr/bin/python3" ]; then
    /usr/local/bin/python -m pip install --upgrade pip ipykernel jupyter duckdb pyarrow polars pandas numpy scikit-learn opencv-python-headless Pillow fastapi "uvicorn[standard]" "pydantic>=2.6.0" httpx pytest ruff
fi

echo ">>> [4/5] Seeding Apex Logistics multimodal datasets (DuckDB, 1M Parquet, Vision, Logs)..."
/usr/bin/python3 datasets/seed_all_datasets.py

echo ">>> [5/5] Installing CPU-only PyTorch & Sentence-Transformers (Unit 4 RAG)..."
/usr/bin/python3 -m pip install -r requirements.txt
/usr/bin/python3 -c "
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
