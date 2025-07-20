#!/bin/bash

# CloudArb API Credentials Setup Script
# This script helps you set up all required API credentials for real integrations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f .env ]; then
        log "Creating .env file from template..."
        cp env.template .env
        warn "Please edit .env file with your actual API credentials"
    else
        log ".env file already exists"
    fi
}

# Test AWS credentials
test_aws_credentials() {
    info "Testing AWS credentials..."

    if command -v aws &> /dev/null; then
        if aws sts get-caller-identity &> /dev/null; then
            log "✅ AWS credentials are working"
            aws sts get-caller-identity
        else
            error "❌ AWS credentials are not working. Please check your .env file"
        fi
    else
        warn "AWS CLI not installed. Installing..."
        install_aws_cli
    fi
}

# Install AWS CLI
install_aws_cli() {
    info "Installing AWS CLI..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
        unzip awscliv2.zip
        sudo ./aws/install
        rm -rf aws awscliv2.zip
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
        sudo installer -pkg AWSCLIV2.pkg -target /
        rm AWSCLIV2.pkg
    else
        error "Unsupported OS for AWS CLI installation"
    fi

    log "AWS CLI installed successfully"
}

# Test GCP credentials
test_gcp_credentials() {
    info "Testing GCP credentials..."

    if command -v gcloud &> /dev/null; then
        if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
            log "✅ GCP credentials are working"
            gcloud config list
        else
            warn "❌ GCP not authenticated. Please run: gcloud auth login"
        fi
    else
        warn "Google Cloud SDK not installed. Installing..."
        install_gcp_sdk
    fi
}

# Install Google Cloud SDK
install_gcp_sdk() {
    info "Installing Google Cloud SDK..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl https://sdk.cloud.google.com | bash
        exec -l $SHELL
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        curl https://sdk.cloud.google.com | bash
        exec -l $SHELL
    else
        error "Unsupported OS for Google Cloud SDK installation"
    fi

    log "Google Cloud SDK installed successfully"
    warn "Please run: gcloud auth login"
}

# Test Azure credentials
test_azure_credentials() {
    info "Testing Azure credentials..."

    if command -v az &> /dev/null; then
        if az account show &> /dev/null; then
            log "✅ Azure credentials are working"
            az account show --query "{name:name, id:id, tenantId:tenantId}" -o table
        else
            warn "❌ Azure not authenticated. Please run: az login"
        fi
    else
        warn "Azure CLI not installed. Installing..."
        install_azure_cli
    fi
}

# Install Azure CLI
install_azure_cli() {
    info "Installing Azure CLI..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew update && brew install azure-cli
    else
        error "Unsupported OS for Azure CLI installation"
    fi

    log "Azure CLI installed successfully"
    warn "Please run: az login"
}

# Test Lambda Labs API
test_lambda_api() {
    info "Testing Lambda Labs API..."

    if [ -n "$LAMBDA_API_KEY" ] && [ "$LAMBDA_API_KEY" != "your_lambda_api_key_here" ]; then
        response=$(curl -s -H "Authorization: Bearer $LAMBDA_API_KEY" \
            "https://cloud.lambdalabs.com/api/v1/instances" || echo "error")

        if [[ "$response" != "error" ]]; then
            log "✅ Lambda Labs API is working"
        else
            warn "❌ Lambda Labs API test failed. Check your API key"
        fi
    else
        warn "Lambda Labs API key not configured in .env file"
    fi
}

# Test RunPod API
test_runpod_api() {
    info "Testing RunPod API..."

    if [ -n "$RUNPOD_API_KEY" ] && [ "$RUNPOD_API_KEY" != "your_runpod_api_key_here" ]; then
        response=$(curl -s -H "Authorization: Bearer $RUNPOD_API_KEY" \
            "https://api.runpod.io/v2/pods/pricing" || echo "error")

        if [[ "$response" != "error" ]]; then
            log "✅ RunPod API is working"
        else
            warn "❌ RunPod API test failed. Check your API key"
        fi
    else
        warn "RunPod API key not configured in .env file"
    fi
}

# Load environment variables
load_env() {
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
    else
        error ".env file not found. Please run setup first."
    fi
}

# Main setup function
main() {
    log "🚀 CloudArb API Credentials Setup"
    log "=================================="

    # Check and create .env file
    check_env_file

    # Load environment variables
    load_env

    # Test each provider
    log "\n📋 Testing API Credentials..."
    log "=============================="

    test_aws_credentials
    test_gcp_credentials
    test_azure_credentials
    test_lambda_api
    test_runpod_api

    log "\n✅ Credentials setup completed!"
    log "\n📝 Next Steps:"
    log "1. Edit .env file with your actual API credentials"
    log "2. Run this script again to test all credentials"
    log "3. Start the real pricing collector: python -m cloudarb.services.real_pricing_collector"
    log "4. Run the proof of value demo: python scripts/proof_of_value_demo.py"
}

# Run main function
main "$@"