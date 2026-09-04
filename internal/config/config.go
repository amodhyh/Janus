package config

import (
	"os"

	"gopkg.in/yaml.v3"
)

// Config represents the complete configuration structure for Janus.
type Config struct {
	Server    ServerConfig              `yaml:"server"`
	Redis     RedisConfig               `yaml:"redis"`
	Providers map[string]ProviderConfig `yaml:"providers"`
	Routes    []RouteConfig             `yaml:"routes"`
}

// ServerConfig defines general HTTP server options.
type ServerConfig struct {
	Port  int  `yaml:"port"`
	Debug bool `yaml:"debug"`
}

// RedisConfig contains options for connecting to Redis cache/ratelimiter.
type RedisConfig struct {
	Address string `yaml:"address"`
}

// ProviderConfig defines configurations for AI Inference Providers (OpenAI, Gemini, etc.).
type ProviderConfig struct {
	BaseURL string `yaml:"base_url"`
	APIKey  string `yaml:"api_key"`
}

// SecurityConfig governs the settings for Prompt Injection scanning and PII filtering.
type SecurityConfig struct {
	Enabled     bool   `yaml:"enabled"`
	SLMEndpoint string `yaml:"slm_endpoint"`
}

// RateLimitConfig dictates request limits for specific routes.
type RateLimitConfig struct {
	RequestsPerMinute int `yaml:"requests_per_minute"`
}

// RouteConfig maps incoming API endpoints to AI backends and middleware configuration.
type RouteConfig struct {
	Path             string          `yaml:"path"`
	PrimaryProvider  string          `yaml:"primary_provider"`
	FallbackProvider string          `yaml:"fallback_provider"`
	Security         SecurityConfig  `yaml:"security"`
	RateLimit        RateLimitConfig `yaml:"rate_limit"`
}

// LoadConfig reads the YAML file at the specified path and unmarshals its content.
func LoadConfig(path string) (*Config, error) {
	// Read the file from the filesystem.
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	// Unmarshal YAML into our Go Struct.
	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}

	return &cfg, nil
}
