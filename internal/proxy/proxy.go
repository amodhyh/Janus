package proxy

import (
	"net/http"
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
	proxy.Rewrite = func(req *http.Request) {

	}

	return proxy, nil
}
