package pbv1

import (
	"context"
	"fmt"
	"log"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

// EngineClient wraps the gRPC connection to the Python Intelligence Engine
// to ensure we only create the TCP connection once (Singleton pattern).
type EngineClient struct {
	client SecurityEngineClient
	conn   *grpc.ClientConn
}

// NewEngineClient establishes a persistent gRPC connection to the target server.
// The caller is responsible for calling Close() when the application shuts down.
func NewEngineClient(target string) (*EngineClient, error) {
	conn, err := grpc.NewClient(
		target,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create gRPC client: %w", err)
	}

	client := NewSecurityEngineClient(conn)

	return &EngineClient{
		client: client,
		conn:   conn,
	}, nil
}

// Close severs the gRPC TCP connection to free OS file descriptors.
func (c *EngineClient) Close() error {
	return c.conn.Close()
}

// InspectPrompt sends the raw user prompt to the Python engine for security analysis.
func (c *EngineClient) InspectPrompt(ctx context.Context, requestID string, prompt string) (*InspectionResponse, error) {
	req := &InspectionRequest{
		RequestId: requestID,
		RawPrompt: prompt,
	}

	// We pass the context directly down to gRPC. If the HTTP request drops, this cancels.
	resp, err := c.client.InspectPrompt(ctx, req)
	if err != nil {
		log.Printf("[EngineClient] RPC failed for req %s: %v", requestID, err)
		return nil, err
	}

	return resp, nil
}
