package main

import (
	"fmt"
	"log"
	"net/http"

	"janus/internal/config"
	"janus/internal/proxy"
)

func main() {
	fmt.Println("Starting Janus AI Gateway...")

	cfg, err := config.LoadConfig("config/janus.yaml")
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}
	fmt.Printf("Config loaded successfully! Port: %d, Debug: %t\n", cfg.Server.Port, cfg.Server.Debug)
	fmt.Printf("Redis Address: %s\n", cfg.Redis.Address)

	fmt.Println("Configured Routes:")
	for _, route := range cfg.Routes {
		fmt.Printf(" - Path: %s, Primary: %s, Fallback: %s, Security Enabled: %t\n",
			route.Path, route.PrimaryProvider, route.FallbackProvider, route.Security.Enabled)
	}

	mux := http.NewServeMux()
	
	// Map configured routes to the proxy handlers
	for _, route := range cfg.Routes {
		providerName := route.PrimaryProvider
		providerCfg, exists := cfg.Providers[providerName]
		if !exists {
			log.Fatalf("Provider %s not found in config for route %s", providerName, route.Path)
		}

		p, err := proxy.NewJanusProxy(providerCfg.BaseURL)
		if err != nil {
			log.Fatalf("Failed to initialize proxy for %s: %v", route.Path, err)
		}

		mux.HandleFunc(route.Path, func(w http.ResponseWriter, r *http.Request) {
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
