# Unit 4: Required Readings, Concepts & Video Lectures

Welcome to the instructional reading and study guide for **Unit 4: Unstructured Text & Vector Search (RAG)**. This page organizes the week's learning materials into four sections:

1. **Instructor Lecture & Conceptual Deep Dive:** Learn how unstructured text is cleaned, split into overlapping chunks, paired with structured metadata, and converted into dense vector embeddings for Retrieval-Augmented Generation (RAG).
2. **Required Readings & Tutorial Guides:** Explore official documentation from Hugging Face Sentence-Transformers, ChromaDB, Pinecone, and LangChain.
3. **Required Micro-Video Lectures (Embedded):** Watch focused video tutorials covering vector databases, sentence embeddings, and local RAG pipelines.
4. **Institutional Video Lecture Embeds:** Access instructor announcements and lab walkthrough recordings.

*Work through each section in sequence as part of your 150-minute self-study block before starting the applied lab.*

---

## 1. Instructor Lecture & Conceptual Deep Dive

### Turning Freeform Text Logs into Searchable Vector Chunks

In Units 1 and 2, we worked with structured numbers in tables. In Unit 3, we worked with camera photos stored as 3D pixel arrays. In **Unit 4**, we tackle the most common type of unstructured data in any organization: **written human language**.

Much of a company's day-to-day operational knowledge is written in freeform text rather than neat database columns: mechanic repair notes typed on shop floor terminals, customer support tickets, safety inspection reports, and equipment manuals.

When an AI assistant (powered by a Large Language Model like Claude, Llama, or GPT) needs to answer questions about your company's equipment or maintenance history, you cannot retrain the model every afternoon. Instead, engineers use **Retrieval-Augmented Generation (RAG)**:
1. Ahead of time, a data pipeline cleans the company's documents, splits them into bite-sized **chunks**, converts each chunk's meaning into a numeric list called a **vector embedding**, and stores those vectors alongside structured metadata.
2. When a user asks a question, the system searches the vector index for the most relevant chunks and hands those exact paragraphs to the language model so it can answer accurately with source citations.

As a data engineer, your job is building that **text cleaning, chunking, metadata tagging, and vector retrieval pipeline**.

#### Measurable Learning Objectives
* **Compare** exact keyword search (`SQL LIKE` / `ILIKE`) with semantic vector search (cosine similarity across embedding vectors).
* **Clean** noisy operational text logs by stripping HTML/markup tags, normalizing whitespace, and removing boilerplate noise.
* **Implement** sliding-window text chunking with configurable chunk size and overlap so sentences and ideas are not cut off mid-thought.
* **Attach** structured metadata (`doc_id`, `vehicle_id`, `service_date`, `chunk_index`) to every text chunk in JSON Lines (`.jsonl`) and Parquet formats.
* **Compute** cosine similarity between normalized embedding vectors to retrieve the top-<i>k</i> most relevant maintenance logs for a diagnostic query.

---

### What Our Output Looks Like and Where the Data Comes From

#### The Purpose
Our goal in Unit 4 is to build a **Chunked & Embedded Document Index** (`rag_chunks.jsonl` and `rag_vectors.parquet`) from raw diesel mechanic work orders. Each record in our output contains a clean text chunk, its token count, structured filter metadata, and a numeric embedding vector ready for semantic search.

#### Why Language Models and Vector Databases Need This Format
Why can't we just dump entire 50-page PDF manuals or raw database text dumps straight into an embedding model or a language model?
1. **Embedding Models Have Strict Input Limits:** Most embedding models (such as `all-MiniLM-L6-v2`) only accept `256` to `512` tokens (roughly 150–350 words) at a time. Any text past that limit is silently cut off and ignored.
2. **One Giant Document Blurs Specific Answers:** If a 20-page maintenance log covers brakes, tires, air conditioning, and turbochargers all in one giant string, a single summary vector averages all those topics together into a blurry middle ground. Splitting the text into focused 200-token chunks with a 40-token overlap ensures each vector represents one clear topic.
3. **Structured Metadata Enables Fast Pre-Filtering:** By keeping structured fields (`truck_id`, `service_date`, `shop_code`) in a separate `metadata` dictionary alongside the text chunk, our search engine can instantly filter to `"TRUCK-219"` *before* comparing vectors.

#### Where the Raw Data Comes From (Source Systems)
In a fleet maintenance operation, unstructured text arrives from three sources:
1. **Shop Bay Maintenance Terminals (`work_orders.jsonl`):** Mechanics type freeform repair notes at the end of a shift. These logs often contain shop shorthand (`"trbo"`, `"PM service"`), inconsistent spacing, and HTML tags copied from legacy web forms (`<br>`, `<p>`).
2. **Manufacturer Technical Service Bulletins (PDF / Markdown Manuals):** Official engineering notices describing part numbers, symptoms, and repair procedures.
3. **Driver Post-Trip DVIR Logs (Mobile App Submissions):** Short text descriptions entered by drivers when reporting unusual noises, vibrations, or dashboard warning lights.

#### Sample Output Dataset (The Target Shape)
When our Unit 4 pipeline finishes cleaning, chunking, and embedding the raw work orders, each output record in `rag_chunks.jsonl` (or Parquet) follows this structure:

```json
{
  "chunk_id": "WO-90812_chunk_0",
  "doc_id": "WO-90812",
  "chunk_index": 0,
  "token_count": 32,
  "text": "Driver complained of high whistling sound when pulling hills near 1800 revs. Pulled dipstick, noticed fine brass glitter in oil pan. Inspected trbo oil line.",
  "metadata": {
    "truck_id": "TRUCK-219",
    "service_date": "2026-09-28",
    "shop_code": "DEN-SHOP-02",
    "system_category": "Engine/Turbo"
  },
  "embedding_preview": [0.0412, -0.0891, 0.1145, "... (384 floats total)"]
}
```

---

### Why Keyword Search Alone Misses Critical Maintenance Records

To see why companies pair SQL databases with vector search, let's look at a real scenario from heavy-duty truck maintenance.

A fleet operator managed 450 semi-trucks. Every time a truck visited a repair shop, the mechanic typed notes into the `fleet_maintenance_orders` table. One afternoon, the engine manufacturer sent out an urgent safety bulletin:

> **Safety Bulletin:** *"High-pressure turbocharger oil feed lines (Part #TC-884) may develop small cracks. Early warning signs include a **high-pitched turbine whining noise** at 1,800 RPM and a **metallic sheen** in the engine oil. Replace immediately to prevent engine bearing failure."*

An analyst ran a SQL keyword query to find any trucks showing those warning signs:

```sql
SELECT work_order_id, truck_id, service_date, mechanic_notes
FROM fleet_maintenance_orders
WHERE mechanic_notes ILIKE '%turbocharger%'
   OR mechanic_notes ILIKE '%turbine whining%'
   OR mechanic_notes ILIKE '%metallic sheen%';
```

That query returned 12 records. However, it completely missed **Work Order #WO-90812** for Truck #219, which had been entered two weeks earlier:

```text
WORK ORDER: #WO-90812 | TRUCK: TRUCK-219 | DATE: 2026-09-28
MECHANIC NOTES:
"Driver complained of high whistling sound when pulling hills near 1800 revs.
Pulled dipstick, noticed fine brass glitter in oil pan. Inspected trbo oil line,
flushed oil, advised driver to monitor."
```

Look at why `ILIKE` missed Truck #219:
* The mechanic wrote `"high whistling sound"` instead of `"turbine whining"`.
* The mechanic wrote `"fine brass glitter"` instead of `"metallic sheen"`.
* The mechanic abbreviated `"trbo oil line"` instead of spelling out `"turbocharger"`.

SQL `ILIKE` only checks whether exact sequences of letters match. It has no idea that *"brass glitter in oil pan"* and *"metallic sheen in engine oil"* describe the exact same physical symptom.

---

### How Vector Embeddings and Cosine Similarity Work

How do we teach a computer to match **meaning** rather than exact spelling?

We use an **embedding model** (such as `all-MiniLM-L6-v2`). An embedding model is a compact neural network that reads a sentence or paragraph and outputs a fixed-length list of numbers—for example, a vector of **384 floating-point numbers**:

```text
"high whistling sound near 1800 revs"  -->  [ 0.041, -0.089,  0.114, ..., 0.022 ] (384 numbers)
"high-pitched turbine whining at RPM"  -->  [ 0.039, -0.085,  0.118, ..., 0.019 ] (384 numbers)
"replaced cab air conditioning filter" -->  [-0.112,  0.074, -0.063, ..., 0.091 ] (384 numbers)
```

Each number in that list captures a subtle aspect of the text's topic and context. Texts with similar meanings produce lists of numbers that point in nearly the same direction.

```
VISUALIZING VECTORS ON A CIRCLE (UNIT SPHERE):
                    "high whistling sound" (Vector A)
                          *
                         / \   Small angle between A and B!
                        /   *  "turbine whining noise" (Vector B)
                       /       Cosine Similarity = 0.89 (Strong Match)
                      /
  "replaced A/C filter" * (Vector C)
  (Points in a totally different direction -> Cosine Similarity = 0.05)
```

#### Computing Cosine Similarity
To measure how closely two vectors `A` and `B` point in the same direction, we compute their **Cosine Similarity**:
1. Multiply matching positions together and add them up (the **dot product**: `A[0]*B[0] + A[1]*B[1] + ...`).
2. Divide by the lengths (magnitudes) of both vectors:
   <p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.6rem; border-radius: 4px;">
     Cosine Similarity(<i>A</i>, <i>B</i>) = ( <i>A</i> &middot; <i>B</i> ) / ( ||<i>A</i>|| &times; ||<i>B</i>|| )
   </p>
* A Cosine Similarity of **`1.0`** means the two vectors point in the exact same direction (identical meaning).
* A Cosine Similarity near **`0.0`** means the topics are unrelated.
* When vectors are pre-normalized so their length `||A||` and `||B||` equals `1.0`, Cosine Similarity is simply the dot product `np.dot(A, B)`!

---

### How Sliding-Window Text Chunking Preserves Context

Before we generate embeddings for a long maintenance report or manual, we have to split the document into chunks.

What happens if we slice a document every 200 characters without looking at words or overlap?
```text
Chunk 1: "...mechanic inspected the high-pressure turbocharger oil line and found NO"
Chunk 2: "leaks on Monday, but noted severe vibration from the rear axle bearing..."
```
Notice how cutting right between `"NO"` and `"leaks"` reversed the meaning of Chunk 2 (`"leaks on Monday"` instead of `"NO leaks on Monday"`)!

To prevent this, data engineers use **Sliding-Window Chunking with Overlap**:
1. **Split on whole words/tokens or sentence boundaries** rather than cutting words in half.
2. **Include a sliding overlap** (for example, chunk size = `50` words, overlap = `10` words). The last 10 words of Chunk 0 are repeated at the start of Chunk 1:
   * **Chunk 0:** Words `0` to `50`
   * **Chunk 1:** Words `40` to `90` (starts `50 - 10 = 40` words in, preserving the 10-word bridge!)
   * **Chunk 2:** Words `80` to `130`

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

### Step-by-Step Code Ramp-Up: Text Cleaning, Chunking, and Vector Search

Let's build every part of a Python text and vector pipeline from scratch using standard Python and NumPy.

#### Step 1: Reading JSON Lines (`.jsonl`) and Scrubbing Dirty Text
In data engineering, multi-document text datasets are almost always stored in **JSON Lines (`.jsonl`)** format—where every line of the file is one self-contained JSON dictionary. We can clean HTML tags and messy extra spaces using Python's built-in `re` (regular expressions) module:

```python
import json
import re

raw_line = '{"doc_id": "WO-101", "truck_id": "TRUCK-219", "text": "<p>Driver   reported  <b>whistling</b>\\n\\nsound near 1800 RPM.</p>"}'
record = json.loads(raw_line)

def clean_text(raw_str: str) -> str:
    """Strips HTML tags and collapses multiple spaces/newlines into single spaces."""
    # 1. Remove any <...> HTML tags
    no_html = re.sub(r"<[^>]+>", " ", raw_str)
    # 2. Collapse multiple spaces, tabs, or newlines into a single space
    normalized = re.sub(r"\s+", " ", no_html).strip()
    return normalized

print("Cleaned text:", clean_text(record["text"]))
```

#### Step 2: Writing a Sliding-Window Word/Token Chunker
Here is how you write a clean, predictable function that splits a cleaned string into overlapping chunks of `chunk_size` words with `overlap` words repeated between neighbors:

```python
def chunk_text_sliding_window(text: str, chunk_size: int = 40, overlap: int = 10) -> list[str]:
    """Splits text into overlapping word chunks so context across boundaries is preserved."""
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size:
        return [" ".join(words)]

    chunks = []
    step = max(1, chunk_size - overlap)
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

Look at the output of that loop:
* `Chunk 0`: `40 words (word_1 ... word_40)`
* `Chunk 1`: `40 words (word_31 ... word_70)` — starts at `word_31`, repeating `word_31` through `word_40`!
* `Chunk 2`: `24 words (word_61 ... word_94)` — starts at `word_61`, repeating `word_61` through `word_70`!

#### Step 3: Computing Cosine Similarity and Metadata Filtering with NumPy
Once each chunk has an embedding vector, how does vector search score and rank them? Let's write the exact cosine similarity math in NumPy:

```python
import numpy as np

def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Computes cosine similarity between two 1D NumPy vectors."""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

# Example 4-dimensional vectors
query_vec   = np.array([0.80, 0.60, 0.00, 0.00])
turbo_chunk = np.array([0.78, 0.62, 0.05, 0.00])
brake_chunk = np.array([0.00, 0.05, 0.90, 0.43])

print("Similarity to turbo_chunk:", round(cosine_similarity(query_vec, turbo_chunk), 4))  # ~0.998
print("Similarity to brake_chunk:", round(cosine_similarity(query_vec, brake_chunk), 4))  # ~0.030
```

When we combine **metadata pre-filtering** with **cosine similarity ranking**, our retrieval function looks like this:
1. First, filter the list of chunks using exact metadata rules (for example, `chunk["metadata"]["system_category"] == "Engine/Turbo"`).
2. Second, compute `cosine_similarity(query_vec, chunk_vec)` for each remaining chunk.
3. Third, sort by similarity score from highest to lowest (`reverse=True`) and return the top <i>k</i> chunks!

---

### Practice Exercises and Common Questions

Try these three exercises in your GitHub Codespaces sandbox (`units/unit_04_unstructured_text_and_vector_rag/`) before starting the graded lab:

1. **Exercise 1 (HTML & Whitespace Cleaning):** Test `clean_text()` on a string containing `<div class="note">Oil   pressure\t\tdropped\nbelow 20 PSI!</div>` and verify that the output is `"Oil pressure dropped below 20 PSI!"`.
2. **Exercise 2 (Overlap Boundary Check):** Run `chunk_text_sliding_window` with `chunk_size=20` and `overlap=5` on a 50-word paragraph. Print the last 5 words of `chunks[0]` and the first 5 words of `chunks[1]` to confirm they match identically.
3. **Exercise 3 (Unit Vector Normalization):** Normalize a NumPy vector using `u = v / np.linalg.norm(v)`, then check `np.linalg.norm(u)` to confirm its length is `1.0`.

#### Common Questions & Troubleshooting

* **Question 1: What happens if `overlap` is set equal to or larger than `chunk_size`?**  
  *Answer:* If `overlap >= chunk_size`, the step size `chunk_size - overlap` becomes `0` or negative, which would cause an infinite loop! Always validate that `0 <= overlap < chunk_size` (typically `overlap` is 10% to 25% of `chunk_size`).

* **Question 2: What is the difference between Cosine Similarity and Cosine Distance?**  
  *Answer:* **Cosine Similarity** measures closeness (`1.0` = identical, `0.0` = unrelated). Some vector databases (like ChromaDB) report **Cosine Distance**, which is simply `1.0 - Cosine Similarity` (`0.0` = identical, `1.0` = unrelated). Always check whether your tool returns similarity (higher is better) or distance (lower is better).

* **Question 3: Why shouldn't I just glue the metadata (`truck_id`, `service_date`) into the text string instead of storing a separate `metadata` dictionary?**  
  *Answer:* Embedding vectors are great at fuzzy conceptual meaning, but terrible at exact date comparisons (like `service_date >= '2026-09-01'`). Keeping structured fields in a `metadata` dictionary lets you filter dates and IDs with 100% precision before running vector similarity.

---

## 2. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical references before beginning your applied lab:

1. **[Hugging Face Sentence-Transformers Official Documentation](https://sbert.net/)**
   *Learn how sentence embedding models encode text into dense vectors for semantic search and clustering.*

2. **[ChromaDB Official Documentation: Getting Started & Vector Collections](https://docs.trychroma.com/docs/overview/getting-started)**
   *Understand vector collection creation, cosine vs. L2 distance metrics, metadata filtering, and querying.*

3. **[Pinecone Learning Center: Vector Similarity Explained](https://www.pinecone.io/learn/vector-similarity/)**
   *Study the practical differences between Dot Product, Cosine Similarity, and Euclidean Distance.*

4. **[LangChain Conceptual Guide: Text Splitters & Chunking](https://python.langchain.com/docs/concepts/)**
   *Review character, recursive character, and token-based text chunking strategies.*

5. **[Anthropic Engineering: Context Retrieval & Grounding](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/context-stuffing)**
   *See how retrieving focused text chunks with source IDs grounds language model responses.*

---

## 3. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to see vector embeddings and RAG pipelines in practice:

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
