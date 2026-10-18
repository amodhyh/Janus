from dataclasses import dataclass
from enum import Enum
from typing import Optional

class DTODecision(Enum):
    ALLOW = 1
    DENY = 2
    MUTATE = 3

@dataclass(slots=True)
class PipelineDTO:
    """
    Data Transfer Object carrying the state and decision of a prompt 
    as it moves through the inspection pipeline.
    """
    action: DTODecision
    prompt: str
    is_final: bool = False
    reason: Optional[str] = None