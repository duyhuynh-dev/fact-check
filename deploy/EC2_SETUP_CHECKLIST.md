# EC2 Setup Checklist

Follow these steps in order to set up your backend on EC2:

## Pre-Deployment

- [ ] AWS account created and EC2 access configured
- [ ] EC2 instance launched (Ubuntu 22.04 LTS recommended)
- [ ] Security group configured:
  - [ ] SSH (22) from your IP
  - [ ] HTTP (80) from anywhere (0.0.0.0/0)
  - [ ] HTTPS (443) from anywhere (0.0.0.0/0)
- [ ] Key pair downloaded and permissions set: `chmod 400 your-key.pem`
- [ ] GitHub repository is accessible (or code ready to transfer)

## Step 1: Connect to EC2

```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

## Step 2: Clone Repository

```bash
# Clone your repository
git clone <your-repo-url> /opt/fact-check
cd /opt/fact-check

# OR if you need to use a specific branch:
git clone -b main <your-repo-url> /opt/fact-check
cd /opt/fact-check
```

## Step 3: Run Setup Script

```bash
# Make script executable
chmod +x deploy/ec2-setup.sh

# Run setup (this installs dependencies and configures services)
./deploy/ec2-setup.sh
```

**Expected output**: Script will install Python, Poetry, nginx, supervisor, and configure services.

## Step 4: Configure Environment Variables

```bash
# Copy example environment file
cp deploy/env.example.ec2 .env

# Edit with your settings
nano .env
```

**Required settings:**

- `GEMINI_API_KEY` - Your Gemini API key
- `CORS_ORIGINS` - Set to `https://*.vercel.app` (allows all Vercel deployments)
- `APP_ENV` - Set to `production`

**Optional settings:**

- `VERIFICATION_PROVIDER` - Default is `gemini`
- `CLAIM_EXTRACTOR` - Default is `spacy`

## Step 5: Download spaCy Model

```bash
cd /opt/fact-check
poetry run python -m spacy download en_core_web_sm
```

## Step 6: Create Data Directories

```bash
mkdir -p data/uploads data/processed vectorstore
chmod -R 755 data vectorstore
```

## Step 7: Start Services

```bash
# Start the backend service
sudo systemctl start fact-check

# Enable it to start on boot
sudo systemctl enable fact-check

# Check status
sudo systemctl status fact-check
```

## Step 8: Verify Backend is Running

```bash
# Test health endpoint
curl http://localhost:8000/healthz

# Should return: {"status":"ok"}

# Check logs if there are issues
sudo journalctl -u fact-check -f
```

## Step 9: Configure Domain (Optional)

If you have a domain name:

```bash
# Edit nginx config
sudo nano /etc/nginx/sites-available/fact-check

# Update server_name:
# server_name your-domain.com www.your-domain.com;

# Test nginx config
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

## Step 10: Set Up SSL (Recommended)

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Follow prompts to complete setup
```

## Step 11: Get Your Backend URL

- **With domain**: `https://your-domain.com`
- **Without domain**: `http://your-ec2-ip` (or Elastic IP if configured)

**Note**: You'll need this URL for the Vercel `NEXT_PUBLIC_API_URL` environment variable.

## Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u fact-check -n 50

# Check if port is in use
sudo lsof -i :8000

# Verify .env file exists and has correct values
cat /opt/fact-check/.env
```

### Permission errors

```bash
# Fix ownership
sudo chown -R $USER:$USER /opt/fact-check
sudo chown -R $USER:$USER /opt/fact-check/data
```

### CORS issues

- Verify `CORS_ORIGINS=https://*.vercel.app` in `.env`
- Restart service: `sudo systemctl restart fact-check`

### Port already in use

```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill if needed (replace PID)
sudo kill -9 <PID>
```

## Next Steps

After EC2 is set up:

1. Deploy frontend to Vercel
2. Set `NEXT_PUBLIC_API_URL` in Vercel to your EC2 backend URL
3. Test the full application

## Security Notes

- Keep your `.env` file secure (never commit it)
- Regularly update system packages: `sudo apt-get update && sudo apt-get upgrade`
- Consider setting up firewall rules (ufw)
- Monitor logs regularly: `sudo journalctl -u fact-check -f`
- Set up automated backups for the database
