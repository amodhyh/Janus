package main

import (
	"fmt"
	"log"
	"net/http"

	"janus/internal/config"
	"janus/internal/proxy"
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
	
	// Map configured routes to the proxy
	for _, route := range cfg.Routes {
		providerName := route.PrimaryProvider
		providerCfg, exists := cfg.Providers[providerName]
		if !exists {
			log.Fatalf("Provider %s not found in config for route %s", providerName, route.Path)
		}

		// Initialize the proxy engine for this route's target provider
		p, err := proxy.NewJanusProxy(providerCfg.BaseURL)
		if err != nil {
			log.Fatalf("Failed to initialize proxy for %s: %v", route.Path, err)
		}

		// Register the proxy to handle this path
		// We wrap it in a handler function to inject the API key if needed
		mux.HandleFunc(route.Path, func(w http.ResponseWriter, r *http.Request) {
			// Forward the provider's API key in the Authorization header
			if providerCfg.APIKey != "" {
				r.Header.Set("Authorization", "Bearer "+providerCfg.APIKey)
			}
			p.ServeHTTP(w, r)
		})
	}

	addr := fmt.Sprintf(":%d", cfg.Server.Port)
	fmt.Printf("Server starting on port %s...\n", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}

}
