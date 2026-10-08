from pb.v1.janus_pb2_grpc import SecurityEngineServicer,add_SecurityEngineServicer_to_server
from pb.v1.janus_pb2 import InspectionRequest, InspectionResponse
import grpc
from concurrent import futures
from services.AI_Service import SecurityService

print("Starting AI service")

security_service=SecurityService()
    
    # gRPC server
server = grpc.server(
    thread_pool = futures.ThreadPoolExecutor(max_workers = 10, 
                                                thread_name_prefix = "grpc_server"),
    
    maximum_concurrent_rpcs = 20,
    
    )
add_SecurityEngineServicer_to_server(servicer= security_service,
                                     server=server)
    
server.add_insecure_port('[::]:50051')
server.start()

print("AI gRPC Server has started...")
server.wait_for_termination()

print("AI gRPC Server has stopped...")
