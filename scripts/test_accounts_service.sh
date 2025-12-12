#!/bin/bash

# Script to test Accounts Service deployment
# Usage: ./scripts/test_accounts_service.sh [CONTAINER_URL]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get container URL from argument or Yandex Cloud
if [ -z "$1" ]; then
    echo -e "${YELLOW}No URL provided, fetching from Yandex Cloud...${NC}"
    CONTAINER_URL=$(yc serverless container get accounts-service-container --format json | jq -r '.url')
    
    if [ -z "$CONTAINER_URL" ] || [ "$CONTAINER_URL" == "null" ]; then
        echo -e "${RED}Error: Could not fetch container URL${NC}"
        echo "Usage: $0 [CONTAINER_URL]"
        exit 1
    fi
else
    CONTAINER_URL=$1
fi

echo -e "${GREEN}Testing Accounts Service at: ${CONTAINER_URL}${NC}"
echo ""

# Test 1: Health check
echo -e "${YELLOW}[1/4] Testing health endpoint...${NC}"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${CONTAINER_URL}/health")
HEALTH_CODE=$(echo "$HEALTH_RESPONSE" | tail -n 1)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | head -n -1)

if [ "$HEALTH_CODE" == "200" ]; then
    echo -e "${GREEN}✅ Health check passed${NC}"
    echo "Response: $HEALTH_BODY"
else
    echo -e "${RED}❌ Health check failed (HTTP $HEALTH_CODE)${NC}"
    echo "Response: $HEALTH_BODY"
    exit 1
fi
echo ""

# Test 2: OpenAPI docs
echo -e "${YELLOW}[2/4] Testing OpenAPI docs endpoint...${NC}"
DOCS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${CONTAINER_URL}/docs")

if [ "$DOCS_CODE" == "200" ]; then
    echo -e "${GREEN}✅ OpenAPI docs available${NC}"
    echo "URL: ${CONTAINER_URL}/docs"
else
    echo -e "${RED}❌ OpenAPI docs failed (HTTP $DOCS_CODE)${NC}"
fi
echo ""

# Test 3: Create payment instruction
echo -e "${YELLOW}[3/4] Testing payment creation...${NC}"
PAYMENT_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "${CONTAINER_URL}/accounts/ACC-001/payments" \
    -H "Content-Type: application/json" \
    -d '{
        "to_account": "ACC-002",
        "amount": 100.50,
        "currency": "RUB",
        "description": "Test payment from script"
    }')

PAYMENT_CODE=$(echo "$PAYMENT_RESPONSE" | tail -n 1)
PAYMENT_BODY=$(echo "$PAYMENT_RESPONSE" | head -n -1)

if [ "$PAYMENT_CODE" == "202" ]; then
    echo -e "${GREEN}✅ Payment instruction created${NC}"
    echo "Response: $PAYMENT_BODY"
    
    # Extract instruction_id
    INSTRUCTION_ID=$(echo "$PAYMENT_BODY" | jq -r '.instruction_id')
    echo "Instruction ID: $INSTRUCTION_ID"
else
    echo -e "${RED}❌ Payment creation failed (HTTP $PAYMENT_CODE)${NC}"
    echo "Response: $PAYMENT_BODY"
fi
echo ""

# Test 4: Invalid request
echo -e "${YELLOW}[4/4] Testing validation (invalid request)...${NC}"
INVALID_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "${CONTAINER_URL}/accounts/ACC-001/payments" \
    -H "Content-Type: application/json" \
    -d '{
        "invalid_field": "test"
    }')

INVALID_CODE=$(echo "$INVALID_RESPONSE" | tail -n 1)
INVALID_BODY=$(echo "$INVALID_RESPONSE" | head -n -1)

if [ "$INVALID_CODE" == "422" ]; then
    echo -e "${GREEN}✅ Validation working correctly${NC}"
    echo "Response: $INVALID_BODY"
else
    echo -e "${YELLOW}⚠️  Expected 422, got HTTP $INVALID_CODE${NC}"
    echo "Response: $INVALID_BODY"
fi
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ All tests completed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Container URL: ${CONTAINER_URL}"
echo "OpenAPI Docs: ${CONTAINER_URL}/docs"
echo "ReDoc: ${CONTAINER_URL}/redoc"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Check logs: yc serverless container revision logs --container-name accounts-service-container --follow"
echo "2. Monitor metrics in Yandex Cloud Console"
echo "3. Test with real RabbitMQ integration"

