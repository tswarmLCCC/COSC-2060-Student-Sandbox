"""
====================================================================
COSC 2060: Modern Data Engineering & AI Infrastructure
Unit 4 Synchronous Coding Clinic ("I Do, We Do, You Do")
Topic: Unstructured Text, Semantic Chunking, & Vector RAG
====================================================================
Run this script from the terminal to execute the live class walkthrough
demonstrations:
    python units/unit_04_unstructured_text_and_vector_rag/coding_clinic.py
====================================================================
"""


# ====================================================================
# PART 0: BASICS WARM-UP — TEXT CLEANING & BASIC WORD SPLITTING
# ====================================================================
print("\n>>> Executing PART 0: BASICS WARM-UP (Text Scrubbing & Word Slicing)...")
import re
import numpy as np

dirty_note = "<p>Driver   reported  <b>whistling</b>\n\nsound near 1800 RPM.</p>"
clean_note = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", dirty_note)).strip()
words_preview = clean_note.split()
vec_a = np.array([0.8, 0.6])
vec_b = np.array([0.8, 0.6])
print(f"Part 0 Warm-Up — Cleaned note ({len(words_preview)} words): '{clean_note}'")
print(f"Part 0 Warm-Up — Dot product of identical unit vectors: {float(np.dot(vec_a, vec_b)):.2f}")


# ====================================================================
# PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION
# ====================================================================
print("\n>>> Executing PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION...")
def chunk_text_by_words(text: str, chunk_size: int = 50, overlap: int = 15) -> list[str]:
    """Splits a body of text into overlapping word chunks."""
    words = text.split()
    chunks = []
    
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += (chunk_size - overlap)
        
    return chunks

sample = "The high pressure turbocharger feed line was found to have micro cracks. " * 8
chunks = chunk_text_by_words(sample, chunk_size=20, overlap=5)
print(f"Generated {len(chunks)} overlapping chunks.")
print(f"Chunk 0: {chunks[0]}")
print(f"Chunk 1: {chunks[1]}")


# ====================================================================
# PART 2: 'WE DO' — GUIDED CLASS PRACTICE
# ====================================================================
print("\n>>> Executing PART 2: 'WE DO' — GUIDED CLASS PRACTICE...")
# Sample structured chunk dictionary:
records = [
    {"id": "c1", "truck_id": "TRUCK-101", "text": "Engine oil pressure normal during road test."},
    {"id": "c2", "truck_id": "TRUCK-219", "text": "Whining noise reported at 1800 rpm near turbo housing."},
    {"id": "c3", "truck_id": "TRUCK-304", "text": "Brake pad thickness measured at 4mm on steer axle."}
]

# Guided Exercise: Filter to only 'TRUCK-219' chunks before vector similarity:
target_truck = "TRUCK-219"
filtered_pool = [rec for rec in records if rec["truck_id"] == target_truck]
print(f"Filtered pool contains {len(filtered_pool)} records for truck {target_truck}.")

