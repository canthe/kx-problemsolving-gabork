import os
import uuid
import random
import fastapi
import uvicorn

from typing import Dict
from typing import List
from typing import Optional


class DataRepository:
    """Repository class for managing dummy data."""

    def __init__(self, service_id: str):
        """Initialize with some dummy data."""

        self.service_id = service_id

        self.data: List[Dict] = [
            {"id": 1, "name": "Product 01", "category": "Books", "price": 100, "_service_id": self.service_id},
            {"id": 2, "name": "Product 02", "category": "Books", "price": 200, "_service_id": self.service_id},
            {"id": 3, "name": "Product 03", "category": "Cars", "price": 300, "_service_id": self.service_id},
            {"id": 4, "name": "Product 04", "category": "Cars", "price": 400, "_service_id": self.service_id},
            {"id": 5, "name": "Product 05", "category": "Food", "price": 500, "_service_id": self.service_id},
        ]

    def get_all(self) -> List[Dict]:
        """Get all data items."""
        return self.data

    def get_by_id(self, item_id: int) -> Optional[Dict]:
        """Get a specific data item by ID."""
        for item in self.data:
            if item["id"] == item_id:
                return item
        return None


class StorageService:
    """Main storage service class."""

    def __init__(self):
        """Initialize the storage service."""
        self.app = fastapi.FastAPI(
            title="KX - Storage Service",
            debug=False,
            redoc_url=None,
            docs_url="/docs",
            openapi_url="/openapi.json"
        )

        self.service_id = str(uuid.uuid4())[:8]
        self.service_port = int(os.environ.get("PORT", 8000))
        self.repository = DataRepository(service_id=self.service_id)

        self._register_api_routes()

    def _register_api_routes(self):
        """Register all API routes."""

        @self.app.get("/")
        async def root():
            """Root endpoint providing basic service information."""
            return {
                "service": "Storage Service",
                "id": self.service_id,
                "status": "running",
                "port": self.service_port
            }

        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy", "service_id": self.service_id}

        @self.app.get("/data")
        async def get_data():
            """Return all dummy data."""
            return {"service_id": self.service_id, "data": self.repository.get_all()}

        @self.app.get("/data/{item_id}")
        async def get_data_by_id(item_id: int):
            """Return specific data item by ID."""

            if item := self.repository.get_by_id(item_id):
                return {"service_id": self.service_id, "data": item}

            raise fastapi.HTTPException(status_code=404, detail=f"Item with ID {item_id} not found")

    def run(self):
        """Run the service."""
        uvicorn.run(
            app=self.app,
            host="0.0.0.0",
            port=self.service_port
        )


if __name__ == "__main__":
    service = StorageService()
    service.run()
