# Janus: High-Performance AI Security Gateway

Janus is an ultra-low latency reverse proxy designed to secure Large Language Model (LLM) workflows. It acts as a specialized security perimeter positioned between client applications and AI inference providers (such as Ollama, OpenAI, or Anthropic).

Janus provides real-time Prompt Injection Defense and streaming Personally Identifiable Information (PII) redaction while optimizing for minimal throughput overhead.

## Architectural Diagram

The following diagram illustrates the hybrid architecture of Janus, distinguishing between the high-concurrency data path and the semantic analysis engine.

```mermaid
graph LR
    classDef boundary fill:#f9f,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;
    classDef primary fill:#e1f5fe,stroke:#0277bd,stroke-width:2px;
    classDef secondary fill:#fff3e0,stroke:#ef6c00,stroke-width:2px;

    Client(Application Client)
    
    subgraph JanusGateway["Janus Gateway Boundary"]
        direction TB
        
        Proxy[Go Proxy Plane <br/> Networking, Buffering, Routing]:::primary
        Engine[Python Security Engine <br/> SLM-based Inspection, Semantic Analysis]:::secondary
        
        Proxy <-->|High-Speed IPC / gRPC <br/> Protocol Buffers| Engine
    end
    
    Provider(AI Provider <br/> Ollama / Cloud API)
    
    %% Request Flow
    Client -->|1. Request <br/> Unsecured Prompt| Proxy
    Proxy -->|2. Secure Request <br/> Redacted Prompt| Provider
    
    %% Response Flow
    Provider -->|3. Response <br/> Stream| Proxy
    Proxy -->|4. Secure Response <br/> Redacted Stream| Client

    %% Highlighting components
    linkStyle 0,1,2,3 stroke-width:2px,fill:none,stroke:black;


```
