#!/bin/bash
# Build script for Vercel deployment
# This script injects the API URL into the frontend files

set -e

API_URL="${NEXT_PUBLIC_API_URL:-}"

if [ -n "$API_URL" ]; then
  echo "Injecting API URL: $API_URL"
  # Replace the placeholder in index.html
  sed -i.bak "s|{{API_URL}}|$API_URL|g" frontend/index.html
  rm -f frontend/index.html.bak
else
  echo "Warning: NEXT_PUBLIC_API_URL not set, using same-origin fallback"
  # Remove the script tag if no API URL is provided
  sed -i.bak 's|<script>.*API_BASE_URL.*</script>||g' frontend/index.html
  rm -f frontend/index.html.bak
fi

echo "Build complete"
