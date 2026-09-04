package middleware

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

// TODO: Mentor Task 1
// Implement an interceptor that reads the request body to extract the LLM prompt,
// but also restores the body so the ReverseProxy can still forward it.
func PromptInterceptor(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		
		// 1. Read the body
		bodyBytes, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "Failed to read request body", http.StatusInternalServerError)
			return
		}

		// 1b. Since reading the body consumes the stream, we MUST restore it
		// so the reverse proxy down the chain can read it again.
		r.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))

		// 2. Extract the actual "prompt" from the JSON payload.
		// We expect an OpenAI-compatible payload like {"messages": [{"role": "user", "content": "Hello"}]}
		var payload struct {
			Messages []struct {
				Role    string `json:"role"`
				Content string `json:"content"`
			} `json:"messages"`
		}

		if err := json.Unmarshal(bodyBytes, &payload); err == nil {
			// Find the last message (usually what we want to inspect)
			if len(payload.Messages) > 0 {
				lastMessage := payload.Messages[len(payload.Messages)-1]
				fmt.Printf("[Interceptor] Intercepted Prompt: %s\n", lastMessage.Content)
			}
		} else {
			fmt.Printf("[Interceptor] Failed to parse JSON: %v\n", err)
		}
		
		// 3. (Future) Send extracted prompt to Python engine via IPC
		
		// 4. Pass control to the next handler (the proxy)
		next.ServeHTTP(w, r)
	})
}
