package middleware

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	pbv1 "janus/internal/pb/v1"
	"net/http"
)

// PromptInterceptor reads the request body to extract the LLM prompt,
// then restores the body so the downstream handlers can still process it.
// Factory function for the initialising the engine client with the middleware
func PromptInterceptorFactory(client *pbv1.EngineClient) func(http.Handler) http.Handler {

	return func(handler http.Handler) http.Handler {
		return http.HandlerFunc(
			func(w http.ResponseWriter, r *http.Request) {
				fmt.Println("Listenining for Requests...")
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
						resp,err:=client.InspectPrompt(r.Context(),"reqi_id12", lastMessage.Content)
						if err!=nil{
							http.Error(w, "AI Security Engine Unavailable", http.StatusServiceUnavailable)                
        					return        

						}
						if resp.Action==pbv1.Action_ACTION_DENY{
							http.Error(w,resp.Reason,http.StatusForbidden)
							return
						}

					}
				} else {
					fmt.Printf("[Interceptor] Failed to parse JSON: %v\n", err)
				}

				handler.ServeHTTP(w, r)

			})

	}
}
