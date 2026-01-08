#!/bin/bash

echo "setting up environment..."
source .venv/bin/activate

echo ""
echo "seeding database..."
time python src/seed.py

echo ""
echo "running benchmark tests..."
time python src/test_benchmark.py