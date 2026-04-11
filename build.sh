#!/bin/bash
set -e

# Configuration
IMAGE_NAME="auto_bangumi"
VERSION="${1:-dev}"
PLATFORMS="${2:-linux/amd64}"

echo "========================================="
echo "AutoBangumi Docker Build"
echo "Version: $VERSION"
echo "Platforms: $PLATFORMS"
echo "========================================="

# Build frontend
echo "[1/4] Building frontend..."
cd webui
pnpm install
pnpm build
cd ..

# Copy dist to backend
echo "[2/4] Copying frontend assets..."
rm -rf backend/src/dist
cp -r webui/dist backend/src/dist

# Create version info
echo "[3/4] Creating version info..."
echo "VERSION='$VERSION'" > backend/src/module/__version__.py

# Build Docker image
echo "[4/4] Building Docker image..."
if [[ "$PLATFORMS" == *","* ]]; then
    # Multi-platform build (requires buildx)
    docker buildx build \
        --platform "$PLATFORMS" \
        -t "$IMAGE_NAME:$VERSION" \
        -t "$IMAGE_NAME:latest" \
        --load \
        .
else
    # Single platform build
    docker build \
        -t "$IMAGE_NAME:$VERSION" \
        -t "$IMAGE_NAME:latest" \
        .
fi

echo "========================================="
echo "Build complete!"
echo "Image: $IMAGE_NAME:$VERSION"
echo "========================================="
echo ""
echo "Run with:"
echo "  docker run -p 7892:7892 -v ./config:/app/config -v ./data:/app/data $IMAGE_NAME:$VERSION"
