#!/bin/bash

# Deployment script for Deep Lake Vector Service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
ENVIRONMENT="development"
BUILD_IMAGE=false
PUSH_IMAGE=false
DEPLOY_K8S=false
IMAGE_TAG="latest"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --build)
            BUILD_IMAGE=true
            shift
            ;;
        --push)
            PUSH_IMAGE=true
            shift
            ;;
        --k8s)
            DEPLOY_K8S=true
            shift
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --env ENV       Environment (development|staging|production)"
            echo "  --build         Build Docker image"
            echo "  --push          Push Docker image to registry"
            echo "  --k8s           Deploy to Kubernetes"
            echo "  --tag TAG       Docker image tag (default: latest)"
            echo "  --help          Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

echo "Deploying Deep Lake Vector Service..."
echo "Environment: $ENVIRONMENT"
echo "Project root: $PROJECT_ROOT"

# Change to project root
cd "$PROJECT_ROOT"

# Build Docker image if requested
if [ "$BUILD_IMAGE" = true ]; then
    echo "Building Docker image..."
    docker build -t "deeplake-service:${IMAGE_TAG}" .
    echo "Docker image built: deeplake-service:${IMAGE_TAG}"
fi

# Push Docker image if requested
if [ "$PUSH_IMAGE" = true ]; then
    echo "Pushing Docker image..."
    # Adjust registry URL as needed
    REGISTRY_URL="your-registry.com"
    docker tag "deeplake-service:${IMAGE_TAG}" "${REGISTRY_URL}/deeplake-service:${IMAGE_TAG}"
    docker push "${REGISTRY_URL}/deeplake-service:${IMAGE_TAG}"
    echo "Docker image pushed: ${REGISTRY_URL}/deeplake-service:${IMAGE_TAG}"
fi

# Deploy based on environment
case $ENVIRONMENT in
    development)
        echo "Starting development environment with Docker Compose..."
        docker-compose up -d
        echo "Development environment started!"
        echo "HTTP API: http://localhost:8000"
        echo "gRPC API: localhost:50051"
        echo "Grafana: http://localhost:3000 (admin/admin)"
        echo "Prometheus: http://localhost:9090"
        ;;
    
    staging|production)
        if [ "$DEPLOY_K8S" = true ]; then
            echo "Deploying to Kubernetes ($ENVIRONMENT)..."
            
            # Apply Kubernetes manifests
            kubectl apply -f deployment/kubernetes/namespace.yaml
            kubectl apply -f deployment/kubernetes/configmap.yaml
            kubectl apply -f deployment/kubernetes/secret.yaml
            kubectl apply -f deployment/kubernetes/deployment.yaml
            kubectl apply -f deployment/kubernetes/service.yaml
            kubectl apply -f deployment/kubernetes/ingress.yaml
            kubectl apply -f deployment/kubernetes/hpa.yaml
            
            # Wait for deployment to be ready
            echo "Waiting for deployment to be ready..."
            kubectl wait --for=condition=available --timeout=300s deployment/deeplake-service -n deeplake
            
            # Show status
            kubectl get pods -n deeplake
            kubectl get services -n deeplake
            kubectl get ingress -n deeplake
            
            echo "Kubernetes deployment completed!"
        else
            echo "Use --k8s flag to deploy to Kubernetes"
        fi
        ;;
        
    *)
        echo "Unknown environment: $ENVIRONMENT"
        exit 1
        ;;
esac

echo "Deployment completed successfully!"