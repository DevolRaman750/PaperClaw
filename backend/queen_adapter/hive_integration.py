from __future__ import annotations

import json
import importlib
import os
import sys
from typing import Any, Dict, List


ADAPTER_ROOT = os.path.dirname(os.path.abspath(__file__))
HIVE_ROOT = os.path.abspath(os.path.join(ADAPTER_ROOT, "../../hive"))
HIVE_TOOLS_PATH = os.path.join(HIVE_ROOT, "tools")

if HIVE_TOOLS_PATH not in sys.path:
    sys.path.append(HIVE_TOOLS_PATH)


class HiveBuildIntegrationError(RuntimeError):
    """Raised when patched graph cannot be forwarded to Hive builder tools."""


def _load_coder_tools_server() -> Any:
    try:
        coder_tools_server = importlib.import_module("coder_tools_server")
    except Exception as exc:
        raise HiveBuildIntegrationError(
            "Unable to import Hive coder_tools_server. "
            f"Ensure Hive dependencies are installed. Details: {exc}"
        ) from exc

    # Critical injection to force scaffolding under BuilderPlatform/hive.
    coder_tools_server.PROJECT_ROOT = HIVE_ROOT
    coder_tools_server.SNAPSHOT_DIR = os.path.join(
        os.path.expanduser("~"), ".hive", "snapshots", "hive"
    )

    return coder_tools_server


def _extract_node_ids(patched_json: Dict[str, Any]) -> List[str]:
    node_ids: List[str] = []
    for node in patched_json.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_id = node.get("id") or node.get("node_id")
        if node_id and str(node_id).strip():
            node_ids.append(str(node_id))
    return node_ids


def build_v2_agent(patched_json: Dict[str, Any]) -> Dict[str, Any]:
    coder_tools_server = _load_coder_tools_server()

    agent_name = (patched_json.get("agent_name") or "").strip()
    if not agent_name:
        raise HiveBuildIntegrationError("patched_json must include a non-empty 'agent_name'.")

    node_ids = _extract_node_ids(patched_json)
    nodes_csv = ",".join(node_ids)

    result = coder_tools_server.initialize_and_build_agent(
        agent_name=agent_name,
        nodes=nodes_csv if nodes_csv else None,
        _draft=patched_json,
    )

    if isinstance(result, str):
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            return {"success": False, "raw_result": result}
        return parsed if isinstance(parsed, dict) else {"success": True, "result": parsed}

    if isinstance(result, dict):
        return result

    return {"success": True, "result": result}
