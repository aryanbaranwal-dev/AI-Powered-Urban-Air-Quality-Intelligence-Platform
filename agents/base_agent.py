"""
Shared protocol for the multi-agent AQI intelligence system.

Every agent in this package is INDEPENDENT — it can be imported, tested,
scheduled, or deployed on its own — but they all speak the same language:
a structured JSON envelope (`AgentMessage`). The Coordinator Agent is the
only piece that knows how to call all of them and merge their output, so
adding a 6th agent later never requires touching the others.

    AgentMessage
    ├── agent          which agent produced this
    ├── city
    ├── generated_at   ISO-8601 UTC timestamp
    ├── status         "ok" | "error"
    └── payload        agent-specific structured data (dict)
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict


@dataclass
class AgentMessage:
    agent: str
    city: str
    payload: Dict[str, Any]
    status: str = "ok"
    generated_at: str = field(default_factory=lambda: dt.datetime.utcnow().isoformat() + "Z")

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(asdict(self), indent=indent, default=str)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseAgent:
    """Every concrete agent implements `.run(...) -> AgentMessage`."""

    name: str = "base_agent"

    def _ok(self, city: str, payload: Dict[str, Any]) -> AgentMessage:
        return AgentMessage(agent=self.name, city=city, payload=payload, status="ok")

    def _error(self, city: str, message: str) -> AgentMessage:
        return AgentMessage(agent=self.name, city=city, payload={"error": message}, status="error")

    def run(self, **kwargs) -> AgentMessage:  # pragma: no cover - interface
        raise NotImplementedError
