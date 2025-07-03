#!/bin/bash

# GitHub Container Registry Setup Script
# This script helps set up authentication for GHCR

set -e

echo "=== GitHub Container Registry Setup ==="
echo ""

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if git is available and we're in a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Not in a git repository. Please run this from the project root."
    exit 1
fi

# Extract repository information
REPO_URL=$(git config --get remote.origin.url | sed 's/git@github.com://' | sed 's/.git$//')
REPO_OWNER=$(echo $REPO_URL | cut -d'/' -f1)
REPO_NAME=$(echo $REPO_URL | cut -d'/' -f2)
IMAGE_NAME="ghcr.io/$REPO_OWNER/$REPO_NAME"

echo "Repository: $REPO_URL"
echo "Image name: $IMAGE_NAME"
echo ""

# Check if already logged in
if docker info | grep -q "Username:"; then
    echo "✅ Already logged into Docker registry"
else
    echo "🔐 Docker login required"
fi

# Prompt for GitHub username
read -p "Enter your GitHub username: " GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo "❌ GitHub username is required"
    exit 1
fi

# Check for GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo ""
    echo "⚠️  GITHUB_TOKEN environment variable not set"
    echo "Please create a Personal Access Token at: https://github.com/settings/tokens"
    echo "Required scopes: write:packages, read:packages"
    echo ""
    read -s -p "Enter your GitHub Personal Access Token: " GITHUB_TOKEN
    echo ""
    
    if [ -z "$GITHUB_TOKEN" ]; then
        echo "❌ GitHub token is required"
        exit 1
    fi
fi

# Login to GHCR
echo "🔑 Logging into GitHub Container Registry..."
echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USERNAME" --password-stdin

if [ $? -eq 0 ]; then
    echo "✅ Successfully logged into GitHub Container Registry"
    echo ""
    echo "You can now use the following commands:"
    echo "  make ghcr-build    # Build and tag image"
    echo "  make ghcr-push     # Push image to GHCR"
    echo "  make ghcr-deploy   # Build and push in one step"
    echo ""
    echo "Image will be available at: $IMAGE_NAME"
else
    echo "❌ Failed to login to GitHub Container Registry"
    exit 1
fi
