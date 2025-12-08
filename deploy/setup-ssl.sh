#!/bin/bash
# SSL Setup Script for EC2 with DuckDNS domain
# Run this on your EC2 instance

set -euo pipefail

echo "🔒 Setting up SSL for backend..."

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "Installing nginx..."
    sudo apt-get update
    sudo apt-get install -y nginx
fi

# Install certbot
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    sudo apt-get install -y certbot python3-certbot-nginx
fi

# Get domain from user
read -p "Enter your DuckDNS domain (e.g., myapp.duckdns.org): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo "Error: Domain is required"
    exit 1
fi

# Create nginx configuration
sudo tee /etc/nginx/sites-available/fact-check > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    client_max_body_size 100M;

    # SSL will be configured by certbot
    # ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/fact-check /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx config
sudo nginx -t

# Get SSL certificate
echo "Getting SSL certificate from Let's Encrypt..."
echo "Make sure your DuckDNS domain points to this EC2 IP: $(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
read -p "Press Enter to continue after verifying DNS..."

sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN || {
    echo "Certbot failed. Make sure:"
    echo "1. Your DuckDNS domain points to this EC2 IP"
    echo "2. Port 80 and 443 are open in security group"
    exit 1
}

# Restart nginx
sudo systemctl restart nginx

echo "✅ SSL setup complete!"
echo "Your backend is now available at: https://$DOMAIN"
echo ""
echo "Update Vercel environment variable:"
echo "NEXT_PUBLIC_API_URL=https://$DOMAIN"

