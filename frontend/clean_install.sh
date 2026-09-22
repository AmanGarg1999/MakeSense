#!/bin/bash
set -e

cd /run/media/huntingvision/1c514555-9d09-44e0-8fcc-e90fcada2549/workspaces/MakeSense/frontend

echo "=== Cleaning ==="
rm -rf node_modules package-lock.json
npm cache clean --force

echo "=== Installing with npm ==="
npm install --legacy-peer-deps

echo "=== Verifying vite ==="
ls -la node_modules/.bin/vite
ls -la node_modules/vite

echo "=== Done ==="