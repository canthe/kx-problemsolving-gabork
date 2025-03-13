
## [KX - Problem Solving Exercise Description](exercise.description.md)

---

# KX - Problem Solving - Solution

## Project Structure
```
service-assembly/
├── gateway/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── storage/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── tests/
│   ├── requirerments.txt
│   └── test_storage_service.py
├── docker-compose.yml
└── run_tests.sh
```

## Key Components & Features
**Storage Service**
  * Stores dummy data in-memory
  * Provides dummy data through a REST API
  * Has **/health** check endpoint
  * Returns service ID with responses for tracking

**Gateway Service**
  * Tracks availability of Storage Services with regular **/health** checks
  * Provides **/status** endpoint showing the status of all Storage Services
  * Implements round-robin load balancing for the **/data** endpoint
  * Handles the case when no Storage Services are available by returning a degraded status and empty data array
  * Automatically retries with another service if one fails
  * If a service becomes unhealthy, it's removed from the rotation

## How to execute
To run the service assembly, navigate to the root directory and execute:
```bash
docker-compose up --build
```

The service endpoints can be then accessed:
  * Gateway status: http://localhost:8000/status
  * Gateway data: http://localhost:8000/data
  * Individual storage services: http://localhost:8001, http://localhost:8002, http://localhost:8003