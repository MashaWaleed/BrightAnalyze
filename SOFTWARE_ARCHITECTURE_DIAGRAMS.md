# BrightAnalyze Software Architecture Diagrams

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph "Application Layer"
        A[Main Window<br/>CANAnalyzerMainWindow] --> B[Menu Bar<br/>EnhancedMenuBar]
        A --> C[Toolbar<br/>ModernToolbar]
        A --> D[Left Sidebar<br/>AdvancedLeftSidebar]
        A --> E[Message Log<br/>ProfessionalMessageLog]
        A --> F[Right Sidebar<br/>FeatureRichRightSidebar]
        A --> G[Status Bar<br/>IntelligentStatusBar]
    end
    
    subgraph "UI Components"
        D --> H[DBC Manager<br/>DBCManager]
        F --> I[Diagnostics Panel<br/>DiagnosticsPanel]
        F --> J[Signal Plotter<br/>SignalPlotter]
        F --> K[Scripting Console<br/>ScriptingConsole]
        A --> L[Workspace Manager<br/>WorkspaceManager]
        A --> M[Style Manager<br/>ModernStyleManager]
    end
    
    subgraph "Backend Services"
        N[CAN Bus Manager<br/>CANBusManager] --> O[Message Processing<br/>Queue + Threading]
        P[UDS Backend<br/>SimpleUDSBackend] --> Q[ISOTP Stack<br/>Multi-threaded]
        N --> R[Hardware Interfaces<br/>CANable, SocketCAN, Vector]
    end
    
    subgraph "Data Layer"
        S[DBC Database<br/>Signal Definitions]
        T[Message Storage<br/>Circular Buffers]
        U[Configuration<br/>JSON Settings]
        V[Workspace Files<br/>Session Data]
    end
    
    %% Connections
    D -.-> N
    E -.-> N
    I -.-> P
    J -.-> N
    K -.-> N
    K -.-> P
    
    N --> T
    H --> S
    L --> V
    A --> U
    
    %% Hardware
    R --> W[Physical CAN Bus<br/>Automotive Network]
    
    %% Styling
    classDef ui fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef backend fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef data fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef hardware fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    
    class A,B,C,D,E,F,G,H,I,J,K,L,M ui
    class N,O,P,Q backend
    class S,T,U,V data
    class R,W hardware
```

## 2. Threading Architecture

```mermaid
graph TB
    subgraph "Main Thread (UI)"
        A[Qt Main Thread<br/>GUI Updates] --> B[Signal/Slot System<br/>Thread-Safe Communication]
    end
    
    subgraph "CAN Reception Thread"
        C[CAN Receive Loop<br/>_async_recv_loop] --> D[Message Queue<br/>thread-safe queue.Queue]
        D --> E[Message Processing Thread<br/>_process_messages]
    end
    
    subgraph "Message Processing Thread"
        E --> F[ISOTP Processing<br/>_process_isotp_messages]
        E --> G[Signal Emission<br/>message_received.emit]
    end
    
    subgraph "UDS Processing Thread"
        H[UDS Message Queue<br/>Priority Queue] --> I[UDS Processing<br/>_process_uds_messages]
        I --> J[Service Execution<br/>_execute_uds_request_internal]
    end
    
    subgraph "Background Workers"
        K[Signal Plotting Thread<br/>Real-time Updates]
        L[DBC Processing Thread<br/>Background Parsing]
        M[File I/O Thread<br/>Workspace Operations]
    end
    
    %% Data Flow
    C --> D
    D --> E
    E --> B
    B --> A
    
    A --> H
    H --> I
    I --> B
    
    E --> K
    E --> L
    A --> M
    
    %% Thread Communication
    G -.-> A
    J -.-> A
    K -.-> A
    L -.-> A
    M -.-> A
    
    %% Styling
    classDef mainThread fill:#e3f2fd,stroke:#1976d2,stroke-width:3px
    classDef canThread fill:#f1f8e9,stroke:#689f38,stroke-width:2px
    classDef udsThread fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef workerThread fill:#fff8e1,stroke:#ffa000,stroke-width:2px
    classDef queue fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    
    class A,B mainThread
    class C,E,F,G canThread
    class H,I,J udsThread
    class K,L,M workerThread
    class D,H queue
```

## 3. CAN Message Flow Sequence

```mermaid
sequenceDiagram
    participant HW as CAN Hardware
    participant CM as CANBusManager
    participant Q as Message Queue
    participant PT as Processing Thread
    participant UI as UI Components
    participant DBC as DBC Manager
    participant SP as Signal Plotter
    
    Note over HW,SP: Real-time Message Processing (1000+ msg/sec)
    
    HW->>CM: CAN Frame Received
    CM->>CM: _async_recv_loop()
    CM->>CM: Parse frame data
    CM->>Q: queue.put_nowait(msg_info)
    
    loop Background Processing
        PT->>Q: queue.get(timeout=0.1)
        PT->>PT: _process_isotp_messages()
        PT->>UI: message_received.emit(msg_info)
    end
    
    UI->>DBC: Check for signal definitions
    DBC->>DBC: Parse message signals
    DBC->>UI: Return decoded signals
    
    UI->>SP: Update real-time plots
    SP->>SP: Add data points (60fps)
    
    Note over CM,UI: Thread-safe communication via Qt signals
```

## 4. UDS Diagnostic Sequence

```mermaid
sequenceDiagram
    participant User as User Interface
    participant DP as Diagnostics Panel
    participant UDS as UDS Backend
    participant Q as UDS Queue
    participant PT as Processing Thread
    participant ISOTP as ISOTP Stack
    participant ECU as Target ECU
    
    User->>DP: Request UDS Service
    DP->>UDS: execute_uds_request()
    UDS->>Q: Add to priority queue
    
    PT->>Q: Dequeue request
    PT->>PT: _execute_uds_request_internal()
    
    alt Security Access Required
        PT->>ECU: Request Seed (0x27)
        ECU->>PT: Seed Response
        PT->>PT: Calculate Key (Algorithm)
        PT->>ECU: Send Key (0x27)
        ECU->>PT: Positive Response
    end
    
    PT->>ISOTP: Create ISOTP connection
    ISOTP->>ECU: Send UDS Request
    ECU->>ISOTP: UDS Response
    ISOTP->>PT: Response received
    
    PT->>UDS: Process response
    UDS->>DP: uds_response.emit()
    DP->>User: Display results
```

## 5. Component Interaction Architecture

```mermaid
graph LR
    subgraph "Frontend Layer"
        A[Main Window] --> B[Left Sidebar]
        A --> C[Message Log]
        A --> D[Right Sidebar]
        B --> E[TX Message Editor]
        C --> F[Message Table]
        D --> G[Diagnostics Panel]
        D --> H[Signal Plotter]
    end
    
    subgraph "Service Layer"
        I[CAN Bus Manager] --> J[Message Processing]
        K[UDS Backend] --> L[Security Access]
        M[DBC Manager] --> N[Signal Decoding]
        O[Workspace Manager] --> P[Session Management]
    end
    
    subgraph "Data Access Layer"
        Q[(Message Buffer)] --> R[Circular Buffer]
        S[(DBC Database)] --> T[cantools]
        U[(Configuration)] --> V[QSettings]
        W[(Workspace Data)] --> X[JSON Files]
    end
    
    %% Component Interactions
    E --> I
    F --> I
    G --> K
    H --> I
    
    I --> Q
    K --> I
    N --> S
    P --> W
    
    %% Data Flow
    J --> F
    L --> G
    N --> H
    
    classDef frontend fill:#e8eaf6,stroke:#3f51b5,stroke-width:2px
    classDef service fill:#e0f2f1,stroke:#00695c,stroke-width:2px
    classDef data fill:#fafafa,stroke:#616161,stroke-width:2px
    
    class A,B,C,D,E,F,G,H frontend
    class I,J,K,L,M,N,O,P service
    class Q,R,S,T,U,V,W,X data
```

## 6. Memory Management & Performance Architecture

```mermaid
graph TB
    subgraph "Memory Management"
        A[Circular Message Buffer<br/>Max 10,000 messages] --> B[Automatic Cleanup<br/>FIFO Policy]
        C[Signal Value Cache<br/>LRU Eviction] --> D[Memory Pool<br/>Reusable Objects]
        E[DBC Symbol Table<br/>Lazy Loading] --> F[Garbage Collection<br/>Weak References]
    end
    
    subgraph "Performance Optimization"
        G[Lock-Free Queues<br/>Producer-Consumer] --> H[Batch Processing<br/>Message Chunks]
        I[Async Signal Decoding<br/>Background Thread] --> J[60fps UI Updates<br/>Rate Limited]
        K[Connection Pooling<br/>ISOTP Stacks] --> L[Resource Reuse<br/>Object Pools]
    end
    
    subgraph "Threading Model"
        M[Main UI Thread<br/>16ms Response] --> N[CAN RX Thread<br/>High Priority]
        O[Message Processing<br/>Normal Priority] --> P[UDS Processing<br/>Background]
        Q[Signal Plotting<br/>Low Priority] --> R[File I/O<br/>Lowest Priority]
    end
    
    %% Performance Metrics
    N -.-> S[1000+ msg/sec<br/>Processing Rate]
    M -.-> T[<16ms UI<br/>Response Time]
    Q -.-> U[60fps Plot<br/>Update Rate]
    
    classDef memory fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef performance fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef threading fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    classDef metrics fill:#fce4ec,stroke:#e91e63,stroke-width:2px
    
    class A,B,C,D,E,F memory
    class G,H,I,J,K,L performance
    class M,N,O,P,Q,R threading
    class S,T,U metrics
```

## 7. Security & UDS Service Architecture

```mermaid
graph TB
    subgraph "UDS Service Layer"
        A[Session Control 0x10] --> B[Default Session]
        A --> C[Programming Session]
        A --> D[Extended Session]
        
        E[Security Access 0x27] --> F[Seed Request]
        E --> G[Key Response]
        E --> H[Algorithm Engine]
        
        I[Read Data 0x22] --> J[ECU Information]
        I --> K[Live Data Values]
        
        L[Write Data 0x2E] --> M[Configuration Data]
        L --> N[Calibration Values]
        
        O[Routine Control 0x31] --> P[Start Routine]
        O --> Q[Stop Routine]
        O --> R[Request Results]
    end
    
    subgraph "Security Algorithms"
        H --> S[XOR Algorithm]
        H --> T[Addition Algorithm]
        H --> U[CRC16 Algorithm]
        H --> V[Custom DLL Integration]
    end
    
    subgraph "ISOTP Layer"
        W[Single Frame SF] --> X[≤7 bytes]
        Y[First Frame FF] --> Z[>7 bytes start]
        AA[Consecutive Frame CF] --> BB[Continuation data]
        CC[Flow Control FC] --> DD[Buffer management]
    end
    
    subgraph "Error Handling"
        EE[Negative Response 0x7F] --> FF[Service Not Supported]
        EE --> GG[Conditions Not Correct]
        EE --> HH[Request Out of Range]
        EE --> II[Security Access Denied]
    end
    
    %% Service Flow
    A --> E
    E --> I
    E --> L
    E --> O
    
    %% ISOTP Integration
    A -.-> W
    I -.-> Y
    L -.-> Y
    O -.-> Y
    
    %% Error Paths
    E --> EE
    I --> EE
    L --> EE
    O --> EE
    
    classDef service fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef security fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef isotp fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef error fill:#ffebee,stroke:#c62828,stroke-width:2px
    
    class A,B,C,D,I,J,K,L,M,N,O,P,Q,R service
    class E,F,G,H,S,T,U,V security
    class W,X,Y,Z,AA,BB,CC,DD isotp
    class EE,FF,GG,HH,II error
```

## 8. Data Flow Architecture

```mermaid
flowchart TD
    subgraph "Input Sources"
        A[CAN Hardware] --> B[Message Reception]
        C[User Input] --> D[Message Transmission]
        E[DBC Files] --> F[Signal Definitions]
        G[Workspace Files] --> H[Configuration Data]
    end
    
    subgraph "Processing Pipeline"
        B --> I[Message Parsing]
        I --> J[Signal Decoding]
        J --> K[Data Validation]
        K --> L[Storage/Display]
        
        D --> M[Message Formatting]
        M --> N[Hardware Transmission]
        
        F --> O[Database Parsing]
        O --> P[Symbol Table Creation]
        
        H --> Q[Settings Loading]
        Q --> R[UI Configuration]
    end
    
    subgraph "Output Destinations"
        L --> S[Message Log Table]
        L --> T[Signal Plotter]
        L --> U[Statistics Display]
        
        N --> V[CAN Bus Network]
        
        P --> W[Signal Decoder]
        P --> X[Message Editor]
        
        R --> Y[UI Components]
        R --> Z[Theme Settings]
    end
    
    classDef input fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef process fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    classDef output fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    
    class A,C,E,G input
    class B,D,F,H,I,J,K,L,M,N,O,P,Q,R process
    class S,T,U,V,W,X,Y,Z output
```

These diagrams provide a comprehensive view of BrightAnalyze's software architecture, showing:

1. **High-level component organization** and relationships
2. **Threading architecture** with performance optimizations
3. **Message processing flow** with real-time capabilities
4. **UDS diagnostic sequences** with security access
5. **Component interactions** across layers
6. **Memory management** and performance features
7. **Security and UDS service** implementation
8. **Data flow** from input to output

The architecture demonstrates the sophisticated threading model that enables 1000+ messages/second processing while maintaining responsive UI performance.
