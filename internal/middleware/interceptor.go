package middleware

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

// PromptInterceptor reads the request body to extract the LLM prompt,
// then restores the body so the downstream handlers can still process it.
func PromptInterceptor(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		bodyBytes, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "Failed to read request body", http.StatusInternalServerError)
			return
		}

		// Restore the body for downstream proxy handlers
		r.Body = io.NopCloser(bytes.NewBuffer(bodyBytes))

		// Extract prompt from OpenAI-compatible JSON payload
		var payload struct {
			Messages []struct {
				Role    string `json:"role"`
				Content string `json:"content"`
			} `json:"messages"`
		}

		if err := json.Unmarshal(bodyBytes, &payload); err == nil {
			if len(payload.Messages) > 0 {
				lastMessage := payload.Messages[len(payload.Messages)-1]
				fmt.Printf("[Interceptor] Intercepted Prompt: %s\n", lastMessage.Content)
			}
		} else {
			fmt.Printf("[Interceptor] Failed to parse JSON: %v\n", err)
		}
		
		next.ServeHTTP(w, r)
	})
}
