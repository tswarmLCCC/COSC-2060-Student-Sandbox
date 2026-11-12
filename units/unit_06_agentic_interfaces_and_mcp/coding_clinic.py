"""
====================================================================
COSC 2060: Modern Data Engineering & AI Infrastructure
Unit 6 Synchronous Coding Clinic ("I Do, We Do, You Do")
Topic: The Agentic Interface & Model Context Protocol (MCP)
====================================================================
Run this script from the terminal to execute the live class walkthrough
demonstrations:
    python units/unit_06_agentic_interfaces_and_mcp/coding_clinic.py
====================================================================
"""


# ====================================================================
# PART 0: BASICS WARM-UP — JSON-RPC 2.0 ENVELOPE BASICS
# ====================================================================
print("\n>>> Executing PART 0: BASICS WARM-UP (JSON-RPC 2.0 Request/Response)...")
import json

sample_rpc_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {"name": "ping_truck", "arguments": {"truck_id": "TRUCK-101"}}
}
print("Part 0 Warm-Up — JSON-RPC Request Envelope:", json.dumps(sample_rpc_request))


# ====================================================================
# PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION
# ====================================================================
print("\n>>> Executing PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION...")
import inspect
from typing import Callable, Any

class SimpleToolRegistry:
    def __init__(self):
        self.tools = {}

    def register_tool(self, name: str, description: str):
        def decorator(func: Callable):
            sig = inspect.signature(func)
            params = {k: str(v.annotation) for k, v in sig.parameters.items()}
            self.tools[name] = {
                "name": name,
                "description": description,
                "parameters": params,
                "handler": func
            }
            return func
        return decorator

registry = SimpleToolRegistry()

@registry.register_tool(
    name="get_weather_delay",
    description="Returns current severe weather risk score for a specific route."
)
def get_weather_delay(route_id: str) -> dict:
    return {"route_id": route_id, "risk": "HIGH", "snow_inches": 6.5}

print("Registered Tool:", registry.tools["get_weather_delay"]["name"])


# ====================================================================
# PART 2: 'WE DO' — GUIDED CLASS PRACTICE
# ====================================================================
print("\n>>> Executing PART 2: 'WE DO' — GUIDED CLASS PRACTICE...")
import re

def safe_truck_id_validator(truck_id: str) -> str:
    """Blocks prompt injection or malicious SQL fragments inside tool arguments."""
    clean = truck_id.strip().upper()
    if not re.match(r"^TRUCK-\d{3}$", clean):
        raise ValueError(f"Security Alert: '{truck_id}' is not a valid truck ID format.")
    return clean

# Test defense:
try:
    safe_truck_id_validator("TRUCK-219; DROP TABLE trucks;--")
except ValueError as e:
    print("Defensive Guardrail successfully blocked attack:", e)

