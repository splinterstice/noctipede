# GitHub Container Registry Deployment Guide

This guide covers deploying Noctipede using GitHub Container Registry (GHCR) for image distribution.

## Overview

The project is configured to automatically build and publish Docker images to GitHub Container Registry, making it easy to deploy consistent images across different environments.

## Prerequisites

1. **GitHub Personal Access Token**
   - Go to [GitHub Settings > Tokens](https://github.com/settings/tokens)
   - Create a new token with `write:packages` and `read:packages` scopes
   - Save the token securely

2. **Docker installed locally**
   - Required for building and pushing images manually

3. **Repository access**
   - Clone or fork access to the repository

## Quick Start

### 1. Setup Authentication
```bash
# Interactive setup (recommended for first-time users)
make ghcr-setup

# Or manual setup
export GITHUB_TOKEN=your_token_here
make ghcr-login
```

### 2. Build and Deploy
```bash
# Show current repository and image information
make ghcr-info

# Build, tag, and push to GHCR
make ghcr-deploy
```

### 3. Use Pre-built Images
```bash
# Run with Docker Compose using GHCR image
make run-ghcr

# Deploy to Kubernetes using GHCR image
make k8s-deploy-ghcr
```

## Manual Workflow

### Building Images
```bash
# Build and tag for GHCR
make ghcr-build

# This creates:
# - ghcr.io/splinterstice/noctipede:v1.0.0 (if tagged)
# - ghcr.io/splinterstice/noctipede:latest
```

### Pushing Images
```bash
# Push to GHCR (requires authentication)
make ghcr-push
```

### Combined Build and Push
```bash
# Build and push in one command
make ghcr-deploy
```

## Automated CI/CD

The repository includes a GitHub Actions workflow (`.github/workflows/docker-publish.yml`) that automatically:

- **Triggers on:**
  - Push to `main` or `develop` branches
  - Creation of version tags (e.g., `v1.0.0`)
  - Pull requests to `main`

- **Actions performed:**
  - Builds Docker image using `docker/Dockerfile`
  - Tags with appropriate version numbers
  - Pushes to GitHub Container Registry
  - Generates deployment summary

### Version Tagging

The system automatically creates tags based on:
- **Branch pushes:** `main`, `develop`
- **Git tags:** `v1.0.0` → `1.0.0`, `1.0`, `latest`
- **Pull requests:** `pr-123`

## Using GHCR Images

### Docker Compose
```bash
# Use the GHCR-specific compose file
make run-ghcr

# Or manually specify image
IMAGE_NAME=ghcr.io/splinterstice/noctipede:latest docker-compose -f docker-compose.ghcr.yml up -d
```

### Kubernetes
```bash
# Deploy using GHCR image
make k8s-deploy-ghcr

# Or update existing deployment
kubectl set image deployment/noctipede-app noctipede-app=ghcr.io/splinterstice/noctipede:v1.0.0 -n noctipede
```

### Direct Docker Run
```bash
# Pull and run directly
docker pull ghcr.io/splinterstice/noctipede:latest
docker run -d --name noctipede-app \
  -p 8080:8080 \
  --env-file .env \
  ghcr.io/splinterstice/noctipede:latest
```

## Image Information

### Repository Details
- **Registry:** `ghcr.io`
- **Repository:** `splinterstice/noctipede`
- **Full Image Name:** `ghcr.io/splinterstice/noctipede`

### Available Tags
- `latest` - Latest build from main branch
- `main` - Latest main branch build
- `develop` - Latest develop branch build
- `v1.0.0` - Specific version releases
- `1.0` - Major.minor version
- `pr-123` - Pull request builds

## Troubleshooting

### Authentication Issues
```bash
# Check if logged in
docker info | grep Username

# Re-login if needed
make ghcr-login

# Or use the setup script
make ghcr-setup
```

### Permission Errors
- Ensure your GitHub token has `write:packages` scope
- Verify you have push access to the repository
- Check that the repository allows package publishing

### Image Not Found
- Verify the image was successfully pushed: `docker images | grep ghcr.io`
- Check GitHub Packages page: `https://github.com/splinterstice/noctipede/pkgs/container/noctipede`
- Ensure you're using the correct image name and tag

### Build Failures
- Check Docker daemon is running
- Verify Dockerfile exists at `docker/Dockerfile`
- Ensure all required files are present in build context

## Security Considerations

1. **Token Security**
   - Never commit GitHub tokens to version control
   - Use environment variables or secure secret management
   - Rotate tokens regularly

2. **Image Security**
   - Images are public by default in GHCR
   - Consider making repository private for sensitive projects
   - Regularly update base images and dependencies

3. **Access Control**
   - Limit repository access to authorized users
   - Use branch protection rules
   - Review pull requests before merging

## Makefile Targets Reference

| Target | Description |
|--------|-------------|
| `ghcr-setup` | Interactive setup for GHCR authentication |
| `ghcr-info` | Show repository and image information |
| `ghcr-login` | Login to GitHub Container Registry |
| `ghcr-build` | Build and tag image for GHCR |
| `ghcr-push` | Push image to GHCR |
| `ghcr-deploy` | Build, tag, and push in one command |
| `ghcr-clean` | Remove local GHCR images |
| `run-ghcr` | Run with Docker Compose using GHCR image |
| `k8s-deploy-ghcr` | Deploy to Kubernetes using GHCR image |

## Environment Files

- `.env.ghcr.example` - Example environment configuration for GHCR deployment
- `docker-compose.ghcr.yml` - Docker Compose file configured for GHCR images

Copy and customize these files for your deployment needs.
