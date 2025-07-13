# Noctipede Makefile

# Extract repository info from git config
REPO_URL := $(shell git config --get remote.origin.url | sed 's/git@github.com://' | sed 's/.git$$//')
REPO_NAME := $(shell echo $(REPO_URL) | cut -d'/' -f2)
REPO_OWNER := $(shell echo $(REPO_URL) | cut -d'/' -f1)
GHCR_REGISTRY := ghcr.io
IMAGE_NAME := $(GHCR_REGISTRY)/$(REPO_OWNER)/$(REPO_NAME)
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "latest")

.PHONY: help build run stop clean test lint format docker-build docker-run k8s-deploy k8s-clean ghcr-setup ghcr-login ghcr-build ghcr-push ghcr-deploy ghcr-info ghcr-clean run-ghcr k8s-deploy-ghcr

# Default target
help:
	@echo "Available targets:"
	@echo "  build         - Build Docker image"
	@echo "  run           - Run with Docker Compose"
	@echo "  stop          - Stop Docker Compose services"
	@echo "  clean         - Clean up Docker resources"
	@echo "  test          - Run tests"
	@echo "  lint          - Run linting"
	@echo "  format        - Format code"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-run    - Run Docker container"
	@echo "  k8s-deploy    - Deploy to Kubernetes"
	@echo "  k8s-clean     - Clean up Kubernetes resources"
	@echo ""
	@echo "GitHub Container Registry targets:"
	@echo "  ghcr-setup    - Interactive setup for GHCR authentication"
	@echo "  ghcr-info     - Show GHCR image information"
	@echo "  ghcr-login    - Login to GitHub Container Registry"
	@echo "  ghcr-build    - Build and tag image for GHCR"
	@echo "  ghcr-push     - Push image to GHCR"
	@echo "  ghcr-deploy   - Build, push and deploy to GHCR"
	@echo "  ghcr-clean    - Clean up local GHCR images"
	@echo "  run-ghcr      - Run with GHCR image using Docker Compose"
	@echo "  k8s-deploy-ghcr - Deploy to Kubernetes using GHCR image"

# Docker Compose targets
build:
	docker compose build

run:
	docker compose up -d

stop:
	docker compose down

clean:
	docker compose down -v
	docker system prune -f

# Development targets
test:
	python -m pytest tests/ -v

lint:
	flake8 noctipede/
	mypy noctipede/

format:
	black noctipede/
	isort noctipede/

# Docker targets
docker-build:
	docker build --no-cache -t noctipede:latest -f docker/Dockerfile .

docker-run:
	docker run -d --name noctipede-app \
		-p 8080:8080 \
		-v $(PWD)/data:/app/data \
		-v $(PWD)/output:/app/output \
		-v $(PWD)/logs:/app/logs \
		--env-file .env \
		noctipede:latest

# Kubernetes targets
k8s-deploy:
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/secrets.yaml
	kubectl apply -f k8s/configmap.yaml
	kubectl apply -f k8s/mariadb/
	kubectl apply -f k8s/minio/
	kubectl apply -f k8s/noctipede/

k8s-clean:
	kubectl delete namespace noctipede

# Setup targets
setup-env:
	cp .env.example .env
	@echo "Please edit .env file with your configuration"

setup-dev:
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	@echo "Virtual environment created. Activate with: source venv/bin/activate"

# Database targets
db-init:
	python -c "from database import get_db_manager; get_db_manager().create_tables()"

# Analysis targets
analyze-images:
	python -m noctipede.analysis.image_analyzer

moderate-content:
	python -m noctipede.analysis.content_moderator --threshold 30

# Crawler targets
crawl:
	python -m noctipede.crawlers.main

# API targets
api:
	python -m noctipede.api.main

# GitHub Container Registry targets
ghcr-setup:
	@echo "Running GHCR setup script..."
	@./scripts/ghcr-setup.sh

ghcr-info:
	@echo "Repository: $(REPO_URL)"
	@echo "Owner: $(REPO_OWNER)"
	@echo "Name: $(REPO_NAME)"
	@echo "Image: $(IMAGE_NAME)"
	@echo "Version: $(VERSION)"

ghcr-login:
	@echo "Logging into GitHub Container Registry..."
	@echo "Make sure you have a GitHub Personal Access Token with 'write:packages' scope"
	@echo "You can create one at: https://github.com/settings/tokens"
	@read -p "Enter your GitHub username: " username; \
	echo $$GITHUB_TOKEN | docker login $(GHCR_REGISTRY) -u $$username --password-stdin || \
	docker login $(GHCR_REGISTRY) -u $$username

ghcr-build:
	@echo "Building image for GitHub Container Registry..."
	docker build --no-cache -t $(IMAGE_NAME):$(VERSION) -f docker/Dockerfile .
	docker tag $(IMAGE_NAME):$(VERSION) $(IMAGE_NAME):latest
	@echo "Built and tagged: $(IMAGE_NAME):$(VERSION)"
	@echo "Built and tagged: $(IMAGE_NAME):latest"

ghcr-push:
	@echo "Pushing images to GitHub Container Registry..."
	docker push $(IMAGE_NAME):$(VERSION)
	docker push $(IMAGE_NAME):latest
	@echo "Successfully pushed to $(IMAGE_NAME)"

ghcr-deploy: ghcr-build ghcr-push
	@echo "Image deployed to GitHub Container Registry!"
	@echo "You can now pull with: docker pull $(IMAGE_NAME):$(VERSION)"
	@echo "Or use in Kubernetes with image: $(IMAGE_NAME):$(VERSION)"

# Update Kubernetes deployment to use GHCR image
k8s-deploy-ghcr:
	@echo "Deploying to Kubernetes using GHCR image..."
	@echo "Updating image reference to: $(IMAGE_NAME):$(VERSION)"
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/secrets.yaml
	kubectl apply -f k8s/configmap.yaml
	kubectl apply -f k8s/mariadb/
	kubectl apply -f k8s/minio/
	# Update the deployment to use GHCR image
	kubectl set image deployment/noctipede-app noctipede-app=$(IMAGE_NAME):$(VERSION) -n noctipede || \
	kubectl apply -f k8s/noctipede/
	kubectl set image deployment/noctipede-web noctipede-web=$(IMAGE_NAME):$(VERSION) -n noctipede || true

# Docker Compose with GHCR image
run-ghcr:
	@echo "Running with GHCR image: $(IMAGE_NAME):$(VERSION)"
	IMAGE_NAME=$(IMAGE_NAME):$(VERSION) docker compose -f docker-compose.ghcr.yml up -d

# Clean up local GHCR images
ghcr-clean:
	docker rmi $(IMAGE_NAME):$(VERSION) $(IMAGE_NAME):latest || true
