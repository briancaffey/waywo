# Waywo

An searchable index of 'What are you working on?' projects from Hacker News

## Services

When running with `docker compose up`, the following services are available:

### Backend API
- **URL**: http://localhost:8008
- **API Documentation**: http://localhost:8008/docs
- **ReDoc**: http://localhost:8008/redoc
- **Health Check**: http://localhost:8008/api/health

### Celery Flower (Monitoring)
- **URL**: http://localhost:5555
- Celery task monitoring and management interface

### Redis Insights
- **URL**: http://localhost:7001
- Redis Stack web UI for database management and monitoring

### Redis
- **Connection**: localhost:7379
- Redis database connection port

## Development

### Running Services

```bash
docker compose up -d
```

### Stopping Services

```bash
docker compose down
```

### Code Formatting

```bash
make black      # Format code with black
make check      # Check if code is formatted correctly
```
