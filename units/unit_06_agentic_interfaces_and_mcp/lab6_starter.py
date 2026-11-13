"""
COSC 2060 — Unit 6 Lab: Model Context Protocol (MCP) Interface
Name: [Your Name]
Date: [Current Date]
"""

import json
import re
from typing import Dict, Any, Callable

# =========================================================================
# MOCK ENTERPRISE BACKENDS (Simulating Unit 1, 3, and 4 Data Stores)
# =========================================================================
FLEET_TELEMETRY = {
    "TRUCK-101": {"avg_speed_mph": 58.4, "fuel_mpg": 6.8, "status": "OPERATIONAL"},
    "TRUCK-219": {"avg_speed_mph": 52.1, "fuel_mpg": 5.1, "status": "REQUIRES_INSPECTION"}
}

VISION_DEFECTS = {
    "TRUCK-219": [{"defect": "tire_sidewall_crack", "confidence": 0.89, "axle": "steer_front_right"}],
    "TRUCK-101": []
}

MAINTENANCE_RAG = {
    "TRUCK-219": "Work Order WO-10045: Whistling sound at 1800 rpm; brass glitter in oil pan. Turbo recall active.",
    "TRUCK-101": "Work Order WO-09921: Standard oil filter change. All fluids topped off."
}


# %%
# =========================================================================
# PART 0: BASICS WARM-UP — JSON-RPC 2.0 MESSAGE FORMAT
# =========================================================================
def part0_basics_warmup() -> Dict[str, Any]:
    """
    PART 0: Basics Warm-Up (Ground-Up JSON-RPC 2.0 Structure)
    Constructs a minimal JSON-RPC 2.0 response envelope before registering
    and invoking multi-modal MCP tools.
    """
    print("=== Part 0: Basics Warm-Up (JSON-RPC 2.0 Envelope Structure) ===")
    rpc_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": [{"type": "text", "text": json.dumps({"status": "READY"})}]}
    }
    print("Sample JSON-RPC Response:", json.dumps(rpc_response))
    return rpc_response


# %%
# =========================================================================
# CHALLENGE 1: MCP Tool Registry & Schema Introspection (25 pts)
# =========================================================================
class MCPLogisticsServer:
    def __init__(self, server_name: str = "Logistics-MCP-Core"):
        self.server_name = server_name
        self.tools: Dict[str, Dict[str, Any]] = {}

    def register_tool(self, name: str, description: str, parameters_schema: Dict[str, Any]):
        """Registers a function as an MCP tool with explicit schema definition."""
        def decorator(func: Callable):
            self.tools[name] = {
                "name": name,
                "description": description,
                "inputSchema": parameters_schema,
                "handler": func
            }
            return func
        return decorator

    def list_tools(self) -> Dict[str, Any]:
        """Returns JSON-RPC compliant tools/list response."""
        tool_manifests = []
        for name, meta in self.tools.items():
            tool_manifests.append({
                "name": meta["name"],
                "description": meta["description"],
                "inputSchema": meta["inputSchema"]
            })
        return {"tools": tool_manifests}


server = MCPLogisticsServer()

# %%
# =========================================================================
# CHALLENGE 2: Defensive Input Validation & Least-Privilege Sandboxing (25 pts)
# =========================================================================
def sanitize_truck_id(truck_id: str) -> str:
    """Enforces strict format checking to prevent SQL or script injection."""
    if not isinstance(truck_id, str):
        raise ValueError("truck_id must be a string")
    clean = truck_id.strip().upper()
    if not re.match(r"^TRUCK-\d{3}$", clean):
        raise ValueError(f"Invalid truck identifier '{truck_id}'. Must match pattern TRUCK-XXX.")
    return clean


# %%
# =========================================================================
# CHALLENGE 3: Multimodal Fleet Safety Diagnostic Tool (25 pts)
# =========================================================================
@server.register_tool(
    name="get_truck_telemetry",
    description="Retrieves live operational telemetry including average speed, fuel efficiency, and status.",
    parameters_schema={
        "type": "object",
        "properties": {"truck_id": {"type": "string", "description": "Format TRUCK-XXX"}},
        "required": ["truck_id"]
    }
)
def get_truck_telemetry(truck_id: str) -> Dict[str, Any]:
    clean_id = sanitize_truck_id(truck_id)
    if clean_id not in FLEET_TELEMETRY:
        return {"status": "NOT_FOUND", "message": f"Truck {clean_id} not registered."}
    return {"status": "SUCCESS", "data": FLEET_TELEMETRY[clean_id]}


@server.register_tool(
    name="evaluate_fleet_safety_clearance",
    description="Performs multimodal safety clearance combining computer vision defects and maintenance RAG records.",
    parameters_schema={
        "type": "object",
        "properties": {"truck_id": {"type": "string", "description": "Format TRUCK-XXX"}},
        "required": ["truck_id"]
    }
)
def evaluate_fleet_safety_clearance(truck_id: str) -> Dict[str, Any]:
    """
    Multimodal Diagnostic Logic:
      - If vision detects 'sidewall_crack' OR maintenance notes mention 'turbo recall':
        Return clearance = 'GROUNDED' with CRITICAL severity.
      - Otherwise: Return clearance = 'CLEARED'.
    """
    clean_id = sanitize_truck_id(truck_id)
    defects = VISION_DEFECTS.get(clean_id, [])
    rag_notes = MAINTENANCE_RAG.get(clean_id, "")

    has_crack = any(d["defect"] == "tire_sidewall_crack" for d in defects)
    has_turbo_recall = "turbo recall" in rag_notes.lower()

    if has_crack or has_turbo_recall:
        reasons = []
        if has_crack:
            reasons.append("Computer Vision: Tire sidewall stress crack identified.")
        if has_turbo_recall:
            reasons.append("Maintenance RAG: Unresolved turbocharger oil line safety recall.")
        return {
            "truck_id": clean_id,
            "clearance": "GROUNDED",
            "risk_tier": "CRITICAL",
            "findings": reasons
        }
    else:
        return {
            "truck_id": clean_id,
            "clearance": "CLEARED",
            "risk_tier": "NORMAL",
            "findings": ["All vision and maintenance checks passed."]
        }


# %%
# =========================================================================
# CHALLENGE 4: Agentic JSON-RPC Tool Execution Simulation (25 pts)
# =========================================================================
def execute_agent_call(rpc_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulates the MCP Client dispatch loop:
      Parses a JSON-RPC 'tools/call' request and routes it to the registered handler.
    """
    req_id = rpc_request.get("id", 1)
    params = rpc_request.get("params", {})
    tool_name = params.get("name")
    args = params.get("arguments", {})

    if tool_name not in server.tools:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Tool '{tool_name}' not found."}
        }

    try:
        handler = server.tools[tool_name]["handler"]
        result = handler(**args)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result)}]
            }
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32000, "message": str(e)}
        }


# =========================================================================
# VERIFICATION SUITE (Do not modify)
# =========================================================================
# %%
if __name__ == "__main__":
    part0_basics_warmup()
    print("\n=== Step 1: Verifying Tool Manifest Registration ===")
    tools_list = server.list_tools()
    assert len(tools_list["tools"]) >= 2, f"Expected at least 2 tools, got {len(tools_list['tools'])}"
    tool_names = [t["name"] for t in tools_list["tools"]]
    assert "get_truck_telemetry" in tool_names
    assert "evaluate_fleet_safety_clearance" in tool_names
    print(f"[PASS] Registered tools verified: {tool_names}")

    print("\n=== Step 2: Testing Defensive Input Guardrail ===")
    try:
        sanitize_truck_id("TRUCK-219; DROP TABLE fleet;--")
        assert False, "Security guardrail failed to block injection string!"
    except ValueError:
        print("[PASS] Security guardrail successfully intercepted injection attack.")

    print("\n=== Step 3: Simulating Agent Call for Healthy Vehicle ===")
    healthy_call = {
        "jsonrpc": "2.0",
        "id": 101,
        "method": "tools/call",
        "params": {
            "name": "evaluate_fleet_safety_clearance",
            "arguments": {"truck_id": "TRUCK-101"}
        }
    }
    healthy_resp = execute_agent_call(healthy_call)
    payload = json.loads(healthy_resp["result"]["content"][0]["text"])
    assert payload["clearance"] == "CLEARED"
    assert payload["risk_tier"] == "NORMAL"
    print(f"[PASS] TRUCK-101 clearance verified: {payload['clearance']}")

    print("\n=== Step 4: Simulating Agent Call for High-Risk Vehicle (TRUCK-219) ===")
    risk_call = {
        "jsonrpc": "2.0",
        "id": 102,
        "method": "tools/call",
        "params": {
            "name": "evaluate_fleet_safety_clearance",
            "arguments": {"truck_id": "TRUCK-219"}
        }
    }
    risk_resp = execute_agent_call(risk_call)
    risk_payload = json.loads(risk_resp["result"]["content"][0]["text"])
    assert risk_payload["clearance"] == "GROUNDED"
    assert risk_payload["risk_tier"] == "CRITICAL"
    assert len(risk_payload["findings"]) == 2
    print(f"[PASS] TRUCK-219 grounded successfully with {len(risk_payload['findings'])} findings.")

    print("\n[SUCCESS] All Unit 6 Lab challenges verified successfully!")
