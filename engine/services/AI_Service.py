from pb.v1.janus_pb2_grpc import SecurityEngineServicer
from pb.v1.janus_pb2 import InspectionRequest, InspectionResponse
import pb.v1.janus_pb2 as janus_pb2
import grpc
from concurrent import futures
import threading



class SecurityService(SecurityEngineServicer):
    ''' Manage the sending and retrieving the prompt to the AI models'''
    
    def __init__(self):
        super().__init__()
        print("Initiating Janus Models")
        self.classifier_light = None
        self.classifier_llm = None
        self.slm_lock=threading.Lock()
        self.llm_lock=threading.Lock()
        

    def InspectPrompt(self, request:InspectionRequest, context) -> InspectionResponse:
        prompt = request.raw_prompt
        
        with self.slm_lock:
            # Placeholder for the SLM result
            slm_result="clean"
            
        if slm_result=="gray":
            with self.llm_lock:

            # Placeholder for the LLM result
                is_injected = False
        
                if is_injected:
                    return InspectionResponse(action=janus_pb2.ACTION_DENY , 
                                        mutated_prompt="Test Prompt", 
                                        reason="Prompt Injection detected")
                else:
                    return InspectionResponse(action=janus_pb2.ACTION_ALLOW,
                                        mutated_prompt="",
                                        reason="Clean")
        else:
            return InspectionResponse(action=janus_pb2.ACTION_ALLOW,
                                mutated_prompt="",
                            reason="Clean")