package main

import (
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/joho/godotenv"

	"janus/internal/config"
	"janus/internal/middleware"
	pbv1 "janus/internal/pb/v1"
	"janus/internal/proxy"
)

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	// Optional: real environment variables win over .env.
	_ = godotenv.Load()

	fmt.Println("Starting Janus AI Gateway...")

	cfg, err := config.LoadConfig(envOr("JANUS_CONFIG", "config/janus.yaml"))
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
	// AI engine
	engineClient,err := pbv1.NewEngineClient(envOr("JANUS_ENGINE_ADDR", "localhost:50051"))
	if err != nil {                        
        log.Fatalf("Failed to connect to AI Engine: %v", err)                        
    }                                      
    defer engineClient.Close()             
 
	
	
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

		proxyHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if providerCfg.APIKey != "" {
				r.Header.Set("Authorization", "Bearer "+providerCfg.APIKey)
			}

			p.ServeHTTP(w, r)
		})

		var finalHandler http.Handler = proxyHandler
		

		if route.Security.Enabled{
			secureInterceptor := middleware.PromptInterceptorFactory(engineClient)
			finalHandler = secureInterceptor(proxyHandler)
		}

		mux.Handle(route.Path, finalHandler)


	}

	addr := fmt.Sprintf(":%d", cfg.Server.Port)
	fmt.Printf("Server starting on port %s...\n", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}

}
