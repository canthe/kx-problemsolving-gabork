import os
import time
import uuid
import httpx
import random
import asyncio
import fastapi
import uvicorn

from typing import Dict
from typing import List
from typing import Optional
from pydantic import BaseModel


class ServiceStatus(BaseModel):
    """Model representing a service's status."""
    url: str
    healthy: bool
    last_check: float
    response_time: Optional[float] = None


class ServiceRegistry:
    """Manages the registry of available storage services."""

    def __init__(self, service_urls: List[str]):
        """Initialize the service registry with a list of service URLs."""
        self.services: Dict[str, ServiceStatus] = {}
        for url in service_urls:
            self.services[url] = ServiceStatus(
                url=url,
                healthy=False,
                last_check=0,
                response_time=None
            )

    def mark_healthy(self, url: str, response_time: float) -> None:
        """Mark a service as healthy."""
        if url in self.services:
            self.services[url].healthy = True
            self.services[url].response_time = response_time
            self.services[url].last_check = time.time()

    def mark_unhealthy(self, url: str) -> None:
        """Mark a service as unhealthy."""
        if url in self.services:
            self.services[url].healthy = False
            self.services[url].last_check = time.time()

    def get_healthy_services(self) -> List[str]:
        """Get a list of healthy service URLs."""
        return [url for url, status in self.services.items() if status.healthy]

    def get_all_statuses(self) -> Dict:
        """Get the status of all services."""
        return {
            url: {
                "url": status.url,
                "healthy": status.healthy,
                "last_check": status.last_check,
                "response_time": status.response_time
            }
            for url, status in self.services.items()
        }


class LoadBalancer:
    """Handles load balancing between multiple services."""

    def __init__(self, service_registry: ServiceRegistry):
        """Initialize the load balancer."""
        self.service_registry = service_registry
        self.current_index = 0

    def get_next_service(self) -> Optional[str]:
        """Get the next service using round-robin selection."""
        healthy_services = self.service_registry.get_healthy_services()

        if not healthy_services:
            return None

        if self.current_index >= len(healthy_services):
            self.current_index = 0

        selected_service = healthy_services[self.current_index]
        self.current_index += 1

        return selected_service


class ServiceHealthChecker:
    """Handles health checking for services."""

    def __init__(self, service_registry: ServiceRegistry, timeout: float = 2.0, check_interval: int = 10):
        """Initialize the health checker."""
        self.service_registry = service_registry
        self.timeout = timeout
        self.check_interval = check_interval

    async def check_service(self, url: str) -> bool:
        """Check the health of a single service."""
        try:
            start_time = time.time()

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{url}/health")

            end_time = time.time()

            if response.status_code == 200:
                self.service_registry.mark_healthy(url, end_time - start_time)
                return True
            else:
                self.service_registry.mark_unhealthy(url)
                return False
        except (httpx.RequestError, asyncio.TimeoutError):
            self.service_registry.mark_unhealthy(url)
            return False

    async def check_all_services(self):
        """Check the health of all services."""
        for url in self.service_registry.services:
            await self.check_service(url)

    async def start_health_check_loop(self):
        """Start a continuous loop to check service health."""
        while True:
            await self.check_all_services()
            await asyncio.sleep(self.check_interval)


class DataService:
    """Handles data retrieval from storage services."""

    def __init__(self, load_balancer: LoadBalancer, service_registry: ServiceRegistry, timeout: float = 2.0):
        """Initialize the data service."""
        self.timeout = timeout
        self.load_balancer = load_balancer
        self.service_registry = service_registry

    async def get_data(self, max_retries: int = 3) -> Dict:
        """Get data from a storage service."""
        retries = 0

        while retries < max_retries:
            service_url = self.load_balancer.get_next_service()

            if not service_url:
                # No healthy services available
                return {
                    "status": "degraded",
                    "message": "No storage services available",
                    "data": []
                }

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(f"{service_url}/data")

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "success",
                        "service_used": service_url,
                        "data": data["data"]
                    }
                else:
                    # If we get a non-200 response, mark as unhealthy and retry
                    self.service_registry.mark_unhealthy(service_url)
                    retries += 1

            except (httpx.RequestError, asyncio.TimeoutError):
                # If request fails, mark as unhealthy and retry
                self.service_registry.mark_unhealthy(service_url)
                retries += 1

        # If we've exhausted retries, return error
        return {
            "status": "error",
            "message": "Failed to retrieve data after multiple attempts",
            "data": []
        }


class GatewayService:
    """Main gateway service class."""

    def __init__(self):
        """Initialize the gateway service."""
        self.app = fastapi.FastAPI(
            title="KX - Gateway Service",
            debug=False,
            redoc_url=None,
            docs_url="/docs",
            openapi_url="/openapi.json"
        )

        self.service_port = int(os.environ.get("PORT", 8000))

        self.service_urls = os.environ.get(
            "STORAGE_SERVICES",
            "http://storage1:8001,http://storage2:8002,http://storage3:8003"
        ).split(",")

        check_interval = int(os.environ.get("CHECK_INTERVAL", "10"))
        service_timeout = float(os.environ.get("SERVICE_TIMEOUT", "2.0"))

        self.service_registry = ServiceRegistry(self.service_urls)

        self.load_balancer = LoadBalancer(self.service_registry)

        self.health_checker = ServiceHealthChecker(
            self.service_registry,
            timeout=service_timeout,
            check_interval=check_interval
        )

        self.data_service = DataService(
            self.load_balancer,
            self.service_registry,
            timeout=service_timeout
        )

        self._register_api_routes()

    def _register_api_routes(self):
        """Register all API routes."""

        @self.app.get("/status")
        async def get_status():
            """Get the status of all storage services."""
            return {
                "gateway": "running",
                "services": self.service_registry.get_all_statuses()
            }

        @self.app.get("/data")
        async def get_data():
            """Fetch data from a healthy storage service."""
            return await self.data_service.get_data()

    async def startup(self):
        """Startup event handler."""
        # Start the health check loop
        asyncio.create_task(self.health_checker.start_health_check_loop())

    def run(self):
        """Run the gateway service."""
        self.app.add_event_handler(event_type="startup", func=self.startup)

        uvicorn.run(
            app=self.app,
            host="0.0.0.0",
            port=self.service_port
        )


if __name__ == "__main__":
    service = GatewayService()
    service.run()