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

	// Initialize the reverse proxy engine
	// * used the modern ReverseProxy struct to overcome the rewrite issue
	proxy := &httputil.ReverseProxy{
		Rewrite: func(pr *httputil.ProxyRequest) {
			pr.SetURL(remote)
			pr.Out.Host=remote.Host
			pr.SetXForwarded()
		},

	}

	return proxy, nil
}
