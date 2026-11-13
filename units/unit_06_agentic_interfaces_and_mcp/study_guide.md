# Unit 6: Required Readings, Concepts & Video Lectures

Welcome to the core instructional lecture and study hub for **Unit 6: The Agentic Interface (Model Context Protocol - MCP)**. This page organizes all weekly learning materials into five structured sections:

1. **Unit Overview & Objectives:** Review the architectural context and measurable learning objectives for this unit.
2. **Instructor Lecture & Conceptual Deep Dive (Ribbon Slices 2a–2h):** Master the target MCP JSON-RPC 2.0 schemas, agentic source systems, bottom-up JSON Schema & parameter-guard engineering, how autonomous LLM agents discover and call tools, the "\$500,000 Unrestricted SQL" operational catastrophe, the "USB-C for AI" mental model, defensive tool sandboxing, and JSON-RPC 2.0 communication.
3. **Required Readings & Authoritative Tutorial Guides:** Study curated official documentation from Anthropic MCP, JSON-RPC 2.0 specifications, and local tool calling standards.
4. **Required Micro-Video Lectures (Embedded):** Watch high-definition video chapters with verified timestamp navigation to observe MCP tool discovery and autonomous agent execution in live environments.
5. **Institutional Video Lecture Embeds:** Access campus-specific video recordings and announcements uploaded by your instructor.

*Work through each section in sequence as part of your 150-minute asynchronous self-study allocation before starting the applied laboratory assignment.*

---



## 1. Unit Overview & Objectives
In Unit 5, we engineered a unified REST API layer serving multimodal data products (relational matrices, anomaly engines, computer vision manifests, and vector RAG indices).

In **Unit 6**, we connect this data infrastructure to the frontier of modern software engineering: **Autonomous AI Agents**.

An AI model by itself is simply a next-token predictor. It cannot check current warehouse inventory, it cannot query your database, and it cannot inspect live fleet telemetry. To make an AI model capable of taking action, we give it **tools** (function calling).

Historically, every company invented its own ad-hoc, proprietary framework to connect LLMs to databases. This led to dangerous security vulnerabilities, brittle integrations, and massive code duplication.

In 2024, the industry converged around an open standard: the **Model Context Protocol (MCP)**. Developed by Anthropic and adopted across the AI ecosystem, MCP is the **"USB-C standard for AI applications"**. It establishes an open, standardized, secure client-server protocol where AI models discover and invoke backend data tools through structured **JSON-RPC** messages (Remote Procedure Call formatted as JSON—a simple standard for calling a named function and passing arguments over text).

```
HUMAN OPERATOR ──> LLM AGENT ──(JSON-RPC Request)──> MCP SERVER ──> DAAS BACKEND (DuckDB / Polars / RAG)
                          <──(Structured Tool Result)───┘
```

**Measurable Learning Objectives:**
* **Explain** the architectural role of the Model Context Protocol (MCP) as a standardized, secure JSON-RPC 2.0 bridge between LLMs and enterprise data stores.
* **Design** descriptive, deterministic MCP Tool definitions (including function signatures, JSON Schema / Pydantic argument schemas, and semantic prompt descriptions).
* **Enforce** defensive security boundaries (the Principle of Least Privilege, read-only sandboxes, and parameter bounds) to prevent prompt injection and unauthorized SQL execution.
* **Implement** an MCP Server in Python exposing the logistics data engines developed in Units 1 through 5.
* **Simulate and Verify** an agentic tool-calling loop where an LLM dynamically discovers tools (`tools/list`), executes multi-step queries (`tools/call`), and generates a factual, hallucination-free executive fleet report.

---

## 2a. What Our Output Looks Like and Where the Data Comes From

### The Purpose
Our goal in Unit 6 is to build a **Sandboxed MCP Tool Server** that exposes our logistics data pipelines as structured, read-only tools over **JSON-RPC 2.0**. When an AI agent asks what tools are available (`tools/list`) or invokes a specific tool (`tools/call`), our server validates the parameters, queries the underlying dataset, and returns a structured JSON-RPC response.

### Why AI Agents Need Structured Tool Schemas and Guardrails
An AI agent does not read your Python source code to figure out how to query your database. Instead, when an agent connects to your MCP server, it relies on two standardized structures:
1. **The Tool Registry (`tools/list`):** A JSON catalog listing every tool's `name`, plain-English `description`, and `inputSchema` (the exact parameter names, types, bounds, and required fields).
2. **The Tool Execution Envelope (`tools/call`):** A predictable JSON-RPC 2.0 response returning either the requested records or a structured error message (`isError: true`) that allows the agent to self-correct without crashing the server.

### Where the Raw Data Comes From (Source Systems)
An MCP server connects two sides of our architecture:
1. **Inbound Agent Requests (MCP Host / LLM Client):** An AI assistant running in a dispatch console translates a human operator's question (*"Is Truck 219 safe to dispatch to Denver?"*) into one or more structured JSON-RPC `tools/call` messages.
2. **Backend Curated Data Stores (`feature_matrix.parquet`, `anomaly_features.parquet`, `rag_chunks.jsonl`):** The MCP server executes bounded, read-only lookups against our curated tables and returns compact JSON summaries (never dumping millions of raw rows into the model's context window).

### Sample Output Dataset (The Target MCP JSON-RPC Shape)
Every interaction with our MCP server follows the **JSON-RPC 2.0** specification:

**1. Tool Discovery Output (`method: "tools/list"`):**
```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "result": {
    "tools": [
      {
        "name": "get_truck_telemetry",
        "description": "Retrieve current operational status, speed, and fuel level for a commercial truck.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "truck_id": {
              "type": "integer",
              "description": "The unique truck number (1 to 10000)",
              "minimum": 1,
              "maximum": 10000
            }
          },
          "required": ["truck_id"]
        }
      }
    ]
  }
}
```

**2. Tool Execution Output (`method: "tools/call"`):**
```json
{
  "jsonrpc": "2.0",
  "id": "req-101",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"truck_id\": 219, \"status\": \"EN_ROUTE\", \"current_city\": \"Cheyenne, WY\", \"speed_mph\": 62.5, \"last_inspection\": \"PASS\"}"
      }
    ]
  }
}
```

> **Companion Reference:** To see how MCP JSON-RPC schemas compare with the REST contracts, RAG chunks, and tabular matrices from Units 1–5, open **The Shapes of AI Data: A Companion Guide** in the *Getting Started - Course Orientation* module.

---

## 2b. Building MCP Tool Definitions & Parameter Guards from the Ground Up

Before we examine agentic database disasters or the JSON-RPC 2.0 wire protocol, let's start at the beginning: **How do we turn a regular Python data function into a safe, self-describing tool that an AI model can discover and invoke?**

If you know how to write a Python function and a Python dictionary from Units 1–5, you already know 90% of what it takes to build a Model Context Protocol (MCP) server. Let's walk through the four foundational building blocks from the ground up.

### 1. Writing a Read-Only, Single-Purpose Python Function
In Unit 5, you wrote FastAPI endpoints for human web dashboards. In Unit 6, your functions are called by **autonomous AI models**. Instead of writing one giant function that accepts arbitrary SQL strings, we write small, single-purpose, **read-only** functions with explicit parameters—such as `get_truck_telemetry(truck_id: int)` or `get_recent_anomalies(limit: int = 5)`.

### 2. Defending Every Argument at the Door (Type & Range Checks)
Never assume an AI model will pass clean inputs! An LLM might accidentally pass `"219; DROP TABLE routes;"`, `-5`, `9999999`, or even a boolean `True` (and in Python, `isinstance(True, int)` evaluates to `True`!). Every MCP tool starts with a strict parameter guard:

```python
def validate_truck_id(truck_id: int) -> int:
    if not isinstance(truck_id, int) or isinstance(truck_id, bool):
        raise ValueError("truck_id must be an integer")
    if truck_id < 1 or truck_id > 10000:
        raise ValueError("truck_id must be between 1 and 10000")
    return truck_id
```

### 3. Describing the Tool with JSON Schema (`name`, `description`, `inputSchema`)
An AI model never reads the Python code inside your function body. Instead, it reads a JSON metadata card (`tools/list`) containing three fields:
* **`name`:** Exact function identifier (e.g., `"get_truck_telemetry"`).
* **`description`:** Plain-English instruction telling the model *when* to use this tool and *what* it returns.
* **`inputSchema`:** A JSON Schema dictionary declaring `"type": "object"`, `"properties"` (each parameter's type, bounds, and description), and `"required"` parameter names.

### 4. Wrapping Requests and Responses in JSON-RPC 2.0 Envelopes
Instead of inventing a custom dictionary format for every project, MCP standardizes every message using **JSON-RPC 2.0**—a lightweight envelope with `"jsonrpc": "2.0"`, a matching `"id"` so the caller can pair each reply with its request, and either `"result"` (on success) or `"error"` (when a method or parameter is invalid).

---

## 2c. How Autonomous AI Agents Use Tools Without Hallucinating

You do not need prior AI agent coursework to understand how **tool-calling** works under the hood.

Imagine a human dispatcher sitting in front of a locked terminal. An unassisted LLM is like a brilliant analyst locked in a windowless room with no internet and no database access: if you ask *"What speed is Truck 219 driving right now?"*, the LLM has to either say *"I don't know"* or guess (hallucinate) a plausible-sounding number.

An **MCP-enabled AI Agent** solves this through a deterministic 4-step conversation loop controlled by your **MCP Host** (such as VS Code, Claude Desktop, or a Python agent runner):
1. **Discovery (`tools/list`):** When the session starts, the Host asks your MCP Server what tools exist and places those tool schemas in the LLM's system prompt.
2. **Tool Selection (`tools/call`):** When the user asks about Truck 219, the LLM does *not* write a SQL query or guess a speed. Instead, it outputs a structured JSON request: `{"method": "tools/call", "params": {"name": "get_truck_telemetry", "arguments": {"truck_id": 219}}}`.
3. **Sandboxed Execution (Your Code):** Your MCP Server receives that JSON-RPC message, validates `truck_id == 219`, queries the read-only Parquet/DuckDB store, and returns the exact JSON facts (`{"speed_mph": 62.5, "current_city": "Cheyenne, WY"}`).
4. **Grounded Final Answer:** The Host feeds your JSON tool result back to the LLM, which writes a factual, hallucination-free answer citing the exact numbers your server returned.

This establishes our core rule for Unit 6:

> **The Principle of Least Privilege for AI Agents:** Never give an autonomous model raw database credentials or an unrestricted `execute_sql` tool. Expose only discrete, read-only, schema-validated MCP tools with strict parameter bounds and row-count caps (`limit <= 25`).

---

## 2d. Why the $500,000 "Unrestricted SQL" Disaster Happened (Failure Case Study)

To understand why data engineers must never give raw, unconstrained database credentials to an autonomous AI agent, consider an authentic corporate failure.

Global Freightways deployed an experimental "AI Logistics Assistant" powered by an LLM to help terminal dispatchers answer questions about shipments. The system prompt instructed the model:
> *"You are a helpful logistics assistant. When users ask questions, translate their intent into a SQL query and execute it using the attached `execute_sql` database connection tool."*

The database connection tool was connected with read/write administrative credentials to the central PostgreSQL production cluster.

For three weeks, the system was a sensation. Dispatchers asked: *"How many shipments in Chicago are running late?"* and the AI generated:
```sql
SELECT count(*) FROM shipments WHERE city = 'Chicago' AND status = 'DELAYED';
```

### The Fatal Ambiguity
On a busy Thursday afternoon, a dispatcher was clearing out test shipments from a training exercise. The dispatcher typed into the AI chat window:
> *"Hey, can you please remove all the temporary demo shipments created yesterday?"*

The LLM attempted to construct a SQL delete command. However, the `shipments` table did not have a column called `is_demo`. The model reasoned:
> *"Since there is no demo flag, all shipments created yesterday must have been part of the demo."*

The LLM generated and executed:
```sql
DELETE FROM shipments WHERE created_at >= '2024-11-13 00:00:00';
```

In under 400 milliseconds, the autonomous agent permanently purged **42,000 active, multi-million-dollar commercial freight manifests** across the United States.

Dispatch screens went blank nationwide. Drivers arriving at terminals could not be matched to their trailers. The company was forced to halt interstate operations for 18 hours while database administrators performed a point-in-time recovery from off-site tape backups. The operational paralysis, driver detention fees, and missed SLA penalties totaled over **\$500,000**.

### The Engineering Autopsy
What was the fatal flaw?
* **Unconstrained Tool Surface:** The agent was given arbitrary SQL execution privileges.
* **Violation of Least Privilege:** A dispatcher assistant should never have permission to run `DELETE` or `DROP`.
* **Lack of Guardrails:** There was no schema validation, no parameter boundaries, and no sandboxing.

**The Lesson:** Never give an LLM raw SQL access. Instead, expose **discrete, validated, read-only MCP Tools** (`get_truck_telemetry(truck_id: int)`, `check_anomaly_status(trans_id: int)`) that execute tightly bounded queries.

---

## 2e. "The USB-C Standard for AI" & The Agent Tool-Calling Loop

Before MCP, every developer wrote custom wrappers for every LLM:
* If you used OpenAI, you wrote OpenAI function schemas.
* If you used Anthropic, you wrote Claude tool schemas.
* If you used Ollama, you wrote another custom parser.

This was like the 1990s computer era, when every peripheral device required a proprietary cable: serial ports, parallel printer ports, PS/2 mouse plugs, and SCSI connectors.

```
BEFORE MCP (Proprietary Mess):
[OpenAI] ──> Custom JSON Schema A ──> Database
[Claude] ──> Custom JSON Schema B ──> Database
[Ollama] ──> Custom Regex Parser  ──> Database

AFTER MCP (Universal USB-C Standard):
[OpenAI / Claude / Ollama / Copilot] 
               │ (Standard JSON-RPC 2.0)
               ▼
       [MCP Client Host]
               │
               ▼
       [MCP Data Server] ──> [Enterprise Data Engine]
```

MCP standardizes three foundational primitives:
1. **Tools:** Functions that the model can invoke to perform computations or fetch live state.
2. **Resources:** Static or dynamic data context (like database schemas or log files) that the host can attach to the prompt.
3. **Prompts:** Standardized instructional templates configured by the server.

### How the 4-Step Agent Tool-Calling Loop Operates
When a human operator asks an MCP-connected AI assistant a question, this four-step cycle executes behind the scenes:

```
STEP 1 (Discovery):
Agent asks MCP Server ──> {"method": "tools/list"}
MCP Server replies    ──> Lists available tools, descriptions, and argument schemas.

STEP 2 (User Question & Tool Selection):
Human asks Agent      ──> "Did Truck 219 pass inspection, and was transaction 1002 anomalous?"
Agent decides         ──> Emits tools/call for get_truck_telemetry(truck_id=219) and check_anomaly_status(trans_id=1002).

STEP 3 (Sandboxed Execution):
MCP Server validates  ──> Checks parameter bounds, queries read-only store, returns structured JSON.

STEP 4 (Grounded Answer):
Agent reads JSON      ──> Writes a clear summary citing the exact returned values.
```

---

## 2f. Defensive Tool Evolution — From Raw SQL to Sandboxed JSON-RPC 2.0

When an LLM requests a tool call, MCP communicates using standardized **JSON-RPC 2.0**:

### 1. The Client Sends Request:
```json
{
  "jsonrpc": "2.0",
  "id": "req-101",
  "method": "tools/call",
  "params": {
    "name": "get_truck_telemetry",
    "arguments": {
      "truck_id": 219
    }
  }
}
```

### 2. The Server Validates & Responds:
```json
{
  "jsonrpc": "2.0",
  "id": "req-101",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"truck_id\": 219, \"status\": \"ACTIVE\", \"speed_mph\": 64.2, \"fuel_pct\": 82.0}"
      }
    ]
  }
}
```

### Tracing the 3-Step Engineering Evolution
Let's compare three ways teams expose data to AI agents so you can see why sandboxed MCP tools win:

#### Step 1: Unrestricted `execute_sql(query: str)` (Catastrophic)
```python
# DANGEROUS: Allows DELETE, DROP, or dumping 1,000,000 rows into the LLM context window
def execute_sql(query: str):
    return db_conn.execute(query).fetchall()
```

#### Step 2: Fixed Function Without Input Validation or Row Caps (Fragile)
```python
# FRAGILE: No bounds check on limit; an agent asking for limit=1000000 crashes the context window
def get_anomalies(limit: int):
    return con.sql(f"SELECT * FROM anomalies LIMIT {limit}").df().to_dict(orient="records")
```

#### Step 3: Production Sandboxed MCP Tool (Type-Guarded, Read-Only, Bounded)
```python
# PRODUCTION: Strict integer/bool guards, bounded range, parameterized query, JSON-RPC 2.0 envelope
def get_recent_anomalies(limit: int = 5):
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > 25:
        return {"error": "limit must be an integer between 1 and 25"}
    return con.execute("SELECT * FROM anomalies LIMIT ?", [limit]).df().to_dict(orient="records")
```

---

## 2g. Step-by-Step Code Ramp-Up & Guided Implementation Walkthrough (Python MCP Server)

Let's build up the Python patterns for an MCP server step by step—starting from a single guarded Python function, defining its JSON Schema, and then assembling the complete `FleetMCPServer` class.

### Step 1: Writing a Bounded, Read-Only Data Tool Function
Every MCP tool starts as a regular Python function with clear type checks and defensive parameter bounds:

```python
def validate_positive_id(value: int, field_name: str, max_val: int = 10000) -> int:
    """Ensures an incoming tool argument is a true integer within safe bounds."""
    # Note: in Python, bool is a subclass of int (isinstance(True, int) is True!), so exclude bool:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    if value <= 0 or value > max_val:
        raise ValueError(f"{field_name} must be between 1 and {max_val}")
    return value

print("Validated ID:", validate_positive_id(219, "truck_id"))
```

### Step 2: Defining the MCP Tool Schema (`inputSchema`)
Next, we describe each function in a dictionary matching the MCP `tools/list` specification (`name`, `description`, and `inputSchema`). Clear descriptions are essential because the LLM reads `description` to decide when to call your tool!

### Step 3: Guided Implementation Walkthrough — Production Python MCP Server
Here is the complete `FleetMCPServer` implementation handling `tools/list` discovery, `tools/call` dispatch, defensive parameter bounds, and JSON-RPC 2.0 responses:

```python
import json
from typing import Dict, Any

class FleetMCPServer:
    """
    Production-grade Model Context Protocol server exposing
    defensive, read-only tools to autonomous LLM agents.
    """
    def __init__(self):
        self.tools = {
            "get_truck_telemetry": self.get_truck_telemetry,
            "check_anomaly_status": self.check_anomaly_status
        }
        
    def list_tools(self) -> Dict[str, Any]:
        """Exposes tool definitions following the MCP specification."""
        return {
            "tools": [
                {
                    "name": "get_truck_telemetry",
                    "description": "Retrieve current operational status, speed, and fuel level for a commercial truck.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "truck_id": {"type": "integer", "description": "The unique truck number (e.g. 219)"}
                        },
                        "required": ["truck_id"]
                    }
                },
                {
                    "name": "check_anomaly_status",
                    "description": "Check if a fuel transaction triggered fraud or physical anomaly flags.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "trans_id": {"type": "integer", "description": "The transaction ID"}
                        },
                        "required": ["trans_id"]
                    }
                }
            ]
        }

    def get_truck_telemetry(self, truck_id: int) -> Dict[str, Any]:
        # Defensive constraint: Validate positive integer bounds
        if not isinstance(truck_id, int) or isinstance(truck_id, bool) or truck_id <= 0 or truck_id > 10000:
            return {"error": "Invalid truck_id: Must be an integer between 1 and 10000"}
        return {
            "truck_id": truck_id,
            "status": "EN_ROUTE",
            "current_city": "Cheyenne, WY",
            "speed_mph": 62.5,
            "last_inspection": "PASS"
        }

    def check_anomaly_status(self, trans_id: int) -> Dict[str, Any]:
        if not isinstance(trans_id, int) or isinstance(trans_id, bool) or trans_id <= 0:
            return {"error": "Invalid trans_id: Must be a positive integer"}
        if trans_id == 1002:
            return {"trans_id": 1002, "is_anomaly": True, "reason": "Tank overflow violation"}
        return {"trans_id": trans_id, "is_anomaly": False, "reason": "Normal"}

    def handle_request(self, json_rpc_str: str) -> str:
        req = json.loads(json_rpc_str)
        method = req.get("method")
        
        if method == "tools/list":
            return json.dumps({"jsonrpc": "2.0", "id": req.get("id"), "result": self.list_tools()})
        elif method == "tools/call":
            params = req.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})
            if name in self.tools:
                result = self.tools[name](**args)
                return json.dumps({
                    "jsonrpc": "2.0",
                    "id": req.get("id"),
                    "result": {"content": [{"type": "text", "text": json.dumps(result)}]}
                })
            return json.dumps({
                "jsonrpc": "2.0",
                "id": req.get("id"),
                "error": {"code": -32601, "message": "Method not found"}
            })

server = FleetMCPServer()
test_call = json.dumps({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {"name": "get_truck_telemetry", "arguments": {"truck_id": 219}}
})
print("MCP Server Response:", server.handle_request(test_call))
```

**Verification Output:**
```json
MCP Server Response: {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "{\"truck_id\": 219, \"status\": \"EN_ROUTE\", \"current_city\": \"Cheyenne, WY\", \"speed_mph\": 62.5, \"last_inspection\": \"PASS\"}"}]}}
```

---

## 2h. Practice Exercises & Formative Self-Check FAQ

Try these three exercises in your GitHub Codespaces sandbox (`units/unit_06_agentic_interfaces_and_mcp/`) before starting the graded lab:

1. **Exercise 1 (Inspecting Tool Schemas):** Run `coding_clinic.ipynb` and inspect the output of `tools/list`. Check how every required parameter is listed in both `properties` and `required`.
2. **Exercise 2 (Testing SQL Injection Rejection):** Try passing `"219; DROP TABLE routes;"` as the `truck_id` argument in a `tools/call` request. Confirm that our integer type validation rejects the string immediately before any database query can run.
3. **Exercise 3 (Adding a Cap to `limit`):** Write a tool function `get_recent_anomalies(limit: int = 5)` that rejects `limit < 1` or `limit > 25`, ensuring an agent can never accidentally dump 1,000,000 rows in a single call.

### Common Traps & Formative Self-Check FAQ

* **Question 1: Why shouldn't an MCP server return natural language explanations directly?**  
  *Answer:* An MCP tool should return clean, structured JSON or raw domain data. The LLM agent is responsible for translating that structured data into conversational summaries for human users.

* **Question 2: How does MCP prevent prompt injection attacks?**  
  *Answer:* By enforcing strict JSON-RPC schemas and Pydantic/type parameter boundaries, untrusted user text cannot escape into arbitrary SQL commands or shell scripts. The discrete tool boundary acts as a read-only sandbox.

* **Question 3: What does JSON-RPC error code `-32601` mean?**  
  *Answer:* In the official JSON-RPC 2.0 specification, `-32601` is the standard error code for **"Method not found"** (returned when a client requests a method or tool name that is not registered on the server).

* **Question 4: Why do we check `isinstance(value, bool)` separately when validating integers in Python?**  
  *Answer:* In Python, `bool` is a subclass of `int` (`isinstance(True, int)` is `True`, and `True == 1`!). Checking `isinstance(value, bool)` explicitly prevents a caller from accidentally passing `True` or `False` as a `truck_id` or `limit`.

---

## 3. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical specifications before beginning your applied lab:

1. **[Model Context Protocol (MCP) Official Specification](https://modelcontextprotocol.io/introduction)**
   *Understand the core architecture, client-server lifecycle, transport layers (stdio vs SSE), and protocol primitives.*

2. **[Anthropic: Tool Use & Function Calling Guide](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)**
   *Master how modern foundation models parse tool schemas, construct function call arguments, and integrate tool outputs.*

3. **[JSON-RPC 2.0 Official Specification](https://www.jsonrpc.org/specification)**
   *Review the lightweight remote procedure call specification that powers all MCP message exchanges.*

4. **[Model Context Protocol Python SDK](https://github.com/modelcontextprotocol/python-sdk)**
   *Explore the official Python library for implementing standard-compliant MCP servers and clients.*

5. **[Ollama: Local LLM Tool Calling & Structured Outputs](https://ollama.com/blog/tool-support)**
   *Learn how to execute local agentic tool loops using open-weights models (`llama3.2`, `qwen2.5`) with zero API costs.*

---

## 4. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to observe the Model Context Protocol in action:

### What is the Model Context Protocol (MCP)? Integrating AI Agents with Data <span style="font-size: 0.9em; color: #64748b;">(IBM Technology - Architecture Overview)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Model Context Protocol Intro" src="https://www.youtube.com/embed/eur8dUO9mvE" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=eur8dUO9mvE" target="_blank" rel="noopener">Open video in new tab</a></p>

### How LLMs Use Tools: Function Calling & Agentic Loops <span style="font-size: 0.9em; color: #64748b;">(Google Cloud Tech - Core Concepts)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Function Calling Explained" src="https://www.youtube.com/embed/4vfDgLvuNQk" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=4vfDgLvuNQk" target="_blank" rel="noopener">Open video in new tab</a></p>

### Building a Custom MCP Server from Scratch in Python <span style="font-size: 0.9em; color: #64748b;">(Tech With Tim - Full Walkthrough)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Build a Custom MCP Server in Python" src="https://www.youtube.com/embed/-8k9lGpGQ6g" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=-8k9lGpGQ6g" target="_blank" rel="noopener">Open video in new tab</a></p>

---

## 5. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for Unit 6 will appear in this designated container.</p>
</div>
