#!/bin/bash

# Script to get all values for GitHub Secrets
# This script helps you collect all necessary values for GitHub Actions

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}GitHub Secrets Configuration Helper${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if yc is installed
if ! command -v yc &> /dev/null; then
    echo -e "${YELLOW}Error: Yandex Cloud CLI (yc) is not installed${NC}"
    echo "Install it: curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash"
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Warning: jq is not installed${NC}"
    echo "Install it for better output: brew install jq (macOS) or apt-get install jq (Linux)"
    echo ""
fi

echo -e "${GREEN}Fetching values from Yandex Cloud...${NC}"
echo ""

# YC_CLOUD_ID
echo -e "${YELLOW}YC_CLOUD_ID:${NC}"
CLOUD_ID=$(yc config get cloud-id)
echo "$CLOUD_ID"
echo ""

# YC_FOLDER_ID
echo -e "${YELLOW}YC_FOLDER_ID:${NC}"
FOLDER_ID=$(yc config get folder-id)
echo "$FOLDER_ID"
echo ""

# YC_REGISTRY_ID
echo -e "${YELLOW}YC_REGISTRY_ID:${NC}"
if command -v jq &> /dev/null; then
    REGISTRY_ID=$(yc container registry list --format json | jq -r '.[0].id // empty')
    if [ -z "$REGISTRY_ID" ]; then
        echo "No registry found. Create one with:"
        echo "  yc container registry create --name miar-registry"
    else
        echo "$REGISTRY_ID"
    fi
else
    yc container registry list
    echo "(Copy the ID from above)"
fi
echo ""

# YC_SERVICE_ACCOUNT_ID
echo -e "${YELLOW}YC_SERVICE_ACCOUNT_ID:${NC}"
echo "Looking for 'github-deployer' service account..."
if command -v jq &> /dev/null; then
    SA_ID=$(yc iam service-account get github-deployer --format json 2>/dev/null | jq -r '.id // empty')
    if [ -z "$SA_ID" ]; then
        echo "Service account 'github-deployer' not found."
        echo ""
        echo "Create it with:"
        echo "  yc iam service-account create --name github-deployer --description 'Service account for GitHub Actions'"
        echo ""
        echo "Then assign roles:"
        echo "  SA_ID=\$(yc iam service-account get github-deployer --format json | jq -r '.id')"
        echo "  FOLDER_ID=\$(yc config get folder-id)"
        echo "  yc resource-manager folder add-access-binding \$FOLDER_ID --role container-registry.images.pusher --subject serviceAccount:\$SA_ID"
        echo "  yc resource-manager folder add-access-binding \$FOLDER_ID --role serverless.containers.admin --subject serviceAccount:\$SA_ID"
    else
        echo "$SA_ID"
    fi
else
    yc iam service-account get github-deployer 2>/dev/null || echo "Not found"
fi
echo ""

# YC_SERVICE_ACCOUNT_KEY
echo -e "${YELLOW}YC_SERVICE_ACCOUNT_KEY:${NC}"
if [ -f "key.json" ]; then
    echo "Found existing key.json file"
    echo ""
    echo "Content (copy everything below):"
    echo "---START---"
    cat key.json
    echo ""
    echo "---END---"
else
    echo "key.json not found."
    echo ""
    echo "Create a new key with:"
    echo "  yc iam key create --service-account-name github-deployer --output key.json"
    echo ""
    echo "Then copy the ENTIRE content of key.json to GitHub Secret YC_SERVICE_ACCOUNT_KEY"
fi
echo ""

# RABBITMQ_URL
echo -e "${YELLOW}RABBITMQ_URL:${NC}"
echo "You need to provide RabbitMQ connection URL"
echo "Format: amqp://username:password@host:5672/"
echo ""
echo "Options:"
echo "  1. CloudAMQP (managed): https://www.cloudamqp.com/"
echo "  2. Yandex Message Queue: https://cloud.yandex.ru/services/message-queue"
echo "  3. Self-hosted RabbitMQ"
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Next Steps:${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "1. Go to your GitHub repository"
echo "2. Navigate to: Settings → Secrets and variables → Actions"
echo "3. Click 'New repository secret'"
echo "4. Add each secret with the values shown above:"
echo ""
echo "   Required secrets:"
echo "   - YC_SERVICE_ACCOUNT_KEY (entire JSON from key.json)"
echo "   - YC_REGISTRY_ID"
echo "   - YC_CLOUD_ID"
echo "   - YC_FOLDER_ID"
echo "   - YC_SERVICE_ACCOUNT_ID"
echo "   - RABBITMQ_URL"
echo ""
echo "5. Push changes to trigger the workflow:"
echo "   git add ."
echo "   git commit -m 'ci: configure accounts-service deployment'"
echo "   git push origin main"
echo ""
echo -e "${GREEN}Done!${NC}"

