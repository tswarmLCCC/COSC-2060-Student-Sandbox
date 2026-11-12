# Unit 6: Required Readings, Concepts & Video Lectures

Welcome to the instructional reading and study guide for **Unit 6: Agentic Interfaces & Model Context Protocol (MCP)**. This page organizes the week's learning materials into four sections:

1. **Instructor Lecture & Conceptual Deep Dive:** Learn how AI agents call external tools, what an MCP tool schema and JSON-RPC 2.0 response look like, why agents should never be given unrestricted SQL permissions, and how to build a safe, read-only MCP tool server in Python step by step.
2. **Required Readings & Tutorial Guides:** Explore official documentation from the Model Context Protocol (MCP), Anthropic tool use guides, JSON-RPC 2.0, and Ollama local tool calling.
3. **Required Micro-Video Lectures (Embedded):** Watch focused video tutorials covering MCP architecture, function calling, and building custom MCP servers in Python.
4. **Institutional Video Lecture Embeds:** Access instructor announcements and lab walkthrough recordings.

*Work through each section in sequence as part of your 150-minute self-study block before starting the applied lab.*

---

## 1. Instructor Lecture & Conceptual Deep Dive

### Connecting AI Agents to Data Safely with MCP

In Unit 5, we wrapped our datasets behind FastAPI endpoints so web dashboards and mobile apps could request clean, validated JSON data. In **Unit 6**, we look at a new type of software client that needs access to our data pipelines: **AI Agents**.

By itself, a Large Language Model (LLM) only predicts words based on what it read during training. It has no built-in way to check whether Truck #219 is delayed right now, whether a fuel card swipe was flagged for fraud, or what a mechanic typed in yesterday's work order.

To let an AI assistant look up live facts, engineers give the model **tools**—Python functions that the model can ask to run. Instead of writing custom integration code for every different AI vendor, the industry uses an open standard called the **Model Context Protocol (MCP)**. Think of MCP as a **universal USB-C port for AI**: write one MCP server around your DuckDB, Polars, and RAG pipelines, and any MCP-compatible AI client (such as Claude Desktop, VS Code Copilot, or local Ollama agents) can discover and call your tools safely.

```
USER QUESTION ──> AI AGENT ──(JSON-RPC Tool Call)──> MCP SERVER ──> DUCKDB / POLARS / RAG
                           <──(Structured JSON)──────┘
```

#### Measurable Learning Objectives
* **Explain** how the Model Context Protocol (MCP) connects AI models to backend datasets using standard **JSON-RPC 2.0** messages (`tools/list` and `tools/call`).
* **Design** clear MCP tool definitions with descriptive docstrings and JSON Schema / Pydantic input rules so an AI agent knows when and how to call each tool.
* **Apply** the **Principle of Least Privilege** by exposing bounded, read-only query tools instead of raw SQL execution.
* **Implement** a Python MCP server that serves live telemetry, anomaly statuses, and maintenance RAG search results from our Units 1–4 datasets.
* **Verify** multi-step agentic tool loops against malformed arguments and injection attempts.

---

### What Our Output Looks Like and Where the Data Comes From

#### The Purpose
Our goal in Unit 6 is to build a **Sandboxed MCP Tool Server** that exposes our logistics data pipelines as structured, read-only tools over **JSON-RPC 2.0**. When an AI agent asks what tools are available (`tools/list`) or invokes a specific tool (`tools/call`), our server validates the parameters, queries the underlying dataset, and returns a structured JSON-RPC response.

#### Why AI Agents Need Structured Tool Schemas and Guardrails
An AI agent does not read your Python source code to figure out how to query your database. Instead, when an agent connects to your MCP server, it reads two things:
1. **The Tool Registry (`tools/list`):** A JSON catalog listing every tool's `name`, plain-English `description`, and `inputSchema` (the exact parameter names, types, and required fields).
2. **The Tool Response (`tools/call`):** A predictable JSON envelope returning either the requested records or a clear validation error message that helps the agent self-correct if it passed an invalid ID.

#### Where the Raw Data Comes From (Source Systems)
An MCP server connects two sides of our architecture:
1. **Inbound Agent Requests (MCP Host / LLM Client):** An AI assistant running in a dispatch console translates a human dispatcher's question (*"Is Truck 219 safe to dispatch to Denver?"*) into one or more structured JSON-RPC `tools/call` messages.
2. **Backend Curated Data Stores (`feature_matrix.parquet`, `anomaly_features.parquet`, `rag_chunks.jsonl`):** The MCP server executes read-only lookups against our curated tables and returns compact JSON summaries (never dumping millions of raw rows into the model's context window).

#### Sample Output Dataset (The Target MCP JSON-RPC Shape)
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
        "description": "Fetch current city, speed, and delay status for a specific fleet truck_id (1 to 10000).",
        "inputSchema": {
          "type": "object",
          "properties": {
            "truck_id": { "type": "integer", "minimum": 1, "maximum": 10000 }
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
  "id": "req-2",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"truck_id\": 219, \"status\": \"EN_ROUTE\", \"origin_city\": \"Cheyenne\", \"predicted_delay_mins\": 15}"
      }
    ],
    "isError": false
  }
}
```

---

### Why You Should Never Give an AI Agent Raw SQL Access

When developers build their first AI database assistant, it is tempting to write a single tool called `run_sql(query: str)` and tell the language model: *"Write any SQL query you need and run it on the database."*

Let's look at why that approach fails in real operations.

A freight company built an internal chatbot to help dispatchers check on shipments. They connected the chatbot directly to their PostgreSQL database using an admin account that had both read (`SELECT`) and write (`DELETE`, `UPDATE`) permissions.

For a few weeks, dispatchers asked questions like *"How many shipments in Chicago are running late?"* and the model ran harmless `SELECT` queries. Then one afternoon, after a training session, a dispatcher typed:
> *"Can you clear out the temporary demo shipments we created yesterday?"*

The `shipments` table didn't have a column named `is_demo`. Guessing at what the user meant, the language model generated and ran:

```sql
DELETE FROM shipments WHERE created_at >= '2026-10-23 00:00:00';
```

In less than a second, the database deleted **42,000 real, active customer shipments**, forcing the company to shut down dispatch terminals for hours while administrators restored backups.

#### Three Defensive Rules for AI Data Tools
To prevent accidents and malicious **prompt injection**, data engineers follow three rules when building MCP servers:
1. **Never Expose Raw SQL Execution:** Instead of `run_sql(query)`, expose specific, purpose-built Python functions like `get_truck_telemetry(truck_id: int)` or `search_maintenance_logs(query: str, limit: int = 5)`.
2. **Enforce Read-Only Connections and Parameter Bounds:** Validate that IDs are positive integers and cap `limit` parameters (for example, `1 <= limit <= 20`) so a single tool call cannot dump the entire database into memory.
3. **Use Parameterized Queries:** Never glue user strings directly into SQL with f-strings (`f"WHERE city = '{city}'"`). Always use parameterized placeholders (`?`) or validated domain lookups.

---

### How the Agent Tool-Calling Loop Works

When a human asks an MCP-enabled AI assistant a question, the human does not type JSON. Here is the four-step loop that happens behind the scenes:

```
STEP 1 (Discovery):
Agent asks MCP Server ──> {"method": "tools/list"}
MCP Server replies    ──> Lists available tools, descriptions, and argument schemas.

STEP 2 (User Question & Tool Selection):
Human asks Agent      ──> "Did Truck 219 have any recent fuel anomalies or turbo issues?"
Agent decides         ──> Calls get_truck_anomalies(truck_id=219) AND search_maintenance(truck_id="TRUCK-219").

STEP 3 (Sandboxed Execution):
MCP Server validates  ──> Checks truck_id bounds, queries Parquet/RAG index, returns structured JSON.

STEP 4 (Grounded Answer):
Agent reads JSON      ──> Writes a clear summary citing the exact transaction ID and work order ID.
```

Notice why the **tool description** and **parameter descriptions** in your MCP server are so important: those descriptions are the instructions the AI model reads to decide *which* tool to call and *what* arguments to pass!

---

### Step-by-Step Code Ramp-Up: Building an MCP Server from the Ground Up

Let's build up the Python patterns for an MCP tool server step by step, starting from a simple Python function and wrapping it in JSON-RPC 2.0 discovery, validation, and dispatch.

#### Step 1: Writing a Bounded, Read-Only Data Tool Function
Every MCP tool starts as a regular Python function with clear type hints, defensive parameter checks, and a dictionary return value:

```python
def get_truck_telemetry(truck_id: int) -> dict:
    """Fetch current operational status, city, and predicted delay for a fleet truck."""
    # 1. Defensive type & boundary check
    if not isinstance(truck_id, int) or isinstance(truck_id, bool):
        raise ValueError("truck_id must be an integer.")
    if truck_id < 1 or truck_id > 10000:
        raise ValueError("truck_id must be between 1 and 10000.")

    # 2. Read-only lookup (e.g. from DuckDB/Parquet or in-memory table)
    sample_fleet = {
        101: {"truck_id": 101, "origin_city": "Cheyenne", "status": "ON_TIME", "delay_mins": 0},
        219: {"truck_id": 219, "origin_city": "Denver", "status": "DELAYED", "delay_mins": 45},
    }
    if truck_id not in sample_fleet:
        return {"truck_id": truck_id, "status": "NOT_FOUND", "message": f"No telemetry found for truck {truck_id}"}
    return sample_fleet[truck_id]

print(get_truck_telemetry(219))
```

#### Step 2: Defining the MCP Tool Schema (`tools/list`)
Next, we describe our function using the standard MCP tool schema format so any AI model can inspect its name, description, and required parameters:

```python
MCP_TOOLS_CATALOG = [
    {
        "name": "get_truck_telemetry",
        "description": "Retrieve current city, operational status, and delay minutes for a specific truck_id (1 to 10000).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "truck_id": {
                    "type": "integer",
                    "description": "Unique positive integer truck ID (between 1 and 10000)",
                    "minimum": 1,
                    "maximum": 10000
                }
            },
            "required": ["truck_id"]
        }
    }
]
```

#### Step 3: Handling JSON-RPC 2.0 Requests (`tools/list` and `tools/call`)
Now let's connect our catalog and function inside a clean `FleetMCPServer` class that processes standard JSON-RPC 2.0 messages and catches any validation errors cleanly without crashing:

```python
import json

class FleetMCPServer:
    def __init__(self):
        self.tool_functions = {
            "get_truck_telemetry": get_truck_telemetry,
        }

    def handle_jsonrpc(self, raw_request: str) -> dict:
        """Processes a JSON-RPC 2.0 request string and returns a JSON-RPC 2.0 response dict."""
        req = json.loads(raw_request)
        req_id = req.get("id")
        method = req.get("method")

        # 1. Handle Tool Discovery (tools/list)
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": MCP_TOOLS_CATALOG}
            }

        # 2. Handle Tool Execution (tools/call)
        if method == "tools/call":
            params = req.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name not in self.tool_functions:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                }

            try:
                output = self.tool_functions[tool_name](**arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(output)}],
                        "isError": False
                    }
                }
            except Exception as exc:
                # Return structured error feedback so the agent knows what parameter was invalid
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps({"error": str(exc)})}],
                        "isError": True
                    }
                }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unsupported method: {method}"}
        }

server = FleetMCPServer()

# Test 1: Discover available tools
list_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
print("Discovered tools:", len(server.handle_jsonrpc(list_req)["result"]["tools"]))

# Test 2: Valid tool call
call_req = json.dumps({
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {"name": "get_truck_telemetry", "arguments": {"truck_id": 219}}
})
print("Valid call response:", server.handle_jsonrpc(call_req))

# Test 3: Out-of-bounds tool call (truck_id = -5) caught safely!
bad_req = json.dumps({
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {"name": "get_truck_telemetry", "arguments": {"truck_id": -5}}
})
print("Guarded error response:", server.handle_jsonrpc(bad_req))
```

---

### Practice Exercises and Common Questions

Try these three exercises in your GitHub Codespaces sandbox (`units/unit_06_agentic_interfaces_and_mcp/`) before starting the graded lab:

1. **Exercise 1 (Inspecting Tool Schemas):** Run `coding_clinic.py` and inspect the output of `tools/list`. Check how every required parameter is listed in both `properties` and `required`.
2. **Exercise 2 (Testing SQL Injection Rejection):** Try passing `"219; DROP TABLE routes;"` as the `truck_id` argument in a `tools/call` request. Confirm that our integer type validation rejects the string immediately before any database query can run.
3. **Exercise 3 (Adding a Cap to `limit`):** Write a tool function `get_recent_anomalies(limit: int = 5)` that raises a `ValueError` if `limit < 1` or `limit > 25`, ensuring an agent can never accidentally request 1,000,000 rows in a single message.

#### Common Questions & Troubleshooting

* **Question 1: Why does `isinstance(True, int)` evaluate to `True` in Python, and why did we check `not isinstance(truck_id, bool)`?**  
  *Answer:* In Python, `bool` is a subclass of `int` (`True == 1` and `False == 0`)! If an AI agent mistakenly passes `{"truck_id": true}`, `isinstance(True, int)` would pass unless you also check `not isinstance(truck_id, bool)` (or use Pydantic's strict integer validation).

* **Question 2: Should an MCP tool return a long conversational paragraph or a compact JSON dictionary?**  
  *Answer:* Always return a compact, structured JSON dictionary containing the exact fields and values from your data store. The AI agent will read that structured JSON and write the conversational explanation for the user.

* **Question 3: What does JSON-RPC error code `-32601` mean?**  
  *Answer:* In the official JSON-RPC 2.0 specification, `-32601` is the standard code for **"Method not found"** (for example, when a client asks to call a tool name that does not exist on the server).

---

## 2. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical references before beginning your applied lab:

1. **[Model Context Protocol (MCP) Official Introduction](https://modelcontextprotocol.io/introduction)**
   *Understand the core architecture, client-server lifecycle, and protocol primitives (Tools, Resources, Prompts).*

2. **[Anthropic Documentation: Tool Use & Function Calling](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)**
   *Learn how language models read tool schemas, construct function arguments, and interpret tool results.*

3. **[JSON-RPC 2.0 Official Specification](https://www.jsonrpc.org/specification)**
   *Review the request/response envelope format and standard error codes used by MCP.*

4. **[Model Context Protocol Python SDK (`FastMCP`)](https://github.com/modelcontextprotocol/python-sdk)**
   *Explore the official Python SDK for building MCP servers and clients.*

5. **[Ollama Blog: Local LLM Tool Support](https://ollama.com/blog/tool-support)**
   *See how open-weight models execute local tool calls on your own hardware.*

---

## 3. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to see the Model Context Protocol and agent tool calling in action:

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

## 4. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for Unit 6 will appear in this designated container.</p>
</div>
