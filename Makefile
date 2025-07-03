# Noctipede Makefile

.PHONY: help build run stop clean test lint format docker-build docker-run k8s-deploy k8s-clean

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
	docker build -t noctipede:latest -f docker/Dockerfile .

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
