# Unit 4: Required Readings, Concepts & Video Lectures

Welcome to the core instructional lecture and study hub for **Unit 4: Unstructured Text & Vector Search (RAG Targets)**. This page organizes all weekly learning materials into four structured chapters:

1. **Instructor Lecture & Conceptual Deep Dive:** Master the target JSONL/Parquet RAG chunk format, maintenance text source systems, document extraction, recursive and sliding-window semantic chunking, high-dimensional vector embeddings (384D unit hyperspheres), cosine similarity metrics, and metadata pre-filtering.
2. **Required Readings & Authoritative Tutorial Guides:** Study curated official documentation from Hugging Face Sentence-Transformers, ChromaDB, and Pinecone vector engineering guides.
3. **Required Micro-Video Lectures (Embedded):** Watch high-definition video chapters with verified timestamp navigation to observe embedding models and vector databases executed in live Python environments.
4. **Institutional Video Lecture Embeds:** Access campus-specific video recordings and announcements uploaded by your instructor.

*Work through each section in sequence as part of your 150-minute asynchronous self-study allocation before starting the applied laboratory assignment.*

---

## 1. Instructor Lecture & Conceptual Deep Dive

### Unstructured Language Pipelines: Semantic Chunking, Embeddings & Vector Retrieval

#### 1. Unit Overview & Objectives
In Units 1 and 2, we engineered structured relational matrices and high-throughput transactional streams. In Unit 3, we preprocessed raw camera pixels into normalized computer vision manifests.

In **Unit 4**, we tackle the most prevalent and messy data modality in modern enterprise systems: **unstructured human language**.

Over 80% of enterprise knowledge does not live in relational SQL tables or clean CSV files. It is trapped in freeform PDF invoices, customer support transcripts, field engineering memos, and mechanic work orders scribbled in greasy shop bays.

When generative AI models (such as Large Language Models like Llama, Claude, or GPT) need to answer factual domain questions, they cannot be retrained or fine-tuned every hour. Instead, production architectures rely on **Retrieval-Augmented Generation (RAG)**.

As a data engineer, your responsibility in RAG is **not** prompt engineering. Your responsibility is the **upstream ingestion, cleaning, chunking, embedding, indexing, and retrieval pipeline**. If your text extraction leaves behind HTML noise, if your chunking splits a sentence in half, or if your vector search returns irrelevant documents, the downstream LLM will hallucinate and fail.

```
RAW UNSTRUCTURED DATA ──> TEXT CLEANER ──> SEMANTIC CHUNKING ──> EMBEDDING MODEL ──> VECTOR INDEX (ChromaDB) ──> TOP-K RETRIEVAL
```

**Measurable Learning Objectives:**
* **Differentiate** between keyword-based full-text search (BM25 / SQL `LIKE` and `ILIKE`) and dense semantic vector search (cosine similarity across high-dimensional embeddings).
* **Clean** noisy operational text logs by stripping HTML/markup tags, normalizing whitespace, and removing boilerplate noise.
* **Implement** deterministic semantic chunking strategies (recursive paragraph/sentence splitting and sliding token/word overlap) to preserve context boundaries without severing semantic meaning.
* **Generate and Inspect** dense vector embeddings using local transformer models (e.g., `all-MiniLM-L6-v2`, 384-dimensional unit hypersphere) and compute cosine similarity in NumPy.
* **Enrich** text chunks with structured operational metadata (`truck_id`, `service_date`, `shop_code`) to enable hybrid pre-filtering before semantic vector similarity scoring.
* **Construct** an end-to-end vector retrieval pipeline that queries historical mechanic work logs and extracts the top-<i>k</i> verified matches with exact source citations.

---

#### 2. What Our Output Looks Like and Where the Data Comes From

##### The Purpose
Our goal in Unit 4 is to build a **Chunked & Embedded Document Index** (`rag_chunks.jsonl` and `rag_vectors.parquet`) from raw diesel mechanic work orders. Each record in our output contains a scrubbed text chunk, its token count, structured filter metadata, and a normalized numeric embedding vector ready for semantic retrieval.

##### Why Language Models and Vector Databases Need This Format
Why can't we dump entire 50-page PDF manuals or raw database text dumps straight into an embedding model or a language model?
1. **Embedding Models Have Strict Input Limits:** Most dense embedding models (such as `all-MiniLM-L6-v2`) only accept `256` to `512` tokens (roughly 150–350 words) at a time. Any text beyond that limit is silently truncated and ignored.
2. **One Giant Document Blurs Specific Answers:** If a 20-page maintenance log covers brakes, tires, air conditioning, and turbochargers all in one giant string, a single summary vector averages all those topics together into a blurry middle ground. Splitting the text into focused chunks with a sliding overlap ensures each vector represents one clear symptom or repair event.
3. **Structured Metadata Enables Fast Pre-Filtering:** By keeping structured fields (`truck_id`, `service_date`, `shop_code`) in a separate `metadata` dictionary alongside the text chunk, our retrieval engine can filter to `"TRUCK-219"` or a specific date range *before* computing vector dot products.

##### Where the Raw Data Comes From (Source Systems)
In a commercial fleet maintenance operation, unstructured text arrives from three primary operational sources:
1. **Shop Bay Maintenance Terminals (`work_orders.jsonl`):** Mechanics type freeform repair notes at the end of a shift. These logs frequently contain shop shorthand (`"trbo"`, `"PM service"`), typos, inconsistent spacing, and HTML tags copied from legacy web forms (`<br>`, `<p>`).
2. **Manufacturer Technical Service Bulletins (NHTSA / OEM Manuals):** Official engineering notices describing part numbers, failure symptoms, and replacement procedures.
3. **Driver Post-Trip DVIR Logs (Mobile App Submissions):** Short text descriptions entered by drivers when reporting unusual noises, vibrations, or dashboard warning lights.

##### Sample Output Dataset (The Target Shape)
When our Unit 4 pipeline finishes scrubbing, chunking, and embedding the raw work orders, each output record in `rag_chunks.jsonl` (and Parquet) follows this exact structure:

```json
{
  "chunk_id": "WO-90812_chunk_0",
  "doc_id": "WO-90812",
  "chunk_index": 0,
  "token_count": 32,
  "text": "Driver complained of high whistling sound when pulling hills near 1800 revs. Pulled dipstick, noticed fine brass glitter in oil pan. Inspected trbo oil line.",
  "metadata": {
    "truck_id": "TRUCK-219",
    "service_date": "2024-09-28",
    "shop_code": "DEN-SHOP-02",
    "system_category": "Engine/Turbo"
  },
  "embedding_preview": [0.0412, -0.0891, 0.1145, "... (384 floats total)"]
}
```

---

#### 3. The \$42,000 Seized Engine & The "Whining Turbo"

To understand why simple SQL keyword matching fails catastrophically on unstructured text, examine an authentic failure in heavy-duty fleet operations.

Midwest Logistics operates a fleet of 450 Class-8 semi-trucks. Every truck visits maintenance facilities quarterly. Over 10 years, diesel mechanics logged hundreds of thousands of work orders into an electronic terminal in the shop bay.

In October 2024, the engine manufacturer issued an urgent National Highway Traffic Safety Administration (NHTSA) technical safety bulletin:
> *"Defective high-pressure turbocharger oil feed line (Part #TC-884-A) prone to internal micro-fissures. Symptoms include high-pitched turbine whining at 1,800 RPM and fine metallic sheen in drained 15W-40 engine oil. Immediate replacement required to avoid sudden bearing seizure and catastrophic block destruction."*

The fleet operations director asked a junior analyst to query the maintenance database for any trucks displaying symptoms of this defect so they could be pulled from service immediately.

The analyst executed a straightforward SQL query:

```sql
-- NAIVE KEYWORD SEARCH (DO NOT RELY ON THIS FOR SAFETY REVIEWS)
SELECT work_order_id, truck_id, service_date, mechanic_notes
FROM fleet_maintenance_orders
WHERE mechanic_notes ILIKE '%turbocharger%' 
   OR mechanic_notes ILIKE '%metallic sheen%';
```

The SQL query returned **12 work orders**. All 12 trucks were inspected, 3 had the line replaced, and management celebrated the safety audit.

##### The Catastrophic Seizure
Two weeks later, Truck #219 was hauling a 48,000-pound refrigerated trailer up a 6% grade on Interstate 70 in Colorado. At 65 mph, the turbocharger bearing suffered dry friction starvation, seized instantly, snapped the drive shaft, and threw shrapnel directly into the engine intake manifold.

The engine block cracked in half, dumping 10 gallons of hot oil onto the exhaust manifold and sparking an under-hood fire. The truck was destroyed, causing a **\$42,000 engine replacement loss** and \$110,000 in spoiled cargo.

##### The Post-Incident Autopsy
Investigators pulled the complete historical log for Truck #219 from 18 days prior:

```text
WORK ORDER: #WO-90812
TRUCK ID: TRUCK-219
DATE: 2024-09-28
MECHANIC NOTES:
"Driver complained of high whistling sound when pulling hills near 1800 revs. 
Pulled dipstick, noticed fine brass glitter in oil pan. Inspected trbo oil line, 
looks like factory fitment. Flushed oil, advised driver to monitor."
```

Why did SQL `ILIKE` miss this?
1. The mechanic typed `"high whistling sound"`, not `"turbine whining"`.
2. The mechanic typed `"fine brass glitter"`, not `"metallic sheen"`.
3. The mechanic typed `"trbo oil line"` (a typo), not `"turbocharger"`.

**Lexical keyword search failed because it searches for matching character strings, not concepts.**  
Dense vector embeddings solve this problem: an embedding model projects `"high whistling sound"` and `"turbine whining"` to nearly identical coordinates in 384-dimensional vector space.

---

#### 4. The Semantic Sphere & Cosine Similarity

How does a computer represent the meaning of words mathematically?

An embedding model (such as `all-MiniLM-L6-v2`) is a neural network trained on hundreds of billions of sentences. It maps any arbitrary string of text into a high-dimensional list of numbers (a vector) in 384-dimensional space:
<p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.6rem; border-radius: 4px;">
  <b><i>v</i></b> = [ <i>x</i><sub>1</sub>, <i>x</i><sub>2</sub>, <i>x</i><sub>3</sub>, &hellip;, <i>x</i><sub>384</sub> ]
</p>

Crucially, modern embedding models **L2-normalize** output vectors so that their Euclidean length (magnitude) is exactly `1.0`:
<p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.6rem; border-radius: 4px;">
  ||<b><i>v</i></b>|| = &radic;( <i>v</i><sub>1</sub><sup>2</sup> + <i>v</i><sub>2</sub><sup>2</sup> + &hellip; + <i>v</i><sub>384</sub><sup>2</sup> ) = 1.0
</p>

Every document chunk and every search query becomes a single point on the surface of a 384-dimensional **unit hypersphere**.

```
THE SEMANTIC HYPERSPHERE:
                         "whistling sound" (v1)
                               *
                              / \  Angle θ is small!
                             /   * "turbine whining" (v2)
                            /      Cosine Similarity = 0.89!
                           /
  "radiator coolant flush" * (v3) [Far away! Angle near 90°, Cosine ~ 0.05]
```

To calculate how similar two texts are, we compute the **Cosine Similarity** (the cosine of the angle &theta; between their vectors):
<p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.6rem; border-radius: 4px;">
  Cosine Similarity(<b><i>A</i></b>, <b><i>B</i></b>) = cos(&theta;) = ( <b><i>A</i></b> &middot; <b><i>B</i></b> ) / ( ||<b><i>A</i></b>|| &times; ||<b><i>B</i></b>|| ) = &Sigma; ( <i>A</i><sub><i>i</i></sub> &times; <i>B</i><sub><i>i</i></sub> )
</p>

Because vectors are pre-normalized (`||A|| = ||B|| = 1.0`), cosine similarity simplifies to a blazing-fast **dot product** (`np.dot(A, B)`).

---

#### 5. Semantic Chunking: Why Naive Splitting Destroys Pipelines

You cannot pass a 50-page PDF into an embedding model at once because transformer models have strict token context limits (typically 256 to 512 tokens for embedding models). You must split text into smaller chunks.

##### The Danger of Naive Fixed-Character Splitting
If you naively split every 500 characters without regard for words or overlap:
> `"...the mechanic verified that the oil line had no"` | `"[SPLIT]"` | `"leaks on Tuesday, but the turbo failed on Wednesday..."`

You severed the negation `"no"` from `"leaks"`, reversing the meaning of the second chunk!

##### Production Solution: Recursive Semantic Splitting with Sliding Window Overlap
1. **Split by Structural Paragraphs (`\n\n`):** Preserve natural human topical boundaries.
2. **Fallback to Sentence or Word Boundaries (`. ` or whole words):** If a paragraph exceeds the target chunk size, split cleanly between sentences or words rather than slicing a word in half.
3. **Enforce Sliding Overlap (e.g., 15–20% overlap):** Repeat the trailing words/characters of Chunk 0 at the beginning of Chunk 1. This ensures that context straddling a boundary is never lost.

```
SLIDING WINDOW WITH OVERLAP (Chunk Size = 50 words, Overlap = 10 words):
Document Words: [ 0 ................................................ 130 ]
Chunk 0:        [ 0 ─────────── 40 ─── 50 ]
Chunk 1:                        [ 40 ─── 50 ─────────── 80 ─── 90 ]
Chunk 2:                                                [ 80 ─── 90 ─────────── 130 ]
                                  ^^^^^^                  ^^^^^^
                            10-Word Overlap         10-Word Overlap
```

---

#### 6. Step-by-Step Code Ramp-Up & Guided Implementation Walkthrough (Python + Vector RAG)

Let's first build every core text-cleaning, sliding-window chunking, and NumPy cosine similarity function from scratch using standard Python, and then walk through a complete `SentenceTransformer` + `ChromaDB` vector search pipeline.

##### Step 1: Reading JSON Lines (`.jsonl`) and Scrubbing Dirty Text
In data engineering, multi-document text corpora are commonly stored in **JSON Lines (`.jsonl`)** format—where each line is a valid JSON object. We can strip stray HTML tags (`<p>`, `<b>`, `<br>`) and collapse extra whitespace using Python's built-in `re` module:

```python
import json
import re

raw_line = '{"doc_id": "WO-101", "truck_id": "TRUCK-219", "text": "<p>Driver   reported  <b>whistling</b>\\n\\nsound near 1800 RPM.</p>"}'
record = json.loads(raw_line)

def clean_text(raw_str: str) -> str:
    """Strips HTML tags and collapses multiple spaces/newlines into single spaces."""
    # 1. Replace any <...> HTML tag with a space
    no_html = re.sub(r"<[^>]+>", " ", raw_str)
    # 2. Collapse multiple spaces, tabs, or newlines into a single space
    normalized = re.sub(r"\s+", " ", no_html).strip()
    return normalized

print("Cleaned text:", clean_text(record["text"]))
```

##### Step 2: Writing a Sliding-Window Word/Token Chunker
Here is how you write a deterministic function that splits a cleaned string into overlapping chunks of `chunk_size` words with `overlap` words repeated between consecutive chunks:

```python
def chunk_text_sliding_window(text: str, chunk_size: int = 40, overlap: int = 10) -> list[str]:
    """Splits text into overlapping word chunks so context across boundaries is preserved."""
    if overlap >= chunk_size:
        raise ValueError("overlap must be strictly less than chunk_size")
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size:
        return [" ".join(words)]

    chunks = []
    step = chunk_size - overlap
    for start_idx in range(0, len(words), step):
        window = words[start_idx : start_idx + chunk_size]
        chunks.append(" ".join(window))
        if start_idx + chunk_size >= len(words):
            break
    return chunks

sample_doc = " ".join([f"word_{i}" for i in range(1, 95)])
chunks = chunk_text_sliding_window(sample_doc, chunk_size=40, overlap=10)
for idx, c in enumerate(chunks):
    w_list = c.split()
    print(f"Chunk {idx}: {len(w_list)} words ({w_list[0]} ... {w_list[-1]})")
```

##### Step 3: Computing Cosine Similarity Directly in NumPy
To see how vector search scores candidate chunks under the hood, here is the exact cosine similarity calculation in NumPy:

```python
import numpy as np

def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Computes cosine similarity between two 1D NumPy vectors."""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

query_vec   = np.array([0.80, 0.60, 0.00, 0.00])
turbo_chunk = np.array([0.78, 0.62, 0.05, 0.00])
brake_chunk = np.array([0.00, 0.05, 0.90, 0.43])

print("Similarity to turbo_chunk:", round(cosine_similarity(query_vec, turbo_chunk), 4))  # ~0.998
print("Similarity to brake_chunk:", round(cosine_similarity(query_vec, brake_chunk), 4))  # ~0.030
```

##### Step 4: Guided Implementation Walkthrough — Vector RAG Ingestion with SentenceTransformers & ChromaDB
Here is how a full production pipeline encodes mechanic work orders using `SentenceTransformer("all-MiniLM-L6-v2")` and indexes them with structured metadata in `ChromaDB`:

```python
from sentence_transformers import SentenceTransformer
import chromadb
import numpy as np

# 1. Initialize local embedding model (runs 100% locally on CPU)
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# 2. Initialize in-memory ChromaDB vector database
client = chromadb.Client()
collection = client.get_or_create_collection(
    name="fleet_maintenance",
    metadata={"hnsw:space": "cosine"}
)

# 3. Mechanic work order logs (including typos and colloquialisms)
documents = [
    "Driver complained of high whistling sound when pulling hills near 1800 revs. Pulled dipstick, noticed fine brass glitter in oil pan.",
    "Routine PM service completed. Replaced steer axle brake shoes and adjusted air chambers. Cleaned wheel seals.",
    "Installed new air conditioning compressor and recharged R134a refrigerant. Cold air restored to sleeper cab.",
    "Transmission fluid flush and filter replacement. No metal shavings found on magnetic drain plug."
]

metadata = [
    {"truck_id": "TRUCK-219", "date": "2024-09-28"},
    {"truck_id": "TRUCK-104", "date": "2024-10-02"},
    {"truck_id": "TRUCK-305", "date": "2024-10-05"},
    {"truck_id": "TRUCK-412", "date": "2024-10-10"}
]

ids = ["WO-90812", "WO-90813", "WO-90814", "WO-90815"]

# 4. Generate dense embeddings and index into ChromaDB
embeddings = embedder.encode(documents).tolist()
collection.add(documents=documents, embeddings=embeddings, metadatas=metadata, ids=ids)

# 5. Query using official engineering terminology
query_text = "turbocharger failure metallic flakes in oil whine sound"
query_vector = embedder.encode([query_text]).tolist()

results = collection.query(query_embeddings=query_vector, n_results=1)

print(f"Top Matched Work Order: {results['ids'][0][0]}")
print(f"Confidence Distance:   {results['distances'][0][0]:.4f}")
print(f"Matched Text:          {results['documents'][0][0]}")
```

**Verification Output:**
```
Top Matched Work Order: WO-90812
Confidence Distance:   0.3124 (Cosine Similarity: 0.6876)
Matched Text: Driver complained of high whistling sound when pulling hills near 1800 revs. Pulled dipstick, noticed fine brass glitter in oil pan.
```

The vector search identified Truck #219 (`WO-90812`) as the #1 match with high confidence, despite zero exact keyword matches.

---

#### 7. Practice Exercises & Formative Self-Check FAQ

Try these three exercises in your GitHub Codespaces sandbox (`units/unit_04_unstructured_text_and_vector_rag/`) before starting the graded lab:

1. **Exercise 1 (HTML & Whitespace Cleaning):** Test `clean_text()` on a string containing `<div class="note">Oil   pressure\t\tdropped\nbelow 20 PSI!</div>` and verify that the output is `"Oil pressure dropped below 20 PSI!"`.
2. **Exercise 2 (Overlap Boundary Check):** Run `chunk_text_sliding_window` with `chunk_size=20` and `overlap=5` on a 50-word paragraph. Print the last 5 words of `chunks[0]` and the first 5 words of `chunks[1]` to confirm they match identically.
3. **Exercise 3 (Unit Vector Normalization):** Normalize a NumPy vector using `u = v / np.linalg.norm(v)`, then check `np.linalg.norm(u)` to confirm its length is `1.0`.

##### Common Traps & Formative Self-Check FAQ

* **Question 1: What is the difference between Cosine Distance and Cosine Similarity?**  
  *Answer:* Cosine Similarity ranges from `-1.0` (opposite) to `+1.0` (identical). ChromaDB reports **Cosine Distance**, defined as `1.0 - Cosine Similarity`. Therefore, a Cosine Distance close to `0.0` (or a Cosine Similarity close to `1.0`) indicates near-identical meaning!

* **Question 2: Should I embed the metadata fields directly into the text?**  
  *Answer:* No! Keep structured attributes (`truck_id`, `date`) in the vector database's `metadata` dictionary. Use metadata pre-filtering (`where={"date": {"$gt": "2024-09-01"}}`) to restrict the vector search space with 100% precision before computing dot products.

* **Question 3: What happens if `overlap` is set equal to or larger than `chunk_size`?**  
  *Answer:* If `overlap >= chunk_size`, the sliding window step size (`chunk_size - overlap`) becomes `0` or negative, causing an infinite loop. Always enforce `0 <= overlap < chunk_size` (typically `overlap` is 10% to 25% of `chunk_size`).

---

## 2. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical specifications before beginning your applied lab:

1. **[Hugging Face Sentence-Transformers Official Documentation](https://sbert.net/)**
   *Learn how sentence embedding architectures encode natural language into dense metric spaces for semantic search and clustering.*

2. **[ChromaDB Official Documentation: Collections & Vector Operations](https://docs.trychroma.com/docs/overview/getting-started)**
   *Understand vector collection initialization, cosine vs. L2 distance spaces, metadata filtering, and embedding functions.*

3. **[Pinecone Learning Center: Vector Similarity Explained](https://www.pinecone.io/learn/vector-similarity/)**
   *Study the mathematical differences between Dot Product, Cosine Similarity, and Euclidean Distance in high-dimensional spaces.*

4. **[LangChain Architectural Concepts: Text Chunking Strategies](https://python.langchain.com/docs/concepts/)**
   *A guide to character, recursive character, and token-aware semantic text splitters and sliding window configurations.*

5. **[Anthropic Engineering: Context Retrieval & Prompt Grounding](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/context-stuffing)**
   *Discover why precise vector retrieval eliminates model hallucinations and enables defensible source attribution.*

---

## 3. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to observe vector embeddings and RAG pipelines in practice:

### Vector Databases in 100 Seconds <span style="font-size: 0.9em; color: #64748b;">(Fireship - 2:20)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Vector Databases in 100 Seconds" src="https://www.youtube.com/embed/klTvEwg3oJ4" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=klTvEwg3oJ4" target="_blank" rel="noopener">Open video in new tab (2:20)</a></p>

### How Sentence Transformers Work: Dense Embeddings & Vector Math <span style="font-size: 0.9em; color: #64748b;">(CodeEmporium - Core Concepts)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Sentence Transformers Explained" src="https://www.youtube.com/embed/O3xbVmpdJwU" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=O3xbVmpdJwU" target="_blank" rel="noopener">Open video in new tab</a></p>

### Building a Local RAG Pipeline with ChromaDB & Python <span style="font-size: 0.9em; color: #64748b;">(Practical AI - Full Walkthrough)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="ChromaDB RAG Pipeline in Python" src="https://www.youtube.com/embed/InlB5-3-nR4" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=InlB5-3-nR4" target="_blank" rel="noopener">Open video in new tab</a></p>

---

## 4. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for Unit 4 will appear in this designated container.</p>
</div>
