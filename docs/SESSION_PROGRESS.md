# Janus Project Session Checkpoint & Progress Log

## Mentor Persona Directives (Active)
- **Role**: Mentor, experienced Product, Backend, and AI Engineer.
- **Guidance Style**: Guide the project and provide knowledge. Do NOT implement code unless explicitly asked.Ask clarifying questions so that the user can understand the technicaliity in depth
- **Decision Making**: Always provide architectural/design options along with their respective trade-offs.

## Current Progress & Status (As of Last Session)

### 1. Proxy Plane (Go) - Completed Features
- **Config Loader**: `internal/config/config.go` successfully parses `config/janus.yaml`.
- **Reverse Proxy**: Implemented in `internal/proxy/proxy.go` using `httputil.NewSingleHostReverseProxy` and standard Go 1.20+ `proxy.Rewrite` hook (`r.SetURL(remote)`, `r.Out.Host = remote.Host`, `r.SetXForwarded()`).
- **Main Server Setup**: `cmd/janus/main.go` iterates over configured routes and binds endpoints to the `ReverseProxy`.
- **Interception Middleware**: 
  - File created at `internal/middleware/interceptor.go`.
  - Implemented `r.Body` reading using `io.ReadAll(r.Body)` and non-destructive body restoration using `r.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))`.
  - Implemented JSON prompt extraction targeting OpenAI-compatible schema (`{"messages": [{"role": "user", "content": "..."}]}`).
  - Wired conditionally into `mux.Handle(route.Path, finalHandler)` based on `route.Security.Enabled`.
  - Removed duplicate config disk-loading from request hot path to avoid latency regressions.

### 2. Infrastructure & IPC Status
- **Dependencies**: Added `requirements.txt` specifying versions for FastAPI, gRPC, Presidio, PyTorch, and Transformers.
- **Protobuf Contract**: `proto/v1/janus.proto` defined with `Action` enum (`ALLOW`, `DENY`, `MUTATE`), `InspectionRequest`, `InspectionResponse`, and `SecurityEngine` service.
- **Client Skeleton**: Added `internal/pb/v1/client.go` ready for Go gRPC client implementation.
- **Branch Status**: Pushed logical commits to `feat/proxy-interceptor-integration`.

---

## Next Step Immediately Ahead

- **Current Activity**: Implementing the IPC Bridge logic (gRPC server and client) using the successfully generated Go and Python protobuf stubs.
- **Next Coding Action**: 
  1. Implement Python gRPC `SecurityEngine` server in `engine/services/AI_Service.py` by inheriting from the generated stubs.
  2. Implement Go gRPC client in `internal/pb/v1/client.go` to connect to the Python service.
  3. Integrate the Go client into the `PromptInterceptor` middleware to dispatch `InspectionRequest`s.
