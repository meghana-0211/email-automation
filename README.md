# Email Automation Dashboard

A sophisticated email automation system featuring LLM-powered personalization, real-time analytics, and advanced campaign management capabilities.

![Dashboard Demo](demo-dashboard.gif)

## 📑 Table of Contents
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [API Documentation](#-api-documentation)
- [Development](#-development)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Security](#-security)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Key Features

### Email Management
- **Smart Personalization**: LLM-powered content generation with custom prompts
- **Template System**: Dynamic field replacement with validation
- **Batch Processing**: Efficient handling of large email campaigns
- **Multi-ESP Support**: SendGrid, Amazon SES, and Mailgun integration

### Data Handling
- **Google Sheets Integration**: Real-time sync with spreadsheet data
- **CSV Import**: Bulk data import with validation
- **Column Mapping**: Intelligent field mapping and validation
- **Data Preprocessing**: Automatic email validation and formatting

### Analytics & Tracking
- **Real-time Dashboard**: Live campaign performance metrics
- **Advanced Analytics**: Conversion tracking and engagement metrics
- **Custom Reports**: Exportable reports in multiple formats
- **Webhook Integration**: Real-time delivery status updates

### Campaign Management
- **Scheduling System**: Timezone-aware scheduling
- **Smart Throttling**: Automatic rate limiting based on ESP constraints
- **Queue Management**: Priority queuing with retry mechanisms
- **Error Handling**: Comprehensive error tracking and reporting

## 🏗 System Architecture

### Component Overview
```mermaid
graph TD
    A[Frontend - Next.js] -->|WebSocket| B[Backend - FastAPI]
    A -->|REST API| B
    B -->|Queue Jobs| C[Redis Queue]
    B -->|Store Data| D[PostgreSQL]
    B -->|Send Emails| E[ESP Service]
    B -->|Cache| F[Redis Cache]
    B -->|Analytics| G[Analytics Service]
    H[Scheduler] -->|Triggers| C
    I[Worker Processes] -->|Process| C
```

### Data Flow
1. **Authentication Flow**
   - OAuth2 with JWT tokens
   - Redis session storage
   - Rate limiting middleware

2. **Email Processing Flow**
   ```
   User Request → API Gateway → Queue Manager → Worker Processes → ESP
        ↓                           ↓                ↓
   Validation           Status Updates        Error Handling
   ```

3. **Analytics Flow**
   ```
   ESP Webhooks → Event Processor → Analytics Service → Real-time Updates
                        ↓
                  Database Storage
   ```

## 🚀 Installation

### Prerequisites
- Python 3.9+
- Node.js 16+
- Firebase
- Redis 6+
- Docker & Docker Compose (optional)

### Local Development Setup

1. **Clone and Configure**
   ```bash
   git clone https://github.com/yourusername/email-automation
   cd email-automation
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   
   # Install dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   
   # Setup pre-commit hooks
   pre-commit install
   ```

2. **Database Setup**
   ```bash
   # Start PostgreSQL and Redis
   docker-compose up -d postgres redis
   
   # Run migrations
   alembic upgrade head
   
   # Seed initial data (optional)
   python scripts/seed_data.py
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   
   # Setup environment
   cp .env.example .env.local
   # Edit .env.local with your settings
   ```

4. **Start Development Servers**
   ```bash
   # Terminal 1: Backend
   cd backend
   uvicorn main:app --reload --port 8000
   
   # Terminal 2: Frontend
   cd frontend
   npm run dev
   
   # Terminal 3: Worker
   cd backend
   rq worker email-queue
   ```

### Docker Setup
```bash
# Build and start all services
docker-compose up --build

# Start specific services
docker-compose up postgres redis worker
```

## ⚙️ Configuration

### Environment Variables

#### Backend (.env)
```ini
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0

# Authentication
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email Service Providers
SENDGRID_API_KEY=your-sendgrid-key
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
MAILGUN_API_KEY=your-mailgun-key

# External Services
GOOGLE_SHEETS_CREDENTIALS=path/to/credentials.json
LLM_API_KEY=your-llm-api-key

# Application Settings
APP_ENV=development
DEBUG=true
CORS_ORIGINS=http://localhost:3000
RATE_LIMIT_PER_MINUTE=60
```

#### Frontend (.env.local)
```ini
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### ESP Configuration

#### SendGrid Setup
```python
# backend/config/sendgrid.py
from sendgrid import SendGridAPIClient

sg = SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))

def configure_webhooks():
    sg.client.user.webhooks.event.settings.patch(
        request_body={
            "enabled": True,
            "url": "https://your-domain.com/api/webhooks/sendgrid",
            "group_resubscribe": True,
            "delivered": True,
            "spam_report": True,
            "bounce": True,
            "open": True,
            "click": True,
        }
    )
```

#### Amazon SES Setup
```python
# backend/config/ses.py
import boto3

ses = boto3.client(
    'ses',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name='us-east-1'
)

def configure_sns():
    # Set up SNS topic for bounces and complaints
    # Implementation details...
```

## 📝 Usage Guide

### Authentication

```typescript
// frontend/lib/auth.ts
async function login(email: string, password: string) {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  
  if (!response.ok) {
    throw new Error('Authentication failed');
  }
  
  const data = await response.json();
  return data.token;
}
```

### Campaign Creation

```typescript
// frontend/lib/campaign.ts
interface CampaignData {
  templateId: string;
  recipients: string[];
  scheduledTime?: Date;
  throttleRate?: number;
}

async function createCampaign(data: CampaignData) {
  // Implementation details...
}
```

### WebSocket Integration

```typescript
// frontend/lib/websocket.ts
function useWebSocket(onMessage: (data: any) => void) {
  useEffect(() => {
    const ws = new WebSocket(process.env.NEXT_PUBLIC_WS_URL);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };
    
    return () => ws.close();
  }, [onMessage]);
}
```

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_email_service.py

# Run with coverage
pytest --cov=app tests/
```

### Frontend Tests
```bash
# Run Jest tests
npm test

# Run with coverage
npm test -- --coverage

# Run E2E tests
npm run cypress:open
```

### Load Testing
```bash
# Using k6
k6 run load_tests/email_campaign.js
```

## 📦 Deployment

### Production Checklist
1. **Environment Configuration**
   - Set production environment variables
   - Configure SSL certificates
   - Set up monitoring services

2. **Database Setup**
   - Run production migrations
   - Set up backup strategy
   - Configure connection pooling

3. **Scaling Configuration**
   - Configure auto-scaling rules
   - Set up load balancers
   - Configure CDN

### Deployment Commands
```bash
# Build production assets
cd frontend && npm run build

# Start production server
cd backend && gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 🔐 Security

### Security Features
- **Authentication**: JWT with refresh tokens
- **Authorization**: Role-based access control
- **Rate Limiting**: Per-user and per-IP limits
- **Input Validation**: Request validation using Pydantic
- **XSS Protection**: Content Security Policy headers
- **CSRF Protection**: Double submit cookie pattern
- **SQL Injection Prevention**: Parameterized queries
- **Security Headers**: HSTS, X-Frame-Options, etc.

### Security Best Practices
1. Regular dependency updates
2. Security audit logging
3. Regular penetration testing
4. Secure session handling
5. Data encryption at rest

## 🔧 Troubleshooting

### Common Issues

1. **Redis Connection Issues**
   ```bash
   # Check Redis connection
   redis-cli ping
   
   # Clear Redis cache
   redis-cli FLUSHALL
   ```

2. **Database Migration Issues**
   ```bash
   # Reset migrations
   alembic downgrade base
   
   # Recreate migrations
   alembic revision --autogenerate -m "reset"
   ```

3. **Worker Process Issues**
   ```bash
   # Check worker status
   rq info
   
   # Clear failed jobs
   rq empty failed
   ```

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

### Code Style
- Follow PEP 8 for Python code
- Use ESLint and Prettier for JavaScript/TypeScript
- Write descriptive commit messages
- Document new features

## 📄 License

MIT License - see [LICENSE.md](LICENSE.md)



