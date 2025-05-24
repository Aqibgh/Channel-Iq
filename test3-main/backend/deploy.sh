#!/bin/bash

# Deployment script for Django application - channel-iq.nzxtsol.com
set -e

echo "🚀 Starting deployment for channel-iq.nzxtsol.com..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Domain configuration
DOMAIN="channel-iq.nzxtsol.com"
EMAIL="nzxtbiz@gmail.com"  # Change this to your email for Let's Encrypt

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

print_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
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

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p nginx/conf.d nginx/ssl logs

# Check if we should use Let's Encrypt or self-signed certificates
if command -v certbot &> /dev/null && [ -n "$EMAIL" ]; then
    print_status "Attempting to get Let's Encrypt certificate for $DOMAIN..."
    
    # Stop nginx if running to free port 80
    docker-compose down nginx 2>/dev/null || true
    
    # Try to get Let's Encrypt certificate
    if certbot certonly --standalone --non-interactive --agree-tos --email "$EMAIL" -d "$DOMAIN" -d "www.$DOMAIN"; then
        print_status "✅ Let's Encrypt certificate obtained successfully!"
        
        # Copy certificates to nginx directory
        cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem nginx/ssl/cert.pem
        cp /etc/letsencrypt/live/$DOMAIN/privkey.pem nginx/ssl/key.pem
        
        # Set up certificate renewal
        echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'docker-compose restart nginx'" | crontab -
        print_status "Certificate auto-renewal set up"
    else
        print_warning "Let's Encrypt certificate generation failed. Using self-signed certificates."
        USE_SELF_SIGNED=true
    fi
else
    print_warning "Certbot not available or email not provided. Using self-signed certificates."
    USE_SELF_SIGNED=true
fi

# Create self-signed SSL certificates if needed
if [ "$USE_SELF_SIGNED" = true ] || [ ! -f nginx/ssl/cert.pem ] || [ ! -f nginx/ssl/key.pem ]; then
    print_status "Creating self-signed SSL certificates for $DOMAIN..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/key.pem \
        -out nginx/ssl/cert.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN" 2>/dev/null || {
        print_warning "Failed to create SSL certificates. HTTPS might not work."
    }
fi

# Handle nginx configuration
if [ -f "nginx.conf" ]; then
    print_status "Copying nginx.conf to nginx/conf.d/default.conf..."
    cp nginx.conf nginx/conf.d/default.conf
elif [ -f "nginx/conf.d/default.conf" ]; then
    print_status "Using existing nginx configuration at nginx/conf.d/default.conf"
elif [ -f "nginx/conf.d/nginx.conf" ]; then
    print_status "Using existing nginx configuration at nginx/conf.d/nginx.conf"
    mv nginx/conf.d/nginx.conf nginx/conf.d/default.conf
else
    print_error "No nginx configuration found. Creating a basic one for $DOMAIN..."
    cat > nginx/conf.d/default.conf << EOF
upstream django {
    server web:8000;
    keepalive 16;
}

server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location /health/ {
        access_log off;
        proxy_pass http://django;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 5s;
        proxy_read_timeout 10s;
    }

    location /static/ {
        alias /app/staticfiles/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /app/media/;
        expires 1d;
        add_header Cache-Control "public";
    }
    
    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    location / {
        proxy_pass http://django;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_read_timeout 300s;
    }
}
EOF
    print_status "Basic nginx configuration created at nginx/conf.d/default.conf"
fi

# Stop existing containers
print_status "Stopping existing containers..."
docker-compose down --remove-orphans || true

# Clean up old images to free space
print_status "Cleaning up old Docker images..."
docker system prune -f || true

# Check if .env file exists and update it with the domain
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating one for $DOMAIN..."
    cat > .env << EOF
DJANGO_SECRET_KEY=your-secret-key-here-$(openssl rand -hex 32)
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN
DATABASE_URL=sqlite:///app/data/db.sqlite3
EOF
else
    # Update existing .env file with domain settings
    print_status "Updating .env file with domain configuration..."
    
    # Update ALLOWED_HOSTS if it exists
    if grep -q "DJANGO_ALLOWED_HOSTS" .env; then
        sed -i "s/DJANGO_ALLOWED_HOSTS=.*/DJANGO_ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN,localhost,127.0.0.1/" .env
    else
        echo "DJANGO_ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN,localhost,127.0.0.1" >> .env
    fi
    
    # Add CSRF_TRUSTED_ORIGINS if not present
    if ! grep -q "DJANGO_CSRF_TRUSTED_ORIGINS" .env; then
        echo "DJANGO_CSRF_TRUSTED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN" >> .env
    fi
fi

# Build and start containers
print_status "Building and starting containers..."
docker-compose up --build -d

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 30

# Check web container logs for issues
print_debug "Checking web container logs..."
docker-compose logs web | tail -10

# Enhanced health check with retries for the domain
print_status "Performing health check with retries for $DOMAIN..."
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Try both HTTP and HTTPS
    if curl -f -H "Host: $DOMAIN" http://localhost/health/ > /dev/null 2>&1 || \
       curl -f -k https://localhost/health/ > /dev/null 2>&1; then
        print_status "✅ Health check passed!"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        print_warning "Health check attempt $RETRY_COUNT/$MAX_RETRIES failed. Retrying in 10 seconds..."
        sleep 10
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "❌ Health check failed after $MAX_RETRIES attempts."
    print_error "Checking container status and logs..."
    docker-compose ps
    echo
    print_error "Web container logs:"
    docker-compose logs web | tail -20
    echo
    print_error "Nginx container logs:"
    docker-compose logs nginx | tail -20
    exit 1
fi

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    print_status "Services are running!"
else
    print_error "Some services failed to start. Check the logs:"
    docker-compose logs
    exit 1
fi

# Wait a bit more for Django to fully initialize
print_status "Waiting for Django to fully initialize..."
sleep 10

# Run Django migrations (with better error handling)
print_status "Running database migrations..."
if docker-compose exec -T web python manage.py migrate; then
    print_status "✅ Migrations completed successfully"
else
    print_warning "⚠️ Migrations failed or not needed"
fi

# Collect static files (with better error handling)
print_status "Collecting static files..."
if docker-compose exec -T web python manage.py collectstatic --noinput; then
    print_status "✅ Static files collected successfully"
else
    print_warning "⚠️ Static files collection failed"
fi

# Final health check
print_status "Performing final health check..."
sleep 5
if curl -f -H "Host: $DOMAIN" http://localhost/health/ > /dev/null 2>&1; then
    print_status "✅ Final health check passed!"
else
    print_warning "⚠️ Final health check failed, but services might still be working"
fi

# Display container status
print_status "Container status:"
docker-compose ps

# Display resource usage
print_status "Resource usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Display useful information
echo
print_status "🎉 Deployment completed for $DOMAIN!"
echo
echo "Your application should be available at:"
echo "  - HTTP: http://$DOMAIN (redirects to HTTPS)"
echo "  - HTTPS: https://$DOMAIN"
echo "  - WWW: https://www.$DOMAIN"
echo
print_warning "Make sure your DNS is pointing to this server's IP address!"
echo
echo "Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Restart services: docker-compose restart"
echo "  - Stop services: docker-compose down"
echo "  - Check status: docker-compose ps"
echo "  - Shell into web container: docker-compose exec web bash"
echo
echo "If you're still having issues:"
echo "  1. Check the logs: docker-compose logs"
echo "  2. Verify your .env file settings"
echo "  3. Ensure your Django app has a /health/ endpoint"
echo "  4. Check DNS configuration for $DOMAIN"
echo "  5. Verify ports 80/443 are open in your firewall"
echo
if [ "$USE_SELF_SIGNED" = true ]; then
    print_warning "Using self-signed certificates. Consider getting a proper SSL certificate for production!"
    echo "To get a Let's Encrypt certificate, install certbot and run this script again."
fi