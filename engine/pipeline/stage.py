from typing import Protocol
from .pipelineDTO import PipelineDTO

class PipelineStage(Protocol):
    """
    Structural interface (Go-style) for all Security Engine pipeline passes.
    
    Any class with a process() method matching this signature implicitly 
    satisfies this protocol. No explicit inheritance is required.
    """
    def process(self, prompt: str) -> PipelineDTO:
        """
        Evaluates or mutates a prompt.
        
        Args:
            prompt: The current state of the text to be evaluated.
            
        Returns:
            PipelineDTO containing the decision, the potentially mutated prompt,
            and control flow flags (is_final).
        """
        ...