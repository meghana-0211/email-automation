flowchart TD
    subgraph Frontend["Frontend (Next.js + Tailwind)"]
        UI[Dashboard UI]
        Forms[Forms & Controls]
        Preferences[User Preferences]
        Analytics[Analytics Display]
        RT[Real-time Update]
    end

    subgraph Backend["Backend (FastAPI)"]
        API[API Layer]
        Auth[Auth Service]
        Queue[Queue Manager]
        Scheduler[Task Scheduler]
        Generator[Email Generator]
        Monitor[Status Monitor]
        DataProcessor[Analytics Processor]
        Security[Security Layer]
    end

    subgraph Services["External Services"]
        DB[(Firestore)]
        Redis[(Redis)]
        ESP[Email Service Provider]
        LLM[LLM API]
        Sheets[Google Sheets API]
        Observability[Logging & Monitoring]
    end

    UI --> API
    Forms --> API
    Preferences --> API
    API --> Auth
    Auth --> DB
    API --> Security
    Security --> DB
    API --> Queue
    Queue --> Redis
    Queue --> Scheduler
    Scheduler --> Generator
    Generator --> LLM
    Generator --> ESP
    ESP --> Monitor
    Monitor --> DataProcessor
    DataProcessor --> DB
    Monitor -->|Error Logging| DB
    RT -->|WebSocket| API
    Backend --> Observability
    Observability -->|Alerts| Admin
