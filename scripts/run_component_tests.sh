#!/bin/bash

# Component Tests Runner Script
# Usage: ./scripts/run_component_tests.sh [options]

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}  Component Tests Runner${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running!${NC}"
    echo "Please start Docker Desktop and try again."
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements-test.txt
else
    source venv/bin/activate
fi

echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Check if pytest is installed
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}pytest not found. Installing dependencies...${NC}"
    pip install -r requirements-test.txt
fi

echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Parse command line arguments
TEST_PATH="tests/component/"
EXTRA_ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --service=*)
            SERVICE="${1#*=}"
            TEST_PATH="tests/component/test_${SERVICE}_service.py"
            shift
            ;;
        --e2e)
            TEST_PATH="tests/component/test_end_to_end_flow.py"
            shift
            ;;
        --parallel)
            EXTRA_ARGS="$EXTRA_ARGS -n auto"
            shift
            ;;
        --coverage)
            EXTRA_ARGS="$EXTRA_ARGS --cov=services --cov-report=html --cov-report=term"
            shift
            ;;
        --verbose)
            EXTRA_ARGS="$EXTRA_ARGS -vv"
            shift
            ;;
        --quick)
            EXTRA_ARGS="$EXTRA_ARGS -x"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--service=NAME] [--e2e] [--parallel] [--coverage] [--verbose] [--quick]"
            exit 1
            ;;
    esac
done

# Run tests
echo -e "${YELLOW}Running tests: $TEST_PATH${NC}"
echo ""

if pytest $TEST_PATH -v $EXTRA_ARGS; then
    echo ""
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}  All tests passed! ✓${NC}"
    echo -e "${GREEN}================================${NC}"
    
    if [[ $EXTRA_ARGS == *"--cov"* ]]; then
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
    fi
else
    echo ""
    echo -e "${RED}================================${NC}"
    echo -e "${RED}  Some tests failed! ✗${NC}"
    echo -e "${RED}================================${NC}"
    exit 1
fi

