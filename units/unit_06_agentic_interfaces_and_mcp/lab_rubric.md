# Unit 6 Lab Grading Rubric: The Agentic Interface & Model Context Protocol (MCP)

> **Course**: COSC 2060 — Modern Data Engineering & AI Infrastructure  
> **Assessment**: Unit 6 Applied Engineering Lab (`lab6_starter.py`)  
> **Total Points**: 100 Points (Canvas SpeedGrader)

---

| Criteria | Points | Full Mastery (100%) | Minor Flaw (75%) | Unacceptable (0%) |
|---|---|---|---|---|
| **Challenge 1: Tool Registry & Schema** | 25 pts | Server dynamically registers tools; introspects parameter schemas; exports JSON-RPC `tools/list` format. | Tools register but schemas are hardcoded or incomplete. | Registry fails or crashes on decoration. |
| **Challenge 2: Defensive Sandboxing** | 25 pts | Regex checks prevent malformed IDs, SQL commands, and prompt injection strings with explicit `ValueError`. | Checks for length only without regex boundary matching. | Accepts raw strings without validation. |
| **Challenge 3: Multimodal Diagnostic** | 25 pts | Unifies vision defects and maintenance RAG notes into an actionable clearance decision (`GROUNDED` vs `CLEARED`). | Checks vision only, missing RAG turbo recall note. | Incorrect logic produces false safety clearances. |
| **Challenge 4: JSON-RPC Simulation** | 25 pts | Dispatches requests using standard JSON-RPC 2.0 envelopes; handles errors cleanly with standard codes. | Dispatches function directly without JSON-RPC response formatting. | Execution errors unhandled or crashes script. |
