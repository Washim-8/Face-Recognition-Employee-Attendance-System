#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "==> Upgrading pip..."
pip install --upgrade pip

echo "==> Installing dependencies from requirements.txt..."
pip install --no-cache-dir -r requirements.txt

echo "==> Installing face-recognition without triggering dlib compilation..."
pip install --no-cache-dir --no-deps face-recognition==1.3.0

echo "==> Build complete successfully!"
