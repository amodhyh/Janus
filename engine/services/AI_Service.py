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
import time

try:
    from pipeline import RegexStage, DTODecision, get_classifier, get_judge, get_decision_log
except (ImportError, ModuleNotFoundError):
    from engine.pipeline import RegexStage, DTODecision, get_classifier, get_judge, get_decision_log


class SecurityService(SecurityEngineServicer):
    """Manages the tiered prompt security inspection pipeline."""

    def __init__(self, decision_log=None):
        super().__init__()
        print("Initiating Janus Security Pipeline...")
        self.regex_stage = RegexStage()
        self.classifier_light = get_classifier()
        self.classifier_llm = get_judge()
        self.decision_log = decision_log or get_decision_log()
        self.slm_lock = threading.Lock()
        self.llm_lock = threading.Lock()


    def InspectPrompt(self, request: InspectionRequest, context) -> InspectionResponse:
        started = time.perf_counter()
        trace = {"request_id": request.request_id, "gray_area": False, "judge_failed": False}

        response = self._inspect(request.raw_prompt, trace)

        trace["total_ms"] = _ms_since(started)
        self.decision_log.record(
            request.raw_prompt,
            action=janus_pb2.Action.Name(response.action),
            reason=response.reason,
            **trace,
        )
        return response

    def _inspect(self, prompt: str, trace: dict) -> InspectionResponse:
        """Run the pipeline, filling `trace` (decided_by, scores, per-stage latency) as it goes."""

        #  Regex Inspection
        t = time.perf_counter()
        regex_dto = self.regex_stage.process(prompt)
        trace["regex_ms"] = _ms_since(t)

        # Short-circuit fast denial (e.g. hardcoded jailbreak detected)
        if regex_dto.action == DTODecision.DENY:
            trace["decided_by"] = "regex"
            return InspectionResponse(
                action=janus_pb2.ACTION_DENY,
                mutated_prompt="",
                reason=regex_dto.reason or "Deterministic jailbreak detected"
            )

        current_prompt = regex_dto.prompt
        has_mutated = (regex_dto.action == DTODecision.MUTATE)

        #  Fast SLM Inspection
        t = time.perf_counter()
        with self.slm_lock:
            slm_dto = self.classifier_light.process(current_prompt)
        trace["slm_ms"] = _ms_since(t)
        trace["slm_injection_prob"] = slm_dto.score
        trace["decided_by"] = "slm"

        if slm_dto.action == DTODecision.DENY:
            return InspectionResponse(
                action=janus_pb2.ACTION_DENY,
                mutated_prompt="",
                reason=slm_dto.reason or "Prompt injection detected"
            )
        reasons = [regex_dto.reason or "PII/Secrets redacted"] if has_mutated else []

        #  Gray-area prompts (SLM not final) are resolved by the LLM judge
        if not slm_dto.is_final:
            trace["gray_area"] = True
            trace["decided_by"] = "judge"
            trace["judge_model"] = getattr(self.classifier_llm, "model", None)
            t = time.perf_counter()
            with self.llm_lock:
                llm_dto = self.classifier_llm.process(current_prompt)
            trace["judge_ms"] = _ms_since(t)
            trace["judge_verdict"] = llm_dto.action.name
            trace["judge_failed"] = llm_dto.error is not None
            trace["judge_error"] = llm_dto.error

            if llm_dto.action == DTODecision.DENY:
                return InspectionResponse(
                    action=janus_pb2.ACTION_DENY,
                    mutated_prompt="",
                    reason=llm_dto.reason or "Prompt injection detected"
                )
            if llm_dto.action == DTODecision.MUTATE:
                # Judge unsure (or unavailable): forward the guardrail-wrapped prompt
                current_prompt = llm_dto.prompt
                has_mutated = True
                reasons.append(llm_dto.reason)

        # Return the mutated prompt if a stage redacted or wrapped it
        if has_mutated:
            return InspectionResponse(
                action=janus_pb2.ACTION_MUTATE,
                mutated_prompt=current_prompt,
                reason=" | ".join(filter(None, reasons))
            )

        return InspectionResponse(
            action=janus_pb2.ACTION_ALLOW,
            mutated_prompt="",
            reason="Clean"
        )


def _ms_since(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)
