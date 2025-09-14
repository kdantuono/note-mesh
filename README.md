# NoteMesh

NoteMesh is a modern, modular, and scalable note-sharing application designed for seamless collaboration. Built with flexibility and performance in mind, it supports real-time synchronization, intuitive organization, and extensibility for teams, students, and professionals.

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Git

### 🐳 Docker Development Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/kdantuono/note-mesh.git
   cd note-mesh
   ```

2. **Start development environment**
   ```bash
   docker-compose -f docker-compose.dev.yml up --build
   ```

   This command will start:
   - **PostgreSQL** (port 5432) - Main database
   - **Redis** (port 6379) - Session storage and caching
   - **Backend API** (port 8000) - FastAPI application with hot reload
   - **Frontend** (port 3000) - Nginx serving HTML/JS/CSS with API proxy

   For additional database management tools:
   ```bash
   docker-compose -f docker-compose.yml up adminer redis-commander -d
   ```
   - **Database Admin (Adminer)**: http://localhost:8080 (username: `notemesh`, password: `password`)
   - **Redis Admin**: http://localhost:8081 (password: `devpassword`)

3. **Access the application**
   - **Frontend Application**: http://localhost:3000
   - **API Documentation**: http://localhost:8000/docs
   - **API Health Check**: http://localhost:8000/api/health/
   - **Frontend Health**: http://localhost:3000/health

### 🔧 Manual Setup (Alternative)

If you prefer to run services individually:

1. **Install dependencies**
   ```bash
   cd backend
   pip install -e .
   pip install -e .[dev]  # For development tools
   ```

2. **Start PostgreSQL and Redis**
   ```bash
   docker-compose up postgres redis -d
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run database migrations**
   ```bash
   cd backend
   alembic upgrade head
   ```

5. **Start the backend**
   ```bash
   cd backend
   uvicorn src.notemesh.main:app --reload --host 0.0.0.0 --port 8000
   ```

## 📚 API Documentation

### Authentication Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/refresh` - Refresh JWT token
- `GET /api/auth/me` - Get current user profile
- `PUT /api/auth/me` - Update user profile
- `POST /api/auth/change-password` - Change password
- `POST /api/auth/logout` - Logout user

### Notes Endpoints

- `POST /api/notes/` - Create new note
- `GET /api/notes/` - List user notes (with pagination and tag filtering)
- `GET /api/notes/{note_id}` - Get specific note
- `PUT /api/notes/{note_id}` - Update note
- `DELETE /api/notes/{note_id}` - Delete note
- `GET /api/notes/tags/` - Get available tags
- `POST /api/notes/validate-links` - Validate hyperlinks

### Search Endpoints

- `GET /api/search/notes` - Search notes by content and tags
- `GET /api/search/tags/suggest` - Get tag suggestions
- `GET /api/search/stats` - Get search statistics

### Sharing Endpoints

- `POST /api/sharing/` - Share note with other users
- `DELETE /api/sharing/{share_id}` - Revoke note share
- `GET /api/sharing/notes/{note_id}` - Get shared note (for recipients)
- `GET /api/sharing/` - List shares (given or received)
- `GET /api/sharing/stats` - Get sharing statistics
- `GET /api/sharing/notes/{note_id}/access` - Check note access permissions

### Health Endpoints

- `GET /api/health/` - Overall system health
- `GET /api/health/database` - Database connectivity
- `GET /api/health/redis` - Redis connectivity
- `GET /api/health/metrics` - System metrics

## 🧪 Testing

### Run Tests

```bash
cd backend

# Run all tests with coverage
pytest --cov=src/notemesh --cov-report=html --cov-fail-under=80

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m "not slow"     # Skip slow tests

# Run single test file
pytest tests/unit/test_services.py -v
```

### Code Quality

```bash
cd backend

# Format code
black --line-length=100 src/ tests/
isort --profile=black src/ tests/

# Type checking
mypy src/ --strict

# Linting
flake8 src/ --max-complexity=10 --max-line-length=100

# Security scanning
bandit -r src/ -ll
```

## 🔧 Development

### Project Structure

```
note-mesh/
├── backend/                # FastAPI backend application
│   ├── src/notemesh/       # Main application code
│   │   ├── api/            # API route handlers
│   │   ├── core/           # Business logic and models
│   │   │   ├── models/     # SQLAlchemy database models
│   │   │   ├── schemas/    # Pydantic request/response schemas
│   │   │   ├── services/   # Business logic services
│   │   │   └── repositories/ # Data access layer
│   │   ├── middleware/     # Custom middleware
│   │   ├── security/       # Authentication and security utilities
│   │   ├── config.py       # Application configuration
│   │   ├── database.py     # Database connection setup
│   │   └── main.py         # FastAPI application entry point
│   ├── alembic/            # Database migrations
│   ├── tests/              # Test suite
│   ├── Dockerfile          # Container definition
│   └── requirements.txt    # Python dependencies
├── docker-compose.yml      # Multi-service development environment
├── .env                    # Environment variables (created from .env.example)
└── README.md               # This file
```

### Database Migrations

```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Reset database (dev only)
alembic downgrade base && alembic upgrade head
```

### Environment Variables

Key environment variables (see `.env.example` for full list):

```bash
# Database
DATABASE_URL=postgresql+asyncpg://notemesh:notemesh_password@postgres:5432/notemesh

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# Application
DEBUG=true
```

## 🔐 Security

- JWT-based authentication with access and refresh tokens
- Password hashing using bcrypt
- CORS protection
- Rate limiting
- Input validation with Pydantic schemas
- SQL injection protection via SQLAlchemy ORM
- Security headers via FastAPI middleware

## 📊 Features

### Core Features

- **User Management**: Registration, authentication, profile management
- **Note Management**: Create, read, update, delete notes with rich content
- **Tag System**: Automatic hashtag extraction and manual tag management
- **Full-Text Search**: Search notes by content and tags with ranking
- **Note Sharing**: Share notes with other users with permission control
- **Hyperlink Validation**: Validate and track external links in notes

### Technical Features

- **Async/Await**: Fully asynchronous operations for high performance
- **Type Safety**: 100% type coverage with mypy strict mode
- **Test Coverage**: Comprehensive test suite with >80% coverage requirement
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- **Database Migrations**: Version-controlled schema changes with Alembic
- **Containerization**: Docker-based development and deployment
- **Health Monitoring**: Built-in health checks for all components

## 🛠 Troubleshooting

### Common Issues

1. **Database connection failed**
   ```bash
   # Ensure PostgreSQL is running
   docker-compose ps postgres

   # Check database logs
   docker-compose logs postgres
   ```

2. **Redis connection failed**
   ```bash
   # Ensure Redis is running
   docker-compose ps redis

   # Check Redis logs
   docker-compose logs redis
   ```

3. **Backend startup issues**
   ```bash
   # Check backend logs
   docker-compose logs backend

   # Rebuild backend container
   docker-compose up --build backend
   ```

4. **Permission issues**
   ```bash
   # Reset Docker volumes
   docker-compose down --volumes
   docker-compose up --build
   ```

### Useful Commands

```bash
# View all container status
docker-compose ps

# View logs for specific service
docker-compose logs <service-name>

# Execute commands in running container
docker-compose exec backend bash

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down --volumes --remove-orphans

# View API logs in real-time
docker-compose logs -f backend
```

## 📝 Testing with Postman

1. **Import the API**: Visit http://localhost:8000/docs for interactive API documentation
2. **Register a user**: `POST /api/auth/register`
3. **Login**: `POST /api/auth/login` to get JWT tokens
4. **Set Authorization**: Add `Bearer <access_token>` to Authorization header
5. **Test endpoints**: Create notes, search, share, etc.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and quality checks
5. Submit a pull request

## 🎯 Complete Application Features

### Frontend Interface
- **Modern Web UI**: Responsive design with mobile-first approach
- **User Authentication**: Login/register forms with validation
- **Notes Dashboard**: Visual distinction between owned, shared, and sharing notes
- **Search & Filter**: Real-time search with tag filtering
- **Note Editor**: Rich text editing with tag assignment
- **Sharing Modal**: User-friendly interface for note sharing
- **Toast Notifications**: Real-time user feedback

### Backend API Complete
- **REST API**: Comprehensive endpoints with OpenAPI documentation
- **Authentication**: JWT-based auth with refresh tokens
- **Database**: PostgreSQL with Redis caching
- **Search**: Full-text search with tag suggestions
- **Security**: Input validation, CORS, rate limiting ready

### Development Tools
- **Docker Setup**: Complete containerized environment
- **CI/CD Pipeline**: GitHub Actions with testing and quality checks
- **Postman Collection**: 3 users, 10 notes, complete API testing
- **Code Quality**: Black, isort, mypy, flake8, bandit, 80%+ coverage

## 🌐 Service URLs

When running with `docker-compose.dev.yml`:
- **Frontend Application**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Checks**:
  - Frontend: http://localhost:3000/health
  - Backend: http://localhost:8000/api/health/

Additional services (if started separately):
- **Database Admin (Adminer)**: http://localhost:8080
- **Redis Admin**: http://localhost:8081


## 📄 License
The MIT License (MIT)

Copyright © 2025 Cosmo D'Antuono

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


