from __future__ import annotations

import copy
from typing import Any, Dict, List, Set

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .payload_validator import validate_agent_update_payload
from .schemas import AgentUpdatePayload, EdgeUpdate, NodeUpdate


class PatchMergeError(RuntimeError):
    """Raised when a patch cannot be merged into the current graph state."""


class DraftGraphNode(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    id: str | None = None
    node_id: str | None = None

    @model_validator(mode="after")
    def validate_identifier(self) -> "DraftGraphNode":
        node_identifier = self.node_id or self.id
        if not node_identifier or not str(node_identifier).strip():
            raise ValueError("Each node must have a non-empty 'node_id' or 'id'.")
        return self


class DraftGraphEdge(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    source: str = Field(min_length=1)
    target: str = Field(min_length=1)


class DraftGraphValidator(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    nodes: List[DraftGraphNode]
    edges: List[DraftGraphEdge]

    @model_validator(mode="after")
    def validate_edge_references(self) -> "DraftGraphValidator":
        node_ids: Set[str] = {
            str(node.node_id or node.id).strip() for node in self.nodes if (node.node_id or node.id)
        }

        for edge in self.edges:
            if edge.source not in node_ids:
                raise ValueError(f"Edge source '{edge.source}' does not reference an existing node.")
            if edge.target not in node_ids:
                raise ValueError(f"Edge target '{edge.target}' does not reference an existing node.")

        return self


def _node_identifier(node: Dict[str, Any]) -> str:
    identifier = node.get("node_id") or node.get("id")
    if not identifier or not str(identifier).strip():
        raise PatchMergeError("Node in state is missing non-empty 'node_id' or 'id'.")
    return str(identifier)


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _extract_node_patch_fields(update: NodeUpdate) -> Dict[str, Any]:
    patch_fields: Dict[str, Any] = {}

    if update.changes:
        patch_fields = copy.deepcopy(update.changes)

    direct_fields = update.model_dump(exclude_none=True)
    for ignored in ("action", "node_id", "changes"):
        direct_fields.pop(ignored, None)

    if direct_fields:
        patch_fields = _deep_merge(patch_fields, direct_fields)

    return patch_fields


def _merge_node_updates(state: Dict[str, Any], node_updates: List[NodeUpdate]) -> None:
    nodes = state.setdefault("nodes", [])
    if not isinstance(nodes, list):
        raise PatchMergeError("State field 'nodes' must be a list.")

    for update in node_updates:
        action = update.action
        index = {
            _node_identifier(node): i
            for i, node in enumerate(nodes)
            if isinstance(node, dict)
        }

        node_idx = index.get(update.node_id)
        patch_fields = _extract_node_patch_fields(update)

        if action == "add":
            if node_idx is not None:
                raise PatchMergeError(f"Cannot add node '{update.node_id}': node already exists.")

            new_node = {"node_id": update.node_id}
            if patch_fields:
                new_node = _deep_merge(new_node, patch_fields)
            nodes.append(new_node)
            continue

        if action == "modify":
            if node_idx is None:
                raise PatchMergeError(f"Cannot modify node '{update.node_id}': node not found.")
            if not patch_fields:
                raise PatchMergeError(
                    f"Cannot modify node '{update.node_id}': no patch fields provided."
                )

            nodes[node_idx] = _deep_merge(nodes[node_idx], patch_fields)
            continue

        if action == "remove":
            if node_idx is None:
                raise PatchMergeError(f"Cannot remove node '{update.node_id}': node not found.")

            del nodes[node_idx]

            # Defensive cleanup for orphaned edges when node is deleted.
            edges = state.setdefault("edges", [])
            if not isinstance(edges, list):
                raise PatchMergeError("State field 'edges' must be a list.")
            state["edges"] = [
                edge
                for edge in edges
                if not (
                    isinstance(edge, dict)
                    and (edge.get("source") == update.node_id or edge.get("target") == update.node_id)
                )
            ]
            continue

        raise PatchMergeError(f"Unsupported node action '{action}'.")


def _match_edge(edge: Dict[str, Any], update: EdgeUpdate) -> bool:
    return edge.get("source") == update.source and edge.get("target") == update.target


def _merge_edge_updates(state: Dict[str, Any], edge_updates: List[EdgeUpdate]) -> None:
    edges = state.setdefault("edges", [])
    if not isinstance(edges, list):
        raise PatchMergeError("State field 'edges' must be a list.")

    for update in edge_updates:
        action = update.action
        edge_idx = next(
            (
                i
                for i, edge in enumerate(edges)
                if isinstance(edge, dict) and _match_edge(edge, update)
            ),
            None,
        )

        if action == "add":
            if edge_idx is not None:
                raise PatchMergeError(
                    f"Cannot add edge '{update.source}->{update.target}': edge already exists."
                )

            new_edge: Dict[str, Any] = {
                "source": update.source,
                "target": update.target,
            }
            if update.condition is not None:
                new_edge["condition"] = update.condition
            edges.append(new_edge)
            continue

        if action == "modify":
            if edge_idx is None:
                raise PatchMergeError(
                    f"Cannot modify edge '{update.source}->{update.target}': edge not found."
                )
            if update.condition is not None:
                edges[edge_idx]["condition"] = update.condition
            continue

        if action == "remove":
            if edge_idx is None:
                raise PatchMergeError(
                    f"Cannot remove edge '{update.source}->{update.target}': edge not found."
                )
            del edges[edge_idx]
            continue

        raise PatchMergeError(f"Unsupported edge action '{action}'.")


def apply_patch_to_graph(base_state: Dict[str, Any], patch_payload: Dict[str, Any] | AgentUpdatePayload) -> Dict[str, Any]:
    if isinstance(patch_payload, AgentUpdatePayload):
        patch = patch_payload
    else:
        patch = validate_agent_update_payload(patch_payload)

    merged_state = copy.deepcopy(base_state)

    if not isinstance(merged_state, dict):
        raise PatchMergeError("Base state must be a dictionary.")

    metadata = merged_state.setdefault("agent_metadata", {})
    if not isinstance(metadata, dict):
        raise PatchMergeError("State field 'agent_metadata' must be a dictionary.")
    merged_state["agent_metadata"] = _deep_merge(metadata, patch.agent_metadata_updates)

    _merge_node_updates(merged_state, patch.node_updates)
    _merge_edge_updates(merged_state, patch.edge_updates)

    try:
        DraftGraphValidator.model_validate(
            {
                "nodes": merged_state.get("nodes", []),
                "edges": merged_state.get("edges", []),
            }
        )
    except ValidationError as exc:
        raise PatchMergeError(f"Merged graph failed DraftGraph validation: {exc}") from exc

    return merged_state
