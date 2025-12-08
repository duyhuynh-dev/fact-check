# Quick Deployment Guide

## Backend on EC2 (5 minutes)

```bash
# 1. SSH into EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# 2. Clone repo
git clone <your-repo-url> /opt/fact-check
cd /opt/fact-check

# 3. Run setup
chmod +x deploy/ec2-setup.sh
./deploy/ec2-setup.sh

# 4. Configure environment
cp deploy/env.example.ec2 .env
nano .env  # Add your GEMINI_API_KEY and CORS_ORIGINS

# 5. Restart service
sudo systemctl restart fact-check

# 6. Test
curl http://localhost:8000/healthz
```

**Important**: Set `CORS_ORIGINS=https://*.vercel.app` in `.env` to allow all Vercel deployments!

## Frontend on Vercel (3 minutes)

1. Go to [vercel.com](https://vercel.com) → New Project
2. Import your GitHub repository
3. Set environment variable:
   - Key: `NEXT_PUBLIC_API_URL`
   - Value: `http://your-ec2-ip` or `https://your-domain.com`
4. Click Deploy

## After Deployment

Configure CORS once with a wildcard pattern (no need to update for each deployment):

1. Update EC2 `.env` file:

   ```bash
   CORS_ORIGINS=https://*.vercel.app
   ```

   This allows ALL Vercel deployments (production, preview, branch deployments)

2. Restart backend:
   ```bash
   sudo systemctl restart fact-check
   ```

That's it! No need to update CORS settings for each Vercel deployment.

## Troubleshooting

**Backend not responding?**

```bash
sudo systemctl status fact-check
sudo journalctl -u fact-check -f
```

**CORS errors?**

- Use wildcard pattern: `CORS_ORIGINS=https://*.vercel.app` (allows all Vercel deployments)
- Or specify exact domains: `CORS_ORIGINS=https://your-app.vercel.app`
- Restart the service after changing `.env`: `sudo systemctl restart fact-check`

**Frontend can't connect?**

- Verify `NEXT_PUBLIC_API_URL` is set in Vercel
- Check browser console for errors
- Verify backend is accessible: `curl http://your-ec2-ip/healthz`

