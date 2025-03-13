# python -m unittest tests.test_storage_service

import os
import sys
import json
import unittest

from unittest.mock import patch
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from storage.app import DataRepository
from storage.app import StorageService


class TestDataRepository(unittest.TestCase):

    def setUp(self):
        """Set up test environment."""
        self.service_id = "dummy"
        self.repository = DataRepository(service_id="dummy")
    
    def test_get_all(self):
        """Test get_all method returns all items."""
        data = self.repository.get_all()
        self.assertEqual(len(data), 5)  # Verify we have 5 items
        self.assertEqual(data[0]["name"], "Product 01")
        self.assertEqual(data[4]["name"], "Product 05")
    
    def test_get_by_id_existing(self):
        """Test get_by_id with an existing ID."""
        item = self.repository.get_by_id(3)
        self.assertIsNotNone(item)
        self.assertEqual(item["name"], "Product 03")
        self.assertEqual(item["category"], "Cars")
    
    def test_get_by_id_nonexistent(self):
        """Test get_by_id with a non-existent ID."""
        item = self.repository.get_by_id(999)
        self.assertIsNone(item)


class TestStorageService(unittest.TestCase):
    """Test cases for the StorageService class."""
    
    def setUp(self):
        """Set up test environment."""
        self.env_patcher = patch.dict('os.environ', {'PORT': '8001'})
        self.env_patcher.start()
        self.service = StorageService()
        self.client = TestClient(self.service.app)
    
    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()
    
    def test_root_endpoint(self):
        """Test the root endpoint."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["service"], "Storage Service")
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["port"], 8001)
        self.assertIsNotNone(data["id"])
    
    def test_health_endpoint(self):
        """Test the health endpoint."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIsNotNone(data["service_id"])
    
    def test_get_data_endpoint(self):
        """Test the data endpoint."""
        response = self.client.get("/data")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNotNone(data["service_id"])
        self.assertEqual(len(data["data"]), 5)
    
    def test_get_data_by_id_existing(self):
        """Test getting data by ID for an existing item."""
        response = self.client.get("/data/2")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNotNone(data["service_id"])
        self.assertEqual(data["data"]["name"], "Product 02")
    
    def test_get_data_by_id_nonexistent(self):
        """Test getting data by ID for a non-existent item."""
        response = self.client.get("/data/999")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertEqual(data["detail"], "Item with ID 999 not found")
