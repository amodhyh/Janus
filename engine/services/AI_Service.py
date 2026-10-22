try:
    from pb.v1.janus_pb2_grpc import SecurityEngineServicer
    from pb.v1.janus_pb2 import InspectionRequest, InspectionResponse
    import pb.v1.janus_pb2 as janus_pb2
except (ImportError, ModuleNotFoundError):
    from engine.pb.v1.janus_pb2_grpc import SecurityEngineServicer
    from engine.pb.v1.janus_pb2 import InspectionRequest, InspectionResponse
    import engine.pb.v1.janus_pb2 as janus_pb2

import grpc
from concurrent import futures
import threading

try:
    from pipeline import RegexStage, DTODecision, get_classifier
except (ImportError, ModuleNotFoundError):
    from engine.pipeline import RegexStage, DTODecision, get_classifier


class SecurityService(SecurityEngineServicer):
    """Manages the tiered prompt security inspection pipeline."""
    
    def __init__(self):
        super().__init__()
        print("Initiating Janus Security Pipeline...")
        self.regex_stage = RegexStage()
        self.classifier_light = get_classifier()
        self.classifier_llm = None
        self.slm_lock = threading.Lock()
        self.llm_lock = threading.Lock()
        

    def InspectPrompt(self, request: InspectionRequest, context) -> InspectionResponse:
        prompt = request.raw_prompt
        
        #  Regex Inspection
        regex_dto = self.regex_stage.process(prompt)
        
        # Short-circuit fast denial (e.g. hardcoded jailbreak detected)
        if regex_dto.action == DTODecision.DENY:
            return InspectionResponse(
                action=janus_pb2.ACTION_DENY,
                mutated_prompt="",
                reason=regex_dto.reason or "Deterministic jailbreak detected"
            )
            
        current_prompt = regex_dto.prompt
        has_mutated = (regex_dto.action == DTODecision.MUTATE)
        
        #  Fast SLM Inspection
        with self.slm_lock:
            slm_dto = self.classifier_light.process(current_prompt)

        if slm_dto.action == DTODecision.DENY:
            return InspectionResponse(
                action=janus_pb2.ACTION_DENY,
                mutated_prompt="",
                reason=slm_dto.reason or "Prompt injection detected"
            )
        # Uncertain (MUTATE, not final) falls through to the planned LLM stage
        
        # If Pass 1 sanitized sensitive PII/secrets, return the mutated prompt
        if has_mutated:
            return InspectionResponse(
                action=janus_pb2.ACTION_MUTATE,
                mutated_prompt=current_prompt,
                reason=regex_dto.reason or "PII/Secrets redacted"
            )
            
        return InspectionResponse(
            action=janus_pb2.ACTION_ALLOW,
            mutated_prompt="",
            reason="Clean"
        )