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

# Function to check DNS resolution
check_dns() {
    local domain=$1
    print_debug "Checking DNS resolution for $domain..."

    if nslookup "$domain" > /dev/null 2>&1; then
        local ip=$(dig +short "$domain" A | head -n1)
        local server_ip=$(curl -s http://ipv4.icanhazip.com 2>/dev/null || echo "unknown")

        print_debug "Domain $domain resolves to: $ip"
        print_debug "Server public IP: $server_ip"

        if [ "$ip" = "$server_ip" ]; then
            print_status "✅ DNS resolution correct for $domain"
            return 0
        else
            print_warning "⚠️ DNS mismatch for $domain (points to $ip, server is $server_ip)"
            return 1
        fi
    else
        print_error "❌ DNS resolution failed for $domain"
        return 1
    fi
}

# Function to check port availability
check_port() {
    local port=$1
    if netstat -tuln | grep -q ":$port "; then
        print_warning "Port $port is already in use"
        return 1
    else
        print_status "Port $port is available"
        return 0
    fi
}

# Check DNS before proceeding with SSL
print_status "Checking DNS configuration..."
DNS_OK=true
check_dns "$DOMAIN" || DNS_OK=false
check_dns "www.$DOMAIN" || DNS_OK=false

if [ "$DNS_OK" = false ]; then
    print_warning "DNS issues detected. SSL certificate generation may fail."
    print_warning "Please ensure your domain points to this server's IP address."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if ports are available
print_status "Checking port availability..."
check_port 80
check_port 443

# Stop existing containers and free up ports
print_status "Stopping existing containers..."
docker-compose down --remove-orphans || true

# Wait for ports to be freed
sleep 5

# Check if we should use Let's Encrypt or self-signed certificates
USE_SELF_SIGNED=false

if command -v certbot &> /dev/null && [ -n "$EMAIL" ]; then
    print_status "Attempting to get Let's Encrypt certificate for $DOMAIN..."

    # Check if domain points to multiple IPs
    DOMAIN_IPS=$(dig +short "$DOMAIN" A | wc -l)
    if [ "$DOMAIN_IPS" -gt 1 ]; then
        print_warning "Domain points to multiple IP addresses ($DOMAIN_IPS IPs found). This may cause ACME HTTP challenge issues."
        print_warning "IPs found: $(dig +short "$DOMAIN" A | tr '\n' ' ')"
        print_warning "Current server IP: $(curl -s http://ipv4.icanhazip.com 2>/dev/null || echo "unknown")"
        print_warning "Consider removing extra DNS records or using DNS challenge method."

        # Try with single domain first (no www)
        print_status "Trying certificate for main domain only..."
    fi

    # Stop existing containers and services using port 80
    docker-compose down 2>/dev/null || true
    if pgrep nginx > /dev/null; then
        print_status "Stopping system nginx service..."
        sudo systemctl stop nginx 2>/dev/null || true
    fi

    # Kill any processes using port 80
    sudo fuser -k 80/tcp 2>/dev/null || true
    sleep 3

    # Try main domain first
    if certbot certonly \
        --standalone \
        --non-interactive \
        --agree-tos \
        --email "$EMAIL" \
        --domains "$DOMAIN" \
        --preferred-challenges http \
        --http-01-port 80 \
        --rsa-key-size 2048; then

        print_status "✅ Let's Encrypt certificate obtained for main domain!"

        # Try to expand to include www subdomain
        if [ "$DOMAIN_IPS" -le 1 ]; then
            print_status "Attempting to expand certificate to include www subdomain..."
            if certbot certonly \
                --standalone \
                --non-interactive \
                --agree-tos \
                --email "$EMAIL" \
                --domains "$DOMAIN,www.$DOMAIN" \
                --preferred-challenges http \
                --http-01-port 80 \
                --expand; then
                print_status "✅ Certificate expanded to include www subdomain!"
            else
                print_warning "Failed to expand certificate. Using certificate for main domain only."
            fi
        fi

        # Copy certificates to nginx directory
        sudo cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" nginx/ssl/cert.pem
        sudo cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" nginx/ssl/key.pem
        sudo chown $(whoami): nginx/ssl/*.pem

        # Set up certificate renewal
        echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'docker-compose restart nginx'" | crontab -
        print_status "Certificate auto-renewal set up"

    else
        print_warning "Let's Encrypt certificate generation failed. Using self-signed certificates."
        print_warning "This is likely due to multiple DNS A records pointing to different servers."
        print_warning "Please remove extra DNS records and try again."
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
        print_error "Failed to create SSL certificates. HTTPS might not work."
        exit 1
    }
fi

# Create improved nginx configuration
print_status "Creating nginx configuration..."
cat > nginx/conf.d/default.conf << 'EOF'
upstream django {
    server web:8000;
    keepalive 16;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=web:10m rate=10r/s;

server {
    listen 80;
    server_name DOMAIN_PLACEHOLDER www.DOMAIN_PLACEHOLDER;

    # ACME challenge location for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        allow all;
    }

    location /health/ {
        access_log off;
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 5s;
        proxy_read_timeout 10s;
    }

    location /static/ {
        alias /app/staticfiles/;
        expires 7d;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff;
    }

    location /media/ {
        alias /app/media/;
        expires 1d;
        add_header Cache-Control "public";
        add_header X-Content-Type-Options nosniff;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name DOMAIN_PLACEHOLDER www.DOMAIN_PLACEHOLDER;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security headers
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Rate limiting
    limit_req zone=web burst=20 nodelay;

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

    location /health/ {
        access_log off;
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 5s;
        proxy_read_timeout 10s;
    }

    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }
}
EOF

# Replace domain placeholder
sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" nginx/conf.d/default.conf

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
print_debug "Checking web container status..."
if docker-compose ps web | grep -q "Up"; then
    print_status "✅ Web container is running"
else
    print_error "❌ Web container failed to start"
    docker-compose logs web
    exit 1
fi

# Enhanced health check with retries for the domain
print_status "Performing health check with retries for $DOMAIN..."
MAX_RETRIES=15
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Try local health check first
    if curl -f -H "Host: $DOMAIN" http://localhost/health/ > /dev/null 2>&1; then
        print_status "✅ Local health check passed!"
        break
    elif curl -f -k https://localhost/health/ > /dev/null 2>&1; then
        print_status "✅ Local HTTPS health check passed!"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        print_warning "Health check attempt $RETRY_COUNT/$MAX_RETRIES failed. Retrying in 10 seconds..."

        if [ $((RETRY_COUNT % 3)) -eq 0 ]; then
            print_debug "Checking container status..."
            docker-compose ps
        fi

        sleep 10
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "❌ Health check failed after $MAX_RETRIES attempts."
    print_error "Debugging information:"
    echo
    print_error "Container status:"
    docker-compose ps
    echo
    print_error "Web container logs:"
    docker-compose logs web | tail -30
    echo
    print_error "Nginx container logs:"
    docker-compose logs nginx | tail -30

    print_error "Network information:"
    docker network ls
    docker network inspect $(docker-compose ps -q | head -1 | xargs docker inspect --format='{{range $net,$conf := .NetworkSettings.Networks}}{{$net}}{{end}}') | grep -A 10 -B 10 Subnet || true

    exit 1
fi

# Run Django migrations (with better error handling)
print_status "Running database migrations..."
if docker-compose exec -T web python manage.py migrate --noinput; then
    print_status "✅ Migrations completed successfully"
else
    print_warning "⚠️ Migrations failed or not needed"
    docker-compose logs web | tail -10
fi

# Collect static files (with better error handling)
print_status "Collecting static files..."
if docker-compose exec -T web python manage.py collectstatic --noinput; then
    print_status "✅ Static files collected successfully"
else
    print_warning "⚠️ Static files collection failed"
    docker-compose logs web | tail -10
fi

# Final comprehensive health check
print_status "Performing final health checks..."
sleep 5

# Check all endpoints
HEALTH_CHECKS=0
TOTAL_CHECKS=4

# Local HTTP health check
if curl -f -H "Host: $DOMAIN" http://localhost/health/ > /dev/null 2>&1; then
    print_status "✅ Local HTTP health check passed"
    HEALTH_CHECKS=$((HEALTH_CHECKS + 1))
fi

# Local HTTPS health check
if curl -f -k https://localhost/health/ > /dev/null 2>&1; then
    print_status "✅ Local HTTPS health check passed"
    HEALTH_CHECKS=$((HEALTH_CHECKS + 1))
fi

# External HTTP health check (if DNS is working)
if [ "$DNS_OK" = true ]; then
    if curl -f http://$DOMAIN/health/ > /dev/null 2>&1; then
        print_status "✅ External HTTP health check passed"
        HEALTH_CHECKS=$((HEALTH_CHECKS + 1))
    fi

    # External HTTPS health check
    if curl -f -k https://$DOMAIN/health/ > /dev/null 2>&1; then
        print_status "✅ External HTTPS health check passed"
        HEALTH_CHECKS=$((HEALTH_CHECKS + 1))
    fi
else
    TOTAL_CHECKS=2  # Only count local checks if DNS is not working
fi

print_status "Health checks passed: $HEALTH_CHECKS/$TOTAL_CHECKS"

# Display container status
print_status "Container status:"
docker-compose ps

# Display resource usage
print_status "Resource usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || print_warning "Could not get resource usage stats"

# Display useful information
echo
print_status "🎉 Deployment completed for $DOMAIN!"
echo
echo "Your application should be available at:"
echo "  - HTTP: http://$DOMAIN (redirects to HTTPS)"
echo "  - HTTPS: https://$DOMAIN"
echo "  - WWW: https://www.$DOMAIN"
echo

if [ "$DNS_OK" = false ]; then
    print_warning "⚠️ DNS ISSUES DETECTED!"
    echo "Your domain is not pointing to this server. Please update your DNS settings:"
    echo "  1. Point $DOMAIN to your server's IP address"
    echo "  2. Point www.$DOMAIN to your server's IP address"
    echo "  3. Wait for DNS propagation (up to 48 hours)"
    echo "  4. Re-run this script to get a proper SSL certificate"
    echo
fi

echo "Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Restart services: docker-compose restart"
echo "  - Stop services: docker-compose down"
echo "  - Check status: docker-compose ps"
echo "  - Shell into web container: docker-compose exec web bash"
echo "  - Check nginx config: docker-compose exec nginx nginx -t"
echo
echo "If you're still having issues:"
echo "  1. Check the logs: docker-compose logs"
echo "  2. Verify your .env file settings"
echo "  3. Ensure your Django app has a /health/ endpoint"
echo "  4. Check DNS configuration for $DOMAIN"
echo "  5. Verify ports 80/443 are open in your firewall"
echo "  6. Check if any other services are using ports 80/443"
echo

if [ "$USE_SELF_SIGNED" = true ]; then
    print_warning "Using self-signed certificates. Browser will show security warnings!"
    echo "To get a Let's Encrypt certificate:"
    echo "  1. Ensure DNS is properly configured"
    echo "  2. Install certbot: sudo apt-get install certbot"
    echo "  3. Re-run this script"
fi

# Show final status
if [ $HEALTH_CHECKS -gt 0 ]; then
    print_status "✅ Deployment appears successful!"
else
    print_warning "⚠️ Deployment completed but health checks failed. Check logs for issues."
fi