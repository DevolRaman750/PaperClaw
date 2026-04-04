from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


class AdapterStateStoreError(RuntimeError):
    """Base error for adapter state store failures."""


class StateNotFoundError(AdapterStateStoreError):
    """Raised when a requested agent state version is missing."""


class StateAlreadyInitializedError(AdapterStateStoreError):
    """Raised when trying to initialize state for an agent that already exists."""


class AdapterStateStore:
    """Filesystem-backed state store for Queen Adapter graph versions.

    Files are stored as:
    - agent_{agent_id}_v1.json
    - agent_{agent_id}_v2.json
    - ...
    """

    def __init__(self, state_dir: str | Path | None = None) -> None:
        default_dir = Path(__file__).resolve().parent.parent / "adapter_state"
        self.state_dir = Path(state_dir) if state_dir is not None else default_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _normalize_agent_id(agent_id: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9_-]", "_", agent_id.strip())
        if not normalized:
            raise ValueError("agent_id must contain at least one valid character")
        return normalized

    def _state_file(self, agent_id: str, version: int) -> Path:
        normalized_agent_id = self._normalize_agent_id(agent_id)
        if version < 1:
            raise ValueError("version must be >= 1")
        return self.state_dir / f"agent_{normalized_agent_id}_v{version}.json"

    def list_versions(self, agent_id: str) -> List[int]:
        normalized_agent_id = self._normalize_agent_id(agent_id)
        pattern = re.compile(rf"^agent_{re.escape(normalized_agent_id)}_v(\d+)\.json$")

        versions: List[int] = []
        for file_path in self.state_dir.glob(f"agent_{normalized_agent_id}_v*.json"):
            match = pattern.match(file_path.name)
            if match:
                versions.append(int(match.group(1)))

        versions.sort()
        return versions

    def get_latest_version(self, agent_id: str) -> int | None:
        versions = self.list_versions(agent_id)
        return versions[-1] if versions else None

    def save_version(self, agent_id: str, version: int, state: Dict[str, Any]) -> Path:
        file_path = self._state_file(agent_id, version)
        file_path.write_text(json.dumps(state, indent=2, ensure_ascii=True), encoding="utf-8")
        return file_path

    def initialize_agent_state(self, agent_id: str, initial_state: Dict[str, Any]) -> int:
        if self.get_latest_version(agent_id) is not None:
            raise StateAlreadyInitializedError(
                f"State already exists for agent '{agent_id}'. Use save_next_patch_state instead."
            )

        self.save_version(agent_id, 1, initial_state)
        return 1

    def save_next_patch_state(self, agent_id: str, patched_state: Dict[str, Any]) -> int:
        latest_version = self.get_latest_version(agent_id)
        next_version = 1 if latest_version is None else latest_version + 1
        self.save_version(agent_id, next_version, patched_state)
        return next_version

    def load_state(self, agent_id: str, version: int) -> Dict[str, Any]:
        file_path = self._state_file(agent_id, version)
        if not file_path.exists():
            raise StateNotFoundError(
                f"State file not found for agent '{agent_id}' version {version}."
            )

        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AdapterStateStoreError(
                f"State file is corrupted for agent '{agent_id}' version {version}."
            ) from exc

    def load_latest_state(self, agent_id: str) -> Tuple[int, Dict[str, Any]]:
        latest_version = self.get_latest_version(agent_id)
        if latest_version is None:
            raise StateNotFoundError(f"No state found for agent '{agent_id}'.")
        return latest_version, self.load_state(agent_id, latest_version)
