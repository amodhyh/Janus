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
- **Go gRPC Client**: Implemented persistent client in `internal/pb/v1/client.go`.
- **Python gRPC Server**: Created server in `engine/services/AI_Service.py` with fine-grained concurrency locks (`slm_lock`, `llm_lock`) to protect GPU VRAM.
- **Integration**: Go `EngineClient` successfully injected into HTTP routing via `PromptInterceptorFactory` closure in `internal/middleware/interceptor.go` and wired in `cmd/janus/main.go`.
- **Branch Status**: `feat/grpc-ipc` is functionally complete and ready for merge into `main`.

---

## Next Step Immediately Ahead

### 3. Outbound Stream Interception (Phase 3)
- **Streaming Middleware**: Created `internal/middleware/stream_interceptor.go`.
- **Custom ResponseWriter**: Implemented `JanusHTTPStream` using Go interface embedding to inherit `http.ResponseWriter` methods.
- **SSE Hijacking**: Overrode `Write()` for on-the-fly string replacement (de-redaction) and implemented `http.Flusher` to prevent response buffering.
- **Integration**: Wired the custom `JanusHTTPStream` into the main `interceptor.go` flow.
- **Branch Status**: `feat/streaming-pii-redaction` is functionally complete and ready for merge into `main`.

---

## Next Step Immediately Ahead

- **Current Activity**: Infrastructure foundation is complete. Moving towards live integration testing or intelligence engine development.
- **Next Coding Action**: (Pending decision)
  - Option A: End-to-end testing with live HTTP traffic (Postman/cURL).
  - Option B: Integrate PyTorch/Transformers into the Python Security Engine.
  - Option C: Implement Redis backend for dynamic PII state mapping.
