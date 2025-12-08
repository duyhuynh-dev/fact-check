# Deployment Guide

This guide covers deploying the Fact-Check application with:

- **Backend**: AWS EC2 instance
- **Frontend**: Vercel

## Prerequisites

- AWS account with EC2 access
- Vercel account
- Domain name (optional, but recommended)
- GitHub repository (for Vercel integration)

## Backend Deployment (EC2)

### 1. Launch EC2 Instance

1. Go to AWS EC2 Console
2. Launch a new instance:
   - **AMI**: Ubuntu 22.04 LTS
   - **Instance Type**: t3.medium or larger (recommended for ML workloads)
   - **Storage**: 20GB+ (for models and data)
   - **Security Group**: Allow HTTP (80), HTTPS (443), and SSH (22)

### 2. Connect to EC2 Instance

```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

### 3. Run Setup Script

```bash
# Clone your repository
git clone <your-repo-url> /opt/fact-check
cd /opt/fact-check

# Make setup script executable
chmod +x deploy/ec2-setup.sh

# Run setup (this will install dependencies and configure services)
./deploy/ec2-setup.sh
```

### 4. Configure Environment Variables

Create `.env` file in `/opt/fact-check`:

```bash
cd /opt/fact-check
nano .env
```

Add your configuration:

```env
APP_ENV=production
DATABASE_DSN=sqlite:///./factcheck.db
GEMINI_API_KEY=your_gemini_api_key_here
VERIFICATION_PROVIDER=gemini
CLAIM_EXTRACTOR=spacy
INGEST_BUCKET_PATH=./data/uploads
PROCESSED_TEXT_PATH=./data/processed
VECTORSTORE_PATH=./vectorstore
```

### 5. Configure CORS Settings

Update your `.env` file with CORS origins. The configuration supports wildcards:

```bash
# Allow all Vercel deployments (recommended)
CORS_ORIGINS=https://*.vercel.app

# Or specify exact domains
CORS_ORIGINS=https://your-app.vercel.app,https://your-custom-domain.com
```

**Note**: The wildcard pattern `*.vercel.app` will automatically allow all Vercel deployments (production, preview, and branch deployments), so you don't need to update CORS settings for each deployment!

### 6. Configure Nginx Domain (Optional)

If you have a domain name:

```bash
sudo nano /etc/nginx/sites-available/fact-check
```

Update `server_name`:

```nginx
server_name your-domain.com www.your-domain.com;
```

### 7. Set Up SSL with Let's Encrypt

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

### 8. Restart Services

```bash
sudo systemctl restart fact-check
sudo systemctl restart nginx
```

### 9. Verify Backend is Running

```bash
# Check service status
sudo systemctl status fact-check

# Check logs
sudo journalctl -u fact-check -f

# Test health endpoint
curl http://localhost:8000/healthz
```

### 10. Get Your Backend URL

- If using domain: `https://your-domain.com`
- If using EC2 IP: `http://your-ec2-ip` (or configure Elastic IP)

## Frontend Deployment (Vercel)

### 1. Install Vercel CLI (Optional)

```bash
npm i -g vercel
```

### 2. Deploy via Vercel Dashboard

1. Go to [vercel.com](https://vercel.com)
2. Click "New Project"
3. Import your GitHub repository
4. Configure project:
   - **Framework Preset**: Other
   - **Root Directory**: Leave empty (or set to project root)
   - **Build Command**: `bash deploy/vercel-build.sh`
   - **Output Directory**: `frontend`

### 3. Set Environment Variables

In Vercel project settings, add:

- **NEXT_PUBLIC_API_URL**: Your EC2 backend URL (e.g., `https://your-domain.com` or `http://your-ec2-ip`)

### 4. Deploy

Click "Deploy" and wait for the build to complete.

### 5. Configure Backend CORS (One-Time Setup)

Update your EC2 `.env` file with CORS origins. Use wildcard pattern to allow all Vercel deployments:

```bash
# In /opt/fact-check/.env
CORS_ORIGINS=https://*.vercel.app
```

Then restart the backend:

```bash
sudo systemctl restart fact-check
```

**Note**: With the wildcard pattern `*.vercel.app`, you only need to configure this once. All Vercel deployments (production, preview, branch deployments) will automatically work without needing to update CORS settings!

## Alternative: Deploy via Vercel CLI

```bash
# Login to Vercel
vercel login

# Set environment variable
vercel env add NEXT_PUBLIC_API_URL

# Deploy
vercel --prod
```

## Post-Deployment Checklist

- [ ] Backend health check returns `{"status":"ok"}`
- [ ] Frontend loads correctly
- [ ] File upload works from frontend
- [ ] CORS is configured correctly
- [ ] SSL certificate is active (if using domain)
- [ ] Environment variables are set correctly
- [ ] Database is accessible and writable
- [ ] Logs are being generated correctly

## Troubleshooting

### Backend Issues

**Service won't start:**

```bash
sudo journalctl -u fact-check -n 50
```

**Check if port is in use:**

```bash
sudo lsof -i :8000
```

**Restart services:**

```bash
sudo systemctl restart fact-check
sudo systemctl restart nginx
```

### Frontend Issues

**API calls failing:**

- Check browser console for CORS errors
- Verify `NEXT_PUBLIC_API_URL` is set correctly in Vercel
- Check backend CORS configuration includes your Vercel domain

**Build fails:**

- Check Vercel build logs
- Ensure `deploy/vercel-build.sh` is executable
- Verify file paths in `vercel.json`

### Database Issues

**Permission errors:**

```bash
sudo chown -R $USER:$USER /opt/fact-check/data
sudo chown -R $USER:$USER /opt/fact-check/factcheck.db
```

## Monitoring

### Backend Logs

```bash
# View logs
sudo journalctl -u fact-check -f

# View last 100 lines
sudo journalctl -u fact-check -n 100
```

### Nginx Logs

```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log
```

## Security Considerations

1. **Firewall**: Configure security groups to only allow necessary ports
2. **SSL**: Always use HTTPS in production
3. **API Keys**: Never commit `.env` files to git
4. **Database**: Consider using PostgreSQL instead of SQLite for production
5. **Rate Limiting**: Add rate limiting to prevent abuse
6. **Backups**: Set up regular database backups

## Scaling Considerations

- Use a load balancer for multiple EC2 instances
- Consider using RDS for database
- Use S3 for file storage instead of local filesystem
- Set up CloudWatch for monitoring
- Consider using ECS/EKS for containerized deployment

## Cost Optimization

- Use EC2 Spot Instances for development
- Set up auto-scaling based on load
- Use CloudFront CDN for static assets
- Consider using AWS Lambda for serverless functions
