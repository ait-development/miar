#!/bin/bash

# Deployment script for audit-service to Yandex Cloud Serverless Containers
# Usage: ./scripts/deploy_audit_service.sh [environment]
# Example: ./scripts/deploy_audit_service.sh production

set -e

# Configuration
SERVICE_NAME="audit-service"
ENVIRONMENT="${1:-production}"
REGISTRY_ID="${YC_REGISTRY_ID}"
IMAGE_NAME="audit-service"
CONTAINER_NAME="audit-service-container"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if required environment variables are set
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    if ! command -v yc &> /dev/null; then
        echo -e "${RED}Error: Yandex Cloud CLI (yc) is not installed${NC}"
        echo "Install it from: https://cloud.yandex.ru/docs/cli/quickstart"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        exit 1
    fi
    
    if [ -z "$YC_REGISTRY_ID" ]; then
        echo -e "${RED}Error: YC_REGISTRY_ID environment variable is not set${NC}"
        exit 1
    fi
    
    if [ -z "$YC_FOLDER_ID" ]; then
        echo -e "${RED}Error: YC_FOLDER_ID environment variable is not set${NC}"
        exit 1
    fi
    
    if [ -z "$YC_SERVICE_ACCOUNT_ID" ]; then
        echo -e "${RED}Error: YC_SERVICE_ACCOUNT_ID environment variable is not set${NC}"
        exit 1
    fi
    
    if [ -z "$RABBITMQ_URL" ]; then
        echo -e "${YELLOW}Warning: RABBITMQ_URL is not set. Using default value.${NC}"
        RABBITMQ_URL="amqp://guest:guest@localhost:5672/"
    fi
    
    echo -e "${GREEN}Prerequisites check passed!${NC}"
}

# Build Docker image
build_image() {
    echo -e "${YELLOW}Building Docker image...${NC}"
    
    IMAGE_TAG="cr.yandex/${REGISTRY_ID}/${IMAGE_NAME}:$(git rev-parse --short HEAD || echo 'latest')"
    
    docker build \
        -f services/audit-service/Dockerfile \
        -t "${IMAGE_TAG}" \
        -t "cr.yandex/${REGISTRY_ID}/${IMAGE_NAME}:latest" \
        .
    
    echo -e "${GREEN}Image built successfully: ${IMAGE_TAG}${NC}"
}

# Push image to Yandex Container Registry
push_image() {
    echo -e "${YELLOW}Pushing image to Yandex Container Registry...${NC}"
    
    # Configure Docker to use Yandex Container Registry
    yc container registry configure-docker
    
    IMAGE_TAG="cr.yandex/${REGISTRY_ID}/${IMAGE_NAME}:$(git rev-parse --short HEAD || echo 'latest')"
    
    docker push "${IMAGE_TAG}"
    docker push "cr.yandex/${REGISTRY_ID}/${IMAGE_NAME}:latest"
    
    echo -e "${GREEN}Image pushed successfully!${NC}"
}

# Deploy to Serverless Containers
deploy_container() {
    echo -e "${YELLOW}Deploying to Yandex Cloud Serverless Containers...${NC}"
    
    IMAGE_TAG="cr.yandex/${REGISTRY_ID}/${IMAGE_NAME}:$(git rev-parse --short HEAD || echo 'latest')"
    
    # Check if container exists
    CONTAINER_ID=$(yc serverless container list --folder-id "$YC_FOLDER_ID" --format json | \
        jq -r ".[] | select(.name==\"${CONTAINER_NAME}\") | .id")
    
    if [ -z "$CONTAINER_ID" ]; then
        echo -e "${YELLOW}Creating new serverless container...${NC}"
        yc serverless container create \
            --name "${CONTAINER_NAME}" \
            --description "Audit Service - Serverless Container (${ENVIRONMENT})" \
            --folder-id "$YC_FOLDER_ID"
    else
        echo -e "${GREEN}Container already exists with ID: ${CONTAINER_ID}${NC}"
    fi
    
    # Deploy new revision
    echo -e "${YELLOW}Deploying new revision...${NC}"
    yc serverless container revision deploy \
        --container-name "${CONTAINER_NAME}" \
        --image "${IMAGE_TAG}" \
        --cores 1 \
        --memory 512MB \
        --execution-timeout 30s \
        --concurrency 4 \
        --service-account-id "$YC_SERVICE_ACCOUNT_ID" \
        --folder-id "$YC_FOLDER_ID" \
        --environment SERVICE_NAME=audit-service \
        --environment SERVICE_ROLE=audit \
        --environment SERVICE_PORT=8000 \
        --environment SLEEP_SYMBOL=- \
        --environment RABBITMQ_URL="$RABBITMQ_URL"
    
    echo -e "${GREEN}Deployment successful!${NC}"
}

# Get container URL and test
test_deployment() {
    echo -e "${YELLOW}Testing deployment...${NC}"
    
    CONTAINER_URL=$(yc serverless container get "${CONTAINER_NAME}" \
        --folder-id "$YC_FOLDER_ID" \
        --format json | jq -r '.url')
    
    if [ -z "$CONTAINER_URL" ] || [ "$CONTAINER_URL" == "null" ]; then
        echo -e "${RED}Error: Could not get container URL${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Container URL: ${CONTAINER_URL}${NC}"
    
    # Wait for container to be ready
    echo -e "${YELLOW}Waiting for container to be ready...${NC}"
    sleep 10
    
    # Test health endpoint
    if curl -f -s "${CONTAINER_URL}/health" > /dev/null; then
        echo -e "${GREEN}Health check passed!${NC}"
        
        # Display health check response
        echo -e "${YELLOW}Health check response:${NC}"
        curl -s "${CONTAINER_URL}/health" | jq '.'
    else
        echo -e "${RED}Health check failed!${NC}"
        echo -e "${YELLOW}Container may still be starting up. Check logs with:${NC}"
        echo "yc serverless container revision logs --container-name ${CONTAINER_NAME} --folder-id ${YC_FOLDER_ID}"
    fi
}

# Main execution
main() {
    echo -e "${GREEN}=== Deploying Audit Service to Yandex Cloud ===${NC}"
    echo -e "Environment: ${ENVIRONMENT}"
    echo ""
    
    check_prerequisites
    build_image
    push_image
    deploy_container
    test_deployment
    
    echo -e "${GREEN}=== Deployment completed successfully! ===${NC}"
}

# Run main function
main

