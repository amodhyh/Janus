from pb.v1.janus_pb2_grpc import SecurityEngineServicer
from pb.v1.janus_pb2 import InspectionRequest, InspectionResponse
import pb.v1.janus_pb2 as janus_pb2
import grpc
from concurrent import futures



class SecurityService(SecurityEngineServicer):
    ''' Manage the sending and retrieving the prompt to the AI models'''
    
    def __init__(self):
        super().__init__()
        print("Initiating Janus Models")
        self.classifier_light = None
        self.classifier_llm = None
        

    def InspectPrompt(self, request:InspectionRequest, context) -> InspectionResponse:
        
        prompt = request.raw_prompt
        
        # Placeholder till AI model connection
        is_injected = False
        
        if is_injected:
            return InspectionResponse(action=janus_pb2.ACTION_DENY , 
                                      mutated_prompt="Test Prompt", 
                                      reason="Prompt Injection detected")
        else:
            return InspectionResponse(action=janus_pb2.ACTION_ALLOW,
                                      mutated_prompt="",
                                      reason="Clean")