"""Typed creator-readable understanding derived from creative structure."""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping


@dataclass(frozen=True)
class CreativeUnderstanding:
    summary: str = "The available observations do not establish how the opening is organized."
    primary_strategy: str = "unavailable"
    structural_summary: str = "unavailable"
    supporting_evidence: List[Dict[str, Any]] = field(default_factory=list)
    evidence_strength: str = "limited"
    confidence: str = "limited"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "CreativeUnderstanding":
        source = value if isinstance(value, Mapping) else {}
        evidence = source.get("supporting_evidence", [])
        return cls(
            summary=str(source.get("summary", cls.__dataclass_fields__["summary"].default)),
            primary_strategy=str(source.get("primary_strategy", "unavailable")),
            structural_summary=str(source.get("structural_summary", "unavailable")),
            supporting_evidence=[dict(item) for item in evidence if isinstance(item, Mapping)],
            evidence_strength=str(source.get("evidence_strength", "limited")),
            confidence=str(source.get("confidence", "limited")),
        )
