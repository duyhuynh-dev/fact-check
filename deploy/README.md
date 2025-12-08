# Deployment Files

This directory contains deployment configurations and scripts for:

- **EC2**: Backend deployment
- **Vercel**: Frontend deployment

## Quick Start

### Backend (EC2)

1. Launch an EC2 instance (Ubuntu 22.04)
2. SSH into the instance
3. Clone your repository
4. Run: `./deploy/ec2-setup.sh`
5. Configure `.env` file (see `.env.example.ec2`)
6. Update CORS origins in `.env` with your Vercel URL
7. Restart: `sudo systemctl restart fact-check`

### Frontend (Vercel)

1. Connect your GitHub repo to Vercel
2. Set environment variable: `NEXT_PUBLIC_API_URL` = your EC2 backend URL
3. Deploy!

See `DEPLOYMENT.md` for detailed instructions.

## Files

- `ec2-setup.sh` - Automated EC2 setup script
- `vercel.json` - Vercel configuration
- `vercel-build.sh` - Build script for Vercel
- `.env.example.ec2` - Example environment variables for EC2
- `DEPLOYMENT.md` - Complete deployment guide

