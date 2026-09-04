package proxy

import (
	"net/http/httputil"
	"net/url"
)

// NewJanusProxy creates the engine that routes traffic to the AI provider
func NewJanusProxy(target string) (*httputil.ReverseProxy, error) {
	// 1. Parse the provider URL (e.g., http://localhost:11434)
	remote, err := url.Parse(target)
	if err != nil {
		return nil, err
	}

	// 2. Initialize the reverse proxy engine
	proxy := httputil.NewSingleHostReverseProxy(remote)

	// 3. The "Director" modifies the request before it leaves Janus
	proxy.Rewrite = func(r *httputil.ProxyRequest) {
		// Point the request to the target provider (e.g., Ollama, OpenAI)
		r.SetURL(remote)

		// Set the Host header to match the target provider.
		// Many cloud providers (like OpenAI) will reject requests if the Host header is incorrect.
		r.Out.Host = remote.Host

		// Standard proxy headers
		r.SetXForwarded()
	}

	return proxy, nil
}
