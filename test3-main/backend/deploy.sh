#!/bin/bash

# Deployment script for Django application
set -e

echo "🚀 Starting deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check available memory
AVAILABLE_MEMORY=$(free -m | awk 'NR==2{printf "%.0f", $7}')
if [ "$AVAILABLE_MEMORY" -lt 512 ]; then
    print_warning "Available memory is ${AVAILABLE_MEMORY}MB. Consider upgrading your server for better performance."
fi

# Stop existing containers
print_status "Stopping existing containers..."
docker-compose down --remove-orphans || true

# Clean up old images to free space
print_status "Cleaning up old Docker images..."
docker system prune -f || true

# Build and start containers
print_status "Building and starting containers..."
docker-compose up --build -d

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 30

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    print_status "Services are running!"
else
    print_error "Some services failed to start. Check the logs:"
    docker-compose logs
    exit 1
fi

# Run Django migrations
print_status "Running database migrations..."
docker-compose exec -T web python manage.py migrate || print_warning "Migrations failed or not needed"

# Collect static files
print_status "Collecting static files..."
docker-compose exec -T web python manage.py collectstatic --noinput || print_warning "Static files collection failed"

# Health check
print_status "Performing health check..."
sleep 10
if curl -f http://localhost/health/ > /dev/null 2>&1; then
    print_status "✅ Health check passed!"
else
    print_warning "Health check failed, but services might still be starting..."
fi

# Display container status
print_status "Container status:"
docker-compose ps

# Display useful information
print_status "🎉 Deployment completed!"
echo
echo "Your application should be available at:"
echo "  - HTTP: http://your-server-ip"
echo "  - HTTPS: https://your-server-ip"
echo
echo "To view logs:"
echo "  docker-compose logs -f"
echo
echo "To restart services:"
echo "  docker-compose restart"
echo
echo "To stop services:"
echo "  docker-compose down"