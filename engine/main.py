import os
from pathlib import Path
from dotenv import load_dotenv

# Pipeline modules read JANUS_* settings at import time, so load .env first.
# Real environment variables take precedence over the file.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from pb.v1.janus_pb2_grpc import SecurityEngineServicer,add_SecurityEngineServicer_to_server
from pb.v1.janus_pb2 import InspectionRequest, InspectionResponse
import grpc
from concurrent import futures
from services.AI_Service import SecurityService

print("Starting AI service")

security_service=SecurityService()
    
    # gRPC server
server = grpc.server(
    thread_pool = futures.ThreadPoolExecutor(max_workers = int(os.getenv("JANUS_ENGINE_WORKERS", "10")),
                                                thread_name_prefix = "grpc_server"),

    maximum_concurrent_rpcs = int(os.getenv("JANUS_ENGINE_MAX_RPCS", "20")),
    
    )
add_SecurityEngineServicer_to_server(servicer= security_service,
                                     server=server)
    
server.add_insecure_port(os.getenv("JANUS_ENGINE_LISTEN", "[::]:50051"))
server.start()

print("AI gRPC Server has started...")
server.wait_for_termination()

print("AI gRPC Server has stopped...")
