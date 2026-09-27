#!/bin/bash

echo "Installing the app and its dependencies (pyproject.toml)..."
pip install -e .
echo "Building the web front end (needs Node.js 20+)..."
(cd frontend && npm install --no-audit --no-fund && npm run build)
echo "Setup complete! The MLX model will be downloaded automatically on first run."
