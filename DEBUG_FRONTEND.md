# Frontend Deployment Debugging Guide

## Current Issue
The frontend directory is not being found in the Docker container at runtime, even though it should be copied during the build.

## Debug Endpoints

After deployment, you can access these endpoints to inspect the filesystem:

1. **`/debug/paths`** - Shows all checked frontend paths and root directory contents
2. **`/debug/filesystem`** - Comprehensive filesystem inspection including Docker environment checks

## Build Verification

The Dockerfile includes a verification step that should:
- List `/app/` contents
- Check if `/app/frontend` exists
- **Fail the build** if frontend is not found

If the build succeeds but frontend is still missing, the verification step may have been cached.

## Solutions

### Option 1: Force Rebuild Without Cache
In Render dashboard:
1. Go to your service
2. Click "Manual Deploy"
3. Check "Clear build cache" option
4. Deploy

### Option 2: Check Build Logs
Look for this section in build logs:
```
=== Verifying frontend directory ===
```

If you see:
- `✓ Frontend directory found` - Frontend was copied successfully
- `✗ ERROR: Frontend directory NOT found` - Build should have failed

### Option 3: Runtime Debugging
After deployment, visit:
- `https://fact-check-23lo.onrender.com/debug/paths` - See what paths were checked
- `https://fact-check-23lo.onrender.com/debug/filesystem` - See full filesystem inspection

### Option 4: Check Startup Logs
The application now logs comprehensive filesystem information on startup. Look for:
```
APPLICATION STARTUP - FILESYSTEM CHECK
============================================================
Current working directory: ...
/app directory exists. Contents:
  [DIR] backend
  [DIR] frontend  <-- Should be here
  ...
```

## Expected Behavior

1. **Build time**: Verification step should show `✓ Frontend directory found`
2. **Runtime**: Startup logs should show `/app/frontend exists: True`
3. **HTTP**: Root URL should serve `index.html`, not JSON fallback

## If Frontend Still Missing

1. Check that `frontend/` directory exists in your Git repository
2. Verify `.dockerignore` doesn't exclude `frontend/`
3. Check Render build logs for the verification step output
4. Use `/debug/filesystem` endpoint to see what's actually in the container

