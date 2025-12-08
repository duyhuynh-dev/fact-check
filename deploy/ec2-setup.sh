#!/bin/bash
# EC2 Deployment Setup Script
# Run this script on your EC2 instance to set up the backend

set -euo pipefail

echo "🚀 Setting up Fact-Check Backend on EC2..."

# Update system
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip nginx supervisor

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"

# Create application directory
APP_DIR="/opt/fact-check"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Clone repository (or copy files)
# git clone <your-repo-url> $APP_DIR
# OR copy files via scp/rsync

cd $APP_DIR

# Install dependencies
poetry install --no-dev

# Download spaCy model
poetry run python -m spacy download en_core_web_sm

# Create necessary directories
mkdir -p data/uploads data/processed vectorstore

# Set up environment file (you'll need to create this with your API keys)
# cp .env.example .env
# nano .env  # Add your GEMINI_API_KEY and other settings

# Create systemd service
sudo tee /etc/systemd/system/fact-check.service > /dev/null <<EOF
[Unit]
Description=Fact-Check Backend API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin:$PATH"
ExecStart=$HOME/.local/bin/poetry run uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create nginx configuration
sudo tee /etc/nginx/sites-available/fact-check > /dev/null <<EOF
server {
    listen 80;
    server_name _;  # Replace with your domain name

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable nginx site
sudo ln -sf /etc/nginx/sites-available/fact-check /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Start services
sudo systemctl daemon-reload
sudo systemctl enable fact-check
sudo systemctl start fact-check
sudo systemctl restart nginx

echo "✅ Setup complete!"
echo "📝 Next steps:"
echo "   1. Configure your .env file with API keys"
echo "   2. Update nginx server_name with your domain"
echo "   3. Set up SSL with Let's Encrypt: sudo certbot --nginx"
echo "   4. Configure security group to allow HTTP/HTTPS traffic"
echo ""
echo "Check status: sudo systemctl status fact-check"
echo "View logs: sudo journalctl -u fact-check -f"
