# 🚀 FastAPI Blog API

A production-ready blog API with authentication, PostgreSQL database, Redis caching, and comprehensive features. Built with FastAPI following best practices.

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)

## ✨ Features

- **🔐 JWT Authentication** - Login, register, password reset
- **📝 Full CRUD** - Create, read, update, delete blog posts
- **⚡ Redis Caching** - Performance optimization
- **🗄️ PostgreSQL** - Async SQLAlchemy ORM
- **📊 Rate Limiting** - Prevent API abuse
- **📧 Email Service** - Password reset functionality
- **📚 Interactive Docs** - Swagger UI & ReDoc
- **🔒 Security** - Password hashing, token blacklisting

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Redis 6+

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/fastapi-blog-api.git
cd fastapi-blog-api

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Mac/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment
cp .env.example .env
# Edit .env with your database credentials

# 6. Run database migrations
alembic upgrade head

# 7. Start Redis (in another terminal)
# Mac: brew services start redis
# Linux: sudo systemctl start redis-server
# Or use Docker: docker run -p 6379:6379 redis:7-alpine

# 8. Run the application
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Access the API
API Server: http://localhost:8000

Swagger UI: http://localhost:8000/docs

ReDoc: http://localhost:8000/redoc

📁 Project Structure
text
fastapi-blog-api/
├── app/
│   ├── api/              # API routes
│   ├── core/             # Config, security, database
│   ├── crud/             # Database operations
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   └── main.py           # FastAPI app
├── migrations/           # Database migrations
├── tests/               # Test suite
├── requirements.txt     # Dependencies
└── .env.example        # Environment template
🔧 Configuration
Create .env file:

env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/blogdb

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-minimum-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
API_V1_STR=/api/v1
PROJECT_NAME=FastAPI Blog API
📚 API Usage Examples
Authentication
bash
# Register
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepassword"}'

# Login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=securepassword"

# Get current user (with token)
curl -X GET "http://localhost:8000/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
Blog Posts
bash
# Create post
curl -X POST "http://localhost:8000/api/v1/posts" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Post", "content": "Post content", "published": true}'

# Get all posts
curl -X GET "http://localhost:8000/api/v1/posts"

# Get single post
curl -X GET "http://localhost:8000/api/v1/posts/1"

🧪 Testing
bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py -v
🔄 Database Migrations
bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
📊 API Endpoints
Method	Endpoint	Description	Auth Required
POST	/api/v1/auth/register	Register user	No
POST	/api/v1/auth/login	Login	No
POST	/api/v1/auth/logout	Logout	Yes
GET	/api/v1/users/me	Current user	Yes
GET	/api/v1/posts	List posts	No
GET	/api/v1/posts/{id}	Get post	No
POST	/api/v1/posts	Create post	Yes
PUT	/api/v1/posts/{id}	Update post	Yes
DELETE	/api/v1/posts/{id}	Delete post	Yes
🤝 Contributing
Fork the repository

Create feature branch (git checkout -b feature/AmazingFeature)

Commit changes (git commit -m 'Add AmazingFeature')

Push to branch (git push origin feature/AmazingFeature)

Open Pull Request

📄 License
MIT License - see LICENSE file for details.

⚡ Quick Commands
bash
# Start server
python -m uvicorn app.main:app --reload

# Run tests
pytest

# Create migration
alembic revision --autogenerate -m "update"

# Format code
black app/
⭐ Star this repo if you find it useful!

Questions? Open an issue or check the interactive docs at http://localhost:8000/docs