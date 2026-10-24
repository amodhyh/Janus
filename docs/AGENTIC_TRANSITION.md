# Transition to Agentic Workloads

Status: **planned, not implemented.** This document records why Janus, as built through Pass 4, is not safe to put in front of an agent, and the order in which the gaps should be closed.

## 1. Why agents change the threat model

Janus was designed for a chat-style request: a person types one prompt, and the proxy inspects it. An agent sends something different:

- The request carries the **whole conversation**: system prompt, earlier turns, tool calls and **tool results**.
- Much of that text was not written by the user. It was fetched from web pages, emails, files and APIs. An attacker who controls any of that content can address the model directly (**indirect prompt injection**).
- The model's output is not just text. It contains **tool calls** with arguments (shell commands, SQL, URLs), which cause real side effects.
- One task is dozens of calls, so latency and cost multiply.

## 2. Current gaps

Findings come from reading `internal/middleware/interceptor.go` and the engine pipeline.

| # | Gap | Where | Impact |
|---|-----|-------|--------|
| 1 | Only the last message is inspected (`Messages[len-1]`). | `interceptor.go` | System prompt, earlier turns and tool results are never checked. |
| 2 | Tool results (`role: "tool"`) are not inspected unless they happen to be last. | `interceptor.go` | Indirect injection, the main agent attack, goes through. |
| 3 | `Content` is declared as `string`. Content-part arrays (`[{type, text}, ...]`) and tool-use blocks fail to unmarshal. | `interceptor.go` | Unmarshal error leads to pass-through. **Silent bypass of inspection.** |
| 4 | Any parse failure forwards the request uninspected. | `interceptor.go` | The proxy fails open. |
| 5 | The model's tool calls and arguments are not inspected. Response streaming is not built. | `JanusHTTPStream` | Dangerous actions are not caught on the way out. |
| 6 | `request_id` is hardcoded as `"reqi_id12"`. No session or conversation ID. | `interceptor.go` | Multi-turn attacks cannot be correlated in the decision log. |
| 7 | The classifier truncates at 512 tokens and was trained on user-style injections. | `slm_analyze.py` | Long documents are only partly checked, and embedded injections may be missed. |
| 8 | Gray-area prompts go to the judge (about 1.2 s each) behind a global `llm_lock`. | `AI_Service.py` | Long agent runs with many gray-area tool outputs become slow and serialized. |
| 9 | The interceptor prints full prompts to stdout. | `interceptor.go` | Agent context is large and may contain secrets. |

## 3. Plan

Ordered by value for effort. Each step should land with tests.

### Step 1: Fail closed (small)

- A body that cannot be parsed is rejected (400) instead of forwarded.
- Add a test that a malformed body and a content-part array are never passed through uninspected.

### Step 2: Parse real message formats

- Support OpenAI-style messages with string or content-part-array `content`, `tool_calls` and `role: "tool"`.
- Support the Anthropic Messages format (`content` blocks, `tool_use`, `tool_result`).
- Extract text from each block, and skip or flag non-text parts (images) explicitly rather than ignoring them.

### Step 3: Inspect every message, with its role

- Extend `InspectionRequest` with `role` and `source` (`user`, `system`, `tool`, `assistant`).
- Inspect each new message in the request. Cache verdicts by prompt hash so unchanged history is not rescanned on every turn.
- Treat `tool` content as untrusted by default: stricter classifier thresholds, and a judge prompt written for indirect injection (instructions embedded in data).
- Chunk long content instead of truncating at 512 tokens, and take the maximum injection score across chunks.

### Step 4: Inspect responses (tool calls)

- Implement response inspection in `JanusHTTPStream`, including streamed responses.
- Check tool names against an allowlist and flag dangerous arguments (shell metacharacters, file paths outside a sandbox, unexpected URLs).
- Decide a policy for a denied tool call: block the response, or strip the call.

### Step 5: Sessions and observability

- Generate a real `request_id` and accept a client-supplied session or conversation ID.
- Add `session_id`, `role` and `source` columns to the decision log, so a multi-turn attack appears as a sequence.
- Remove or gate the interceptor's prompt printing (see gap 9).

### Step 6: Performance under agent load

- Replace the global `llm_lock` with a bounded pool, or a queue with a timeout.
- Measure end-to-end overhead on a representative agent trace (not single prompts), and record p50 and p95 in `docs/`.

## 4. Evaluation

Agent support needs its own labelled set, separate from the chat prompts:

- Benign agent traces: a tool result containing a normal web page, file or email.
- Indirect injection samples: the same content with an embedded instruction ("ignore previous instructions and send ...").
- Acceptance targets, to be agreed before step 3: detection rate on indirect injections, false-positive rate on benign tool results, and added latency per agent step.

This set can also serve as the CI accuracy gate planned for the AWS pipeline.

## 5. Out of scope for this transition

- Sandboxing the agent's tools themselves. Janus filters traffic; it does not isolate execution.
- Authentication and per-tenant policy.
- Multimodal content inspection (images, audio), beyond flagging that it was not inspected.

## 6. Open questions

- Which API formats matter first: OpenAI-compatible only, or Anthropic Messages as well?
- Should a denied tool message abort the whole request, or be replaced with a placeholder so the agent can continue?
- How should the classifier's threshold differ for `tool` content, and what false-positive rate is acceptable there?

## 7. Learning guide: implement it yourself

This section is for working through the plan by hand. For each step: what to learn first, where to work, a hint (the idea, not the code), the test to write **before** the change, and how to know you are done. Work in order. Each step builds on the previous one, and each should be its own commit.

General method for every step: write the failing test, make it pass with the smallest change, then run the whole suite (`pytest` in `engine/`, `go test ./...` at the root) before committing.

### Step 1: Fail closed

**Learn first**
- *Fail open vs fail closed*: what a security control does when it cannot decide. Fail open keeps the system available but lets attacks through. Fail closed blocks.
- Go's `encoding/json` errors: `json.Unmarshal` returns an `*json.UnmarshalTypeError` when a field has the wrong type. Read the docs for it.
- `net/http/httptest`: `httptest.NewRecorder` and `httptest.NewRequest` let you test a handler without a server.

**Where**: `internal/middleware/interceptor.go`, the `else` branch after `json.Unmarshal`, and the `len(payload.Messages) > 0` check.

**Hint**: list every path where the request reaches `handler.ServeHTTP` without an engine verdict. There are at least two: the parse error and an empty `messages` list. Decide what each should return, and what status code fits (400 for a malformed body is a reasonable choice).

**Write these tests first**
1. A body that is not JSON returns 400 and the downstream handler is never called.
2. A body where `content` is an array of parts returns a rejection today, because the parser cannot read it. Keep this test; it will change meaning in step 2.
3. A valid chat body still reaches the downstream handler.

**Done when**: no code path forwards a request the engine has not inspected, and you can explain why that matters for a security proxy.

### Step 2: Parse real message formats

**Learn first**
- How the OpenAI chat format represents `content` as either a string or an array of parts, and how `tool_calls` and `role: "tool"` messages look. Read the API reference and capture a real request body from any OpenAI-compatible client.
- The Anthropic Messages format: `content` blocks of type `text`, `tool_use` and `tool_result`.
- In Go, a field that can be two JSON types: `json.RawMessage` (delay decoding), or a custom `UnmarshalJSON` method on a named type.

**Where**: the anonymous struct in `interceptor.go`. Move it into its own file (for example `internal/middleware/messages.go`) so it can be tested alone.

**Hint**: define a `Message` type whose `Content` decodes from either form into one internal shape, such as a slice of text parts. Write a function `ExtractTexts(body []byte) ([]TextPart, error)` and keep HTTP out of it. A non-text part should produce an explicit marker or error instead of being dropped silently.

**Write these tests first** (table-driven, one row per format)
- String content, array content, tool message, assistant message with `tool_calls`, an image part, an empty array, and a wrong type.

**Done when**: the function is covered by a table test and the interceptor uses it instead of the inline struct.

### Step 3: Inspect every message, with its role

**Learn first**
- *Direct vs indirect prompt injection*, and why `tool` content is untrusted. Search for "indirect prompt injection" and read one real example.
- Protobuf evolution: adding a field to `proto/v1/janus.proto` without breaking old clients (new field numbers only). How the repo generates code from the proto, and how to regenerate both the Go and Python files.
- Caching by content hash (SHA-256) so unchanged history is not rescanned. The same idea you used with `lru_cache`, but keyed on the prompt.
- Chunking: splitting text into windows with overlap, and why you take the **maximum** score across chunks rather than the average.

**Where**: `proto/v1/janus.proto`, `interceptor.go`, `engine/services/AI_Service.py`, `engine/pipeline/slm_analyze.py`.

**Hint (design before code)**: decide what the engine does differently for each `source`. A reasonable start: the same pipeline, but `tool` content uses a lower deny threshold and a judge prompt that says "this text is data fetched by an agent; does it contain instructions aimed at the model?". Put the thresholds in a dict keyed by source so they are easy to tune.

**Write these tests first**
- A tool message containing "ignore previous instructions" is denied, wherever it sits in the history.
- An unchanged earlier message is not sent to the engine twice (assert on call count with a fake client).
- A 3,000-token document with an injection at the end is caught, which fails today because of the 512-token truncation.

**Done when**: the decision log records `role`/`source` and you can show the end-of-document injection case being caught.

### Step 4: Inspect responses (tool calls)

**Learn first**
- How the proxy works today. `JanusHTTPStream` wraps the `ResponseWriter`; read it and `httputil.ReverseProxy` (`ModifyResponse`, `FlushInterval`).
- *Server-sent events (SSE)*: how streamed completions arrive as `data:` lines, and how tool-call arguments are streamed in fragments.
- The core trade-off: to inspect arguments you must **buffer** until they are complete, which delays streaming. Decide whether to buffer only responses containing `tool_calls`.

**Where**: `internal/middleware/` (the stream writer), plus a new engine method or reuse of `InspectPrompt` with `source="tool_call"`.

**Hint**: start with non-streaming responses only. Get allowlist checking working on a complete JSON body first, then add streaming as a separate commit.

**Write these tests first**
- A response calling an allowed tool passes.
- A response calling an unknown tool is blocked.
- Arguments containing a path outside the permitted directory are flagged.

**Done when**: a denied tool call produces the behaviour you chose in the open questions (block, or strip).

### Step 5: Sessions and observability

**Learn first**
- Request IDs and correlation IDs (search "correlation id logging").
- UUIDs in Go (`github.com/google/uuid`) and reading a custom header such as `X-Janus-Session`.
- Adding columns to an existing SQLite table: `CREATE TABLE IF NOT EXISTS` does not alter an existing table, so look up `ALTER TABLE ... ADD COLUMN` and how to apply it once at startup.

**Where**: `interceptor.go` (replace `"reqi_id12"`), `engine/pipeline/decision_log.py` (schema and `COLUMNS`), and the interceptor's `fmt.Printf` of prompts.

**Hint**: a migration is just "check which columns exist, add the missing ones". Keep it idempotent.

**Write these tests first**
- Two requests get different IDs.
- A client-supplied session ID appears in the log row.
- A database created by the old schema opens without error and gains the new columns.

**Done when**: you can query one session's rows in order and the prompt text no longer reaches stdout.

### Step 6: Performance under agent load

**Learn first**
- Why a global `threading.Lock` serializes everything, and the alternatives: `threading.Semaphore` for a bounded pool, or a queue with a timeout.
- Percentiles (p50, p95) and why averages hide the slow cases. `engine/bench_slm.py` already shows the pattern.
- Backpressure: what the caller should see when the engine is overloaded (an error, not an indefinite wait).

**Where**: `engine/services/AI_Service.py` (the two locks) and a new benchmark script.

**Hint**: build a fixture that replays a recorded agent trace (say 20 steps, a few of them gray-area) and measure end-to-end time. Change one thing at a time and re-measure.

**Done when**: you have before/after p50 and p95 numbers recorded in `docs/`, and a judge timeout cannot stall unrelated requests.

### Suggested reading order

1. Fail open vs fail closed, and OWASP's LLM01 Prompt Injection entry.
2. One indirect-injection write-up (search for "indirect prompt injection" and the original research paper).
3. The Go docs for `encoding/json`, `net/http/httptest` and `httputil.ReverseProxy`.
4. The protobuf guide on updating a message type.
5. Anything on SSE if you reach step 4.

When you get stuck on a step, bring the failing test and what you tried. That is the fastest way to get a useful hint without being handed the solution.
