```mermaid
flowchart TD
    subgraph Frontend["Frontend (Next.js + Tailwind)"]
        UI[Dashboard UI]
        Forms[Forms & Controls]
        Analytics[Analytics Display]
        RT[Real-time Updates]
    end

    subgraph Backend["Backend (FastAPI)"]
        API[API Layer]
        Auth[Auth Service]
        Queue[Queue Manager]
        Scheduler[Task Scheduler]
        Generator[Email Generator]
        Monitor[Status Monitor]
    end

    subgraph Services["External Services"]
        DB[(PostgreSQL)]
        Redis[(Redis)]
        ESP[Email Service Provider]
        LLM[LLM API]
        Sheets[Google Sheets API]
    end

    UI --> API
    Forms --> API
    API --> Auth
    Auth --> DB
    API --> Queue
    Queue --> Redis
    Queue --> Scheduler
    Scheduler --> Generator
    Generator --> LLM
    Generator --> ESP
    ESP --> Monitor
    Monitor --> DB
    Monitor --> RT
    API --> Sheets
