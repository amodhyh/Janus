package main

import (
	"fmt"
	"log"
	"net/http"

	"janus/internal/config"
)

func Dummy(w http.ResponseWriter, r *http.Request) {

	jsonResponse := []byte(`{"message":"Server is Running"}`)

	// Prepare response headers via the Interface
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	// 4. Directly stream the payload into the network buffer
	_, _ = w.Write(jsonResponse)

}
func main() {
	fmt.Println("Starting Janus AI Gateway...")

	// 1. Load the configuration file.
	// Since we run the binary from the root directory, the path "config/janus.yaml" is correct.
	cfg, err := config.LoadConfig("config/janus.yaml")
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}

	// 2. Print out some loaded settings to confirm it works.
	fmt.Printf("Config loaded successfully! Port: %d, Debug: %t\n", cfg.Server.Port, cfg.Server.Debug)
	fmt.Printf("Redis Address: %s\n", cfg.Redis.Address)

	fmt.Println("Configured Routes:")
	for _, route := range cfg.Routes {
		fmt.Printf(" - Path: %s, Primary: %s, Fallback: %s, Security Enabled: %t\n",
			route.Path, route.PrimaryProvider, route.FallbackProvider, route.Security.Enabled)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /v1/chat/completions", Dummy)

	addr := fmt.Sprintf(":%d", cfg.Server.Port)
	fmt.Printf("Server starting on port %s...\n", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}

}
