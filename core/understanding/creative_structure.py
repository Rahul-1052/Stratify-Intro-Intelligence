"""Typed, recommendation-free description of an opening's organization."""

from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping


@dataclass(frozen=True)
class CreativeStructure:
    opening_strategy: str = "unavailable"
    information_order: str = "unavailable"
    visual_anchor: str = "unavailable"
    attention_evolution: str = "unavailable"
    structural_rhythm: str = "unavailable"
    information_density: str = "unavailable"
    reveal_pattern: str = "unavailable"
    transition_style: str = "unavailable"
    structural_consistency: str = "unavailable"
    creative_emphasis: str = "unavailable"
    confidence: str = "limited"

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "CreativeStructure":
        source = value if isinstance(value, Mapping) else {}
        return cls(**{
            field_name: str(source.get(field_name, field.default))
            for field_name, field in cls.__dataclass_fields__.items()
        })
