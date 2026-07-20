"""Reusable intelligence-module contract without speculative engines."""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping, Optional, Tuple


class ModuleStatus(str, Enum):
    AVAILABLE = "available"
    PLANNED = "planned"


class IntelligenceStage(str, Enum):
    ACQUIRE = "acquire"
    OBSERVE = "observe"
    UNDERSTAND = "understand"
    REASON = "reason"
    RECOMMEND = "recommend"
    VALIDATE = "validate"
    PRESENT = "present"


ModuleRunner = Callable[..., Mapping]


@dataclass(frozen=True)
class IntelligenceModule:
    module_id: str
    name: str
    description: str
    status: ModuleStatus
    version: str
    supported_inputs: Tuple[str, ...]
    capabilities: Tuple[str, ...]
    stages: Tuple[IntelligenceStage, ...]
    runner: Optional[ModuleRunner] = None

    @property
    def is_available(self):
        return self.status is ModuleStatus.AVAILABLE and self.runner is not None

    def run(self, **kwargs):
        if not self.is_available:
            raise RuntimeError(f"{self.name} is {self.status.value} and cannot be run.")
        return self.runner(**kwargs)
