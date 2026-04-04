from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from pydantic import ValidationError

from .schemas import AgentUpdatePayload

logger = logging.getLogger(__name__)


class PayloadValidationException(ValueError):
    def __init__(
        self,
        message: str,
        *,
        missing_fields: List[str] | None = None,
        validation_errors: List[Dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.missing_fields = missing_fields or []
        self.validation_errors = validation_errors or []


def _format_error_path(location: tuple[Any, ...] | List[Any]) -> str:
    return ".".join(str(part) for part in location) if location else "payload"


def _normalize_payload(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode("utf-8")

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            message = f"Malformed JSON body: {exc.msg}"
            logger.error(message)
            raise PayloadValidationException(message) from exc

    if not isinstance(payload, dict):
        message = "Invalid payload type. Expected a JSON object for AgentUpdatePayload."
        logger.error(message)
        raise PayloadValidationException(message)

    return payload


def validate_agent_update_payload(payload: Any) -> AgentUpdatePayload:
    normalized_payload = _normalize_payload(payload)

    try:
        validated_payload = AgentUpdatePayload.model_validate(normalized_payload)
    except ValidationError as exc:
        missing_fields: List[str] = []
        for err in exc.errors():
            if err.get("type") == "missing":
                missing_fields.append(_format_error_path(err.get("loc", ())))

        if missing_fields:
            logger.error(
                "AgentUpdatePayload validation failed. Missing required field(s): %s",
                ", ".join(missing_fields),
            )

        logger.error("AgentUpdatePayload validation errors: %s", exc.errors())
        raise PayloadValidationException(
            "AgentUpdatePayload validation failed.",
            missing_fields=missing_fields,
            validation_errors=exc.errors(),
        ) from exc

    logger.info(
        "AgentUpdatePayload validation succeeded for request_id=%s target_agent=%s",
        validated_payload.request_id,
        validated_payload.target_agent,
    )
    return validated_payload


def validate_and_pass_agent_update_payload(payload: Any) -> Dict[str, Any]:
    return validate_agent_update_payload(payload).model_dump()
