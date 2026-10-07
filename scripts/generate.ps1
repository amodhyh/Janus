Write-Host "Compiling Go Protobuf Stubs..." -ForegroundColor Cyan 
protoc --proto_path=proto --go_out=. --go_opt=module=janus --go-grpc_out=. --go-grpc_opt=module=janus proto/v1/janus.proto       

Write-Host "Compiling Python Protobuf Stubs..." -ForegroundColor Yellow                                                                                
python -m grpc_tools.protoc -Iproto --python_out=engine/pb --pyi_out=engine/pb --grpc_python_out=engine/pb proto/v1/janus.proto                                                                                                                             
                                                                                                                                                         
Write-Host "Done!" -ForegroundColor Green 