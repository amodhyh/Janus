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

## 3. Outbound Stream Interception & E2E Testing (Phase 3)
- **Streaming Middleware**: Created `internal/middleware/stream_interceptor.go`.
- **Custom ResponseWriter**: Implemented `JanusHTTPStream` using Go interface embedding to inherit `http.ResponseWriter` methods.
- **SSE Hijacking**: Overrode `Write()` for on-the-fly string replacement (de-redaction) and implemented `http.Flusher` to prevent response buffering.
- **Integration**: Wired the custom `JanusHTTPStream` into the main `interceptor.go` flow.
- **E2E Testing (Walking Skeleton)**: Successfully proved the full Go -> gRPC -> Python -> Go -> External Provider -> Client pipeline using Postman.
- **Branch Status**: `feat/streaming-pii-redaction` and E2E core routing bugfixes have been merged into `main`.

---

## Next Step Immediately Ahead

- **Current Activity**: Pass 1 (Deterministic/Regex Inspection) fully wired, integrated with Go proxy plane, and verified end-to-end via automated tests.
- **Completed in Pass 1 Milestone**:
  - Implemented `RegexStage` in `engine/pipeline/regex_analyze.py` adhering to `PipelineStage` protocol.
  - Added pre-compiled patterns for RFC 5322 Email, Credit Cards (Visa, MC, Amex, Discover with delimiters), SSN, and high-entropy Secrets (OpenAI, AWS, GitHub, PEM keys).
  - Added $O(1)$-space, zero-allocation Luhn algorithm check to eliminate credit card false positives on order IDs.
  - Implemented sub-millisecond short-circuit rejection (`DTODecision.DENY`, `is_final=True`) for hardcoded jailbreaks.
  - Wired `RegexStage` into `SecurityService.InspectPrompt` in `engine/services/AI_Service.py`, mapping `PipelineDTO` decisions to gRPC `InspectionResponse`.
  - Updated Go proxy middleware in `internal/middleware/interceptor.go` to handle `Action_ACTION_MUTATE` (rewriting `r.Body` and `Content-Length` headers with sanitized prompts).
  - Resolved root vs engine relative/absolute module imports across polyglot boundaries.
  - Fixed silent `.gitignore` wildcard bug that masked python files from tracking.
  - Created automated Go integration test `internal/pb/v1/client_test.go` proving full Go -> gRPC -> Python Pass 1 pipeline passes cleanly.
- **Branch Status**:
  - `feat/intelligence-engine` (Pass 1 Milestone) is complete, tested, and ready for commit and merge to `main`.
- **Next Step Immediately Ahead**:
  - Merge `feat/intelligence-engine` into `main`.
  - Create feature branch for Pass 2 (Fast SLM sequence classification / DeBERTa / Presidio PII).


