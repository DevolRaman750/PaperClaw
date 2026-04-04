from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrictSchemaModel(BaseModel):
    # Reject unknown keys and prevent implicit type coercion.
    model_config = ConfigDict(extra="forbid", strict=True)


class NodeUpdate(StrictSchemaModel):
    action: Literal["add", "modify", "remove"]
    node_id: str = Field(min_length=1)
    changes: Optional[Dict[str, Any]] = None
    name: Optional[str] = None
    node_type: Optional[str] = None
    description: Optional[str] = None
    tools: Optional[List[str]] = None
    input_keys: Optional[List[str]] = None
    output_keys: Optional[Dict[str, Any] | List[str]] = None
    system_prompt: Optional[str] = None


class EdgeUpdate(StrictSchemaModel):
    action: Literal["add", "modify", "remove"]
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    condition: Optional[str] = None


class AgentUpdatePayload(StrictSchemaModel):
    request_id: str = Field(min_length=1)
    target_agent: str = Field(min_length=1)
    intent_summary: str = Field(min_length=1)
    agent_metadata_updates: Dict[str, Any]
    node_updates: List[NodeUpdate]
    edge_updates: List[EdgeUpdate]
