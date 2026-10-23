#!/bin/bash

echo "Installing the app and its dependencies (pyproject.toml)..."
pip install -e .
echo "Setup complete! The MLX model will be downloaded automatically on first run."
