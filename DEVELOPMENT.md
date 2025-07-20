# CloudArb Development Guide

This guide explains how to set up and use the CloudArb development environment with simplified workflows.

## 🚀 Quick Start

### Prerequisites

- **Node.js 18+**: Required for frontend development (automatically installed by the scripts)
- **Python 3.8+**: Required for backend development
- **Docker**: Required for database and monitoring services

### Option 1: Gitpod Automations (Recommended)

If you're using Gitpod, the development environment will automatically start when you open the workspace. The `.gitpod/automations.yml` file configures all services to start automatically.

**What happens automatically:**
- PostgreSQL with TimescaleDB starts
- Redis cache starts
- FastAPI backend starts with hot reload
- React frontend starts with hot reload
- Prometheus and Grafana monitoring start
- Database schema is initialized
- Admin user is created (admin@cloudarb.com / admin123)

**Access URLs:**
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin/admin)

### Option 2: Local Development Script

For local development, use the simplified development script:

```bash
# Start all services
./scripts/dev.sh start

# Check status
./scripts/dev.sh status

# View logs
./scripts/dev.sh logs

# Stop all services
./scripts/dev.sh stop

# Restart all services
./scripts/dev.sh restart

# Clean up environment
./scripts/dev.sh cleanup
```

## 🔧 Development Workflow

### Frontend Development

The frontend runs in development mode with hot reload, so any changes you make to React components will automatically refresh the browser.

```bash
# Frontend is automatically started, but you can also run it manually:
cd frontend
npm install  # Only needed first time
npm start
```

**Key Features:**
- Hot reload for instant feedback
- Source maps for debugging
- Error overlay for development errors
- Automatic API proxy to backend

### Backend Development

The FastAPI backend runs with auto-reload, so changes to Python files will automatically restart the server.

```bash
# Backend is automatically started, but you can also run it manually:
cd src
source ../venv/bin/activate
python -m uvicorn cloudarb.main:app --host 0.0.0.0 --port 8000 --reload
```

**Key Features:**
- Auto-reload on code changes
- Interactive API documentation at http://localhost:8000/docs
- Automatic database migrations
- Development logging

### Database Development

The database is automatically initialized with the schema and sample data.

```bash
# Database is automatically set up, but you can reinitialize:
cd src
source ../venv/bin/activate
python -c "
from cloudarb.database import engine
from cloudarb.models import Base
Base.metadata.create_all(bind=engine)
"
```

## 🛠️ Available Commands

### Gitpod Automations Tasks

In Gitpod, you can run these tasks from the Automations panel:

- **Initialize Database**: Set up database schema and initial data
- **Run Tests**: Execute all backend and frontend tests
- **Lint Code**: Run code linting and formatting checks
- **Build for Production**: Build the application for production
- **Clean Up**: Stop services and clean up environment

### Development Script Commands

```bash
./scripts/dev.sh start      # Start all development services
./scripts/dev.sh stop       # Stop all development services
./scripts/dev.sh restart    # Restart all development services
./scripts/dev.sh status     # Show status of all services
./scripts/dev.sh cleanup    # Stop services and clean up environment
./scripts/dev.sh logs       # Show live logs from API and frontend
```

## 📁 Project Structure

```
CloudArb/
├── .gitpod/
│   └── automations.yml     # Gitpod automation configuration
├── frontend/               # React frontend application
│   ├── src/
│   ├── public/
│   └── package.json
├── src/                    # Python backend application
│   └── cloudarb/
│       ├── api/           # API routes
│       ├── models/        # Database models
│       ├── services/      # Business logic
│       └── main.py        # FastAPI application
├── scripts/
│   ├── dev.sh            # Development environment script
│   └── deploy.sh         # Production deployment script
├── docker/               # Docker configurations
├── monitoring/           # Prometheus and Grafana configs
└── requirements.txt      # Python dependencies
```

## 🔍 Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Check what's using the port
   lsof -i :3000  # or :8000, :5432, etc.

   # Kill the process
   kill -9 <PID>
   ```

2. **Database connection issues**
   ```bash
   # Restart PostgreSQL
   docker restart cloudarb-postgres

   # Check logs
   docker logs cloudarb-postgres
   ```

3. **Frontend not loading**
   ```bash
   # Check if frontend is running
   ./scripts/dev.sh status

   # Restart frontend
   pkill -f "react-scripts start"
   cd frontend && npm start
   ```

4. **API not responding**
   ```bash
   # Check if API is running
   ./scripts/dev.sh status

   # Restart API
   pkill -f "uvicorn cloudarb.main:app"
   cd src && python -m uvicorn cloudarb.main:app --reload
   ```

### Logs

View logs for debugging:

```bash
# View API logs
tail -f logs/api.log

# View frontend logs
tail -f logs/frontend.log

# View all logs
./scripts/dev.sh logs
```

## 🚀 Production vs Development

### Development Mode
- Hot reload enabled
- Debug logging
- Development database
- No SSL
- CORS enabled for localhost

### Production Mode
- Use `./scripts/deploy.sh start` for production
- Optimized builds
- Production database
- SSL enabled
- Security headers
- Rate limiting

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://reactjs.org/docs/)
- [Gitpod Automations](https://www.gitpod.io/docs/gitpod/configuration/automations/overview.md)
- [TimescaleDB Documentation](https://docs.timescale.com/)

## 🤝 Contributing

1. Use the development environment for all development work
2. Run tests before committing: `./scripts/dev.sh run-tests`
3. Lint your code: `./scripts/dev.sh lint`
4. Follow the existing code style and patterns
5. Update documentation for any new features