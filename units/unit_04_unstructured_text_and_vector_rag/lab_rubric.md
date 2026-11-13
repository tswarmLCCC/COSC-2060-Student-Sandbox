# Unit 4 Lab Grading Rubric: Unstructured Text, Semantic Chunking, & Vector RAG

> **Course**: COSC 2060 — Modern Data Engineering & AI Infrastructure  
> **Assessment**: Unit 4 Applied Engineering Lab (`lab4_starter.py`)  
> **Total Points**: 100 Points (Canvas SpeedGrader)

---

| Criteria | Points | Full Mastery (100%) | Minor Flaw (75%) | Unacceptable (0%) |
|---|---|---|---|---|
| **Challenge 1: Header Ingestion** | 25 pts | Correctly parses all 4 log blocks into structured dictionaries with VIN, work order, mileage, and notes. | Ignores one metadata field (e.g. mileage cast to int fails). | Fails to parse records; regex crashes or truncates text. |
| **Challenge 2: Semantic Chunking** | 25 pts | Correct sliding window word algorithm preserving overlap; tags each chunk with parent ID. | Chunks split words in half or overlap is negative. | Returns single monolithic chunk per document. |
| **Challenge 3: Dense Vector Embeddings** | 25 pts | Computes 384-d embeddings using `all-MiniLM-L6-v2`; enforces unit L2 normalization. | Embeddings not normalized, distorting cosine metric. | Uses random vectors or crash during model initialization. |
| **Challenge 4: Hybrid Retrieval Engine** | 25 pts | Successfully retrieves Truck #219 log with similarity score > 0.55; supports exact metadata filtering. | Retrieves correct record but metadata filter is broken. | Top hit is wrong truck or score < 0.30. |
