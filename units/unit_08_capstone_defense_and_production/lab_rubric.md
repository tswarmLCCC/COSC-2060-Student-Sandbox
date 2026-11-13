# Unit 8 Lab Grading Rubric: Capstone Defense, Multi-Stage Docker, & Blind Batch Audit

> **Course**: COSC 2060 — Modern Data Engineering & AI Infrastructure  
> **Assessment**: Unit 8 Applied Engineering Lab (`lab8_starter.py`)  
> **Total Points**: 100 Points (Canvas SpeedGrader)

---

| Criteria | Points | Full Mastery (100%) | Minor Flaw (75%) | Unacceptable (0%) |
|---|---|---|---|---|
| **Challenge 1: Architecture & Config** | 25 pts | Ecosystem properly structures feature store, DLQ, alert dispatch, and fleet grounding state. | State variables declared globally instead of encapsulated in class. | Incomplete system structure. |
| **Challenge 2: Blind Batch Ingestion** | 25 pts | Quarantines poison pills into DLQ without crash; flags fuel fraud; aggregates valid transactions. | Ingestion crashes on negative values or ignores fraud alert. | Fails to parse transactions. |
| **Challenge 3: Multimodal Diagnostics** | 25 pts | Correctly joins vision defects and RAG notes; grounds TRUCK-219 with 2 verified citations. | Grounds truck but misses one of the two modalities. | Gives false clearance to unsafe vehicle. |
| **Challenge 4: Live Defense Verification** | 25 pts | 100% assertions pass across all 4 phases of blind test batch; outputs clear executive audit trail. | Passes with warnings or manual intervention required. | Script crashes during verification suite. |
