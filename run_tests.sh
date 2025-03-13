#!/bin/bash

# Install test requirements
pip install -r tests/requirements.txt

# Run storage service tests
echo "Running Storage Service Tests..."
python -m unittest tests.test_storage_service
