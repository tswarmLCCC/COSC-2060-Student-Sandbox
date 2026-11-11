#!/bin/bash
set -e

echo "======================================================================"
echo "  COSC 2060: Initializing Modern Data Engineering & AI Sandbox..."
echo "======================================================================"

echo ">>> [1/4] Configuring Git directory trust & line endings..."
git config --global --add safe.directory '*'
git config --global core.autocrlf input

echo ">>> [2/4] Installing Python Data Engineering & AI stack (pip)..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m ipykernel install --user --name python3 --display-name "Python 3.11 (COSC 2060 Sandbox)"

echo ">>> [3/4] Seeding Apex Logistics multimodal datasets (DuckDB, 1M Parquet, Vision, Logs)..."
python datasets/seed_all_datasets.py

echo ">>> [4/4] Pre-warming local Sentence-Transformers model cache (all-MiniLM-L6-v2)..."
python -c "
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
